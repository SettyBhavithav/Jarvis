"""
Unit Tests for JARVIS V2 - Memory & RAG Retrieval
"""
import pytest
from core.schemas import MemoryRecord, MemoryCategory
from memory.manager import memory_manager
from storage.supabase import storage_adapter

def test_memory_add_and_retrieve():
    test_fact = "Setty's brother is Sunny Anna and he likes black coffee"
    success = memory_manager.add_memory(test_fact, category=MemoryCategory.PREFERENCE, importance=0.9)
    assert success is True

    # Search for related query
    results = memory_manager.retrieve_relevant_memories("who is Sunny and what coffee does Setty like?", top_k=2, threshold=0.2)
    assert len(results) > 0
    found_texts = [r["text"] for r in results]
    assert any("Sunny Anna" in t for t in found_texts)
    assert "final_score" in results[0]

def test_automatic_memory_extraction():
    sample_turn = "Remember that my secondary laptop is a Dell XPS running Windows 11"
    extracted = memory_manager.process_turn_for_memory(sample_turn)
    assert extracted is not None
    assert "Dell XPS" in extracted
