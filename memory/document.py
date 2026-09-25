"""
JARVIS V2 - Document RAG Engine
Loads, chunks, embeds, and retrieves context from local PDFs and text files.
"""
import os
from typing import List, Dict, Any, Optional
from memory.embeddings import embedding_engine

from storage.supabase import storage_adapter

class DocumentRAG:
    def __init__(self):
        self.embeddings = embedding_engine
        self.storage = storage_adapter

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def ingest_document(self, file_path: str, user_id: Optional[str] = None, auth_token: Optional[str] = None) -> int:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document '{file_path}' does not exist.")

        raw_text = ""
        if file_path.endswith(".txt") or file_path.endswith(".md"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        elif file_path.endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        raw_text += txt + "\n"
            except ImportError:
                return 0

        if not raw_text.strip():
            return 0

        chunks = self.chunk_text(raw_text)
        from core.schemas import MemoryRecord, MemoryCategory, DEFAULT_SYSTEM_USER_UUID
        count = 0
        doc_name = os.path.basename(file_path)
        effective_uid = user_id or DEFAULT_SYSTEM_USER_UUID
        for i, chunk in enumerate(chunks):
            vector = self.embeddings.encode(chunk)
            rec = MemoryRecord(
                user_id=effective_uid,
                text=f"[{doc_name} - Chunk {i+1}]: {chunk}",
                category=MemoryCategory.PROJECT,
                embedding=vector,
                importance=0.6
            )
            self.storage.save_memory(rec, user_id=effective_uid, auth_token=auth_token)
            count += 1
        return count

    def search_documents(
        self,
        query: str,
        limit: int = 5,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs true hybrid search across indexed documents:
        Combines pgvector dense semantic retrieval with PostgreSQL / SQLite full-text search
        via Reciprocal Rank Fusion (RRF), followed by contextual reranking.
        """
        q_emb = self.embeddings.encode(query)
        matches = self.storage.search_memories(
            query_embedding=q_emb,
            top_k=limit * 2,
            threshold=0.20,
            user_id=user_id,
            auth_token=auth_token,
            query_text=query
        )
        # Format candidate documents with citation metadata
        candidates = []
        for m in matches:
            text = m.get("text", "")
            if text.startswith("[") and "]:" in text:
                citation = text.split("]:")[0].lstrip("[")
                content = text.split("]:", 1)[1].strip()
            else:
                citation = "Indexed Knowledge"
                content = text
            candidates.append({
                "citation": citation,
                "content": content,
                "text": text,
                "similarity": m.get("similarity", 0.0),
                "importance": m.get("importance", 0.5),
                "created_at": m.get("created_at")
            })

        # Apply multi-factor contextual reranking
        from memory.reranker import memory_reranker
        reranked = memory_reranker.rerank(query=query, candidates=candidates, top_n=limit)
        return reranked

# Global Document RAG Singleton
document_rag = DocumentRAG()

