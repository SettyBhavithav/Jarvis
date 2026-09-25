"""
JARVIS V2 - Document Processing & RAG Agent
Specialized agent for ingesting, querying, and summarizing documents and PDFs.
"""
from typing import List, Generator
from core.schemas import ChatMessage
from agents.base_agent import BaseAgent
from memory.document import document_rag
from tools.registry import tool_registry
from core.orchestrator import orchestrator

class DocumentAgent(BaseAgent):
    """Handles document ingestion, semantic search across local documents, and summarization."""

    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        # Check if user wants to search or summarize indexed documents
        system_instruction = (
            "You are Jarvis Document Analysis Specialist. Use document RAG and context "
            "to provide precise, factual answers based on provided documents with explicit citations."
        )
        enhanced_prompt = f"{system_instruction}\n\nUser Request: {prompt}"
        return orchestrator.execute_turn(enhanced_prompt, history, channel="text")

    def index_document(self, file_path: str) -> str:
        """Helper to index a local document into memory."""
        count = document_rag.ingest_document(file_path)
        return f"Successfully indexed {count} chunks from {file_path}."

    def search_documents(self, query: str, limit: int = 5) -> List[dict]:
        """Helper to query the document collection."""
        return document_rag.search_documents(query, limit=limit)

