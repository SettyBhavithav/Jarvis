"""
JARVIS V2 - Local Vector Embedding Engine
Uses sentence-transformers ('all-MiniLM-L6-v2') locally on CPU/GPU (384-dimensions).
"""
import os
from typing import List
from core.config import config

class EmbeddingEngine:
    def __init__(self):
        self._model = None
        self.model_name = config.EMBEDDING_MODEL

    def _load_model(self):
        if self._model is None:
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
            print(f"[EmbeddingEngine: Loading Local Model: {self.model_name}...]")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            print("[EmbeddingEngine: Model Loaded Successfully]")

    def encode(self, text: str) -> List[float]:
        """Encodes text into a 384-dimensional vector."""
        self._load_model()
        vector = self._model.encode(text)
        return vector.tolist()

# Global Embedding Singleton
embedding_engine = EmbeddingEngine()
