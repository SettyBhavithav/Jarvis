"""
JARVIS V2 - Advanced Memory Reranker
Scores candidate memories using multi-factor contextual ranking:
Score = 0.50 * Semantic_Sim + 0.20 * Importance + 0.15 * Recency + 0.15 * Keyword_Match
"""
from typing import List, Dict, Any
from datetime import datetime, timezone

class MemoryReranker:
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_n: int = 4) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        query_terms = set(query.lower().split())
        scored = []

        for item in candidates:
            text = item.get("text", "")
            sim = float(item.get("similarity", 0.5))
            imp = float(item.get("importance", 0.5))

            # Recency factor
            created_at_str = item.get("created_at")
            recency = 0.5
            if created_at_str:
                try:
                    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - dt).days
                    recency = max(0.1, 1.0 - (age_days / 365.0))
                except Exception:
                    recency = 0.5

            # Keyword lexical overlap factor
            text_terms = set(text.lower().split())
            overlap = len(query_terms.intersection(text_terms))
            lexical_score = min(1.0, overlap / max(1, len(query_terms)))

            # Multi-factor final score
            final_score = (0.50 * sim) + (0.20 * imp) + (0.15 * recency) + (0.15 * lexical_score)
            item["rerank_score"] = final_score
            item["final_score"] = final_score
            scored.append(item)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_n]

# Global Reranker Singleton
memory_reranker = MemoryReranker()
