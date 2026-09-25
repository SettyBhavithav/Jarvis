"""
JARVIS V2 - Central Memory Manager
Coordinates working memory, short-term history, semantic long-term RAG, reranking, and knowledge graph.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from core.schemas import MemoryRecord, MemoryCategory, ChatMessage, MessageRole
from storage.supabase import storage_adapter
from memory.embeddings import embedding_engine
from memory.extractor import memory_extractor
from memory.knowledge_graph import knowledge_graph
from memory.reranker import memory_reranker
from memory.document import document_rag

class MemoryManager:
    def __init__(self):
        self.storage = storage_adapter
        self.embeddings = embedding_engine
        self.extractor = memory_extractor
        self.graph = knowledge_graph
        self.reranker = memory_reranker
        self.doc_rag = document_rag
        self.working_memory: List[ChatMessage] = []

    def add_memory(
        self,
        text: str,
        category: MemoryCategory = MemoryCategory.GENERAL,
        importance: float = 0.5,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> bool:
        """Embeds and persists a new memory record with authoritative cloud-first sync."""
        try:
            vector = self.embeddings.encode(text)
            record = MemoryRecord(
                text=text,
                category=category,
                embedding=vector,
                importance=importance,
                created_at=datetime.now(timezone.utc)
            )
            return self.storage.save_memory(record, user_id=user_id, auth_token=auth_token)
        except Exception as e:
            print(f"[MemoryManager Error in add_memory]: {e}")
            return False

    def retrieve_relevant_memories(
        self,
        query: str,
        top_k: int = 4,
        threshold: float = 0.25,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves candidates using hybrid vector search and applies multi-factor contextual reranking."""
        try:
            q_vector = self.embeddings.encode(query)
            raw_candidates = self.storage.search_memories(
                query_embedding=q_vector,
                top_k=top_k * 3,
                threshold=threshold,
                user_id=user_id,
                auth_token=auth_token,
                query_text=query
            )
            
            # Apply real reranker
            reranked = self.reranker.rerank(query=query, candidates=raw_candidates, top_n=top_k)
            return reranked
        except Exception as e:
            print(f"[MemoryManager Error in retrieve_relevant_memories]: {e}")
            return []

    def process_turn_for_memory(
        self,
        user_text: str,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Optional[str]:
        candidate = self.extractor.extract_candidate(user_text)
        if candidate:
            success = self.add_memory(
                text=candidate["text"],
                category=candidate["category"],
                importance=candidate["importance"],
                user_id=user_id,
                auth_token=auth_token
            )
            if success:
                return candidate["text"]
        return None

# Global Memory Manager Singleton
memory_manager = MemoryManager()
