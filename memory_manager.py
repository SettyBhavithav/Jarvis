import os
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class MemoryManager:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI")
        if not self.uri:
            print("[Memory Warning] No MONGODB_URI found in .env. Long-Term Memory will be disabled.")
            self.client = None
            return
            
        print("[Initializing Long-Term Memory (RAG)...]")
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
            self.db = self.client["jarvis_brain"]
            self.collection = self.db["memories"]
            self.task_collection = self.db["tasks"]
            # Test connection
            self.client.server_info()
            print("[Database: Connected to MongoDB Atlas]")
        except Exception as e:
            print(f"[Database Error] Could not connect to MongoDB: {e}")
            self.client = None
            return
            
        # Load embedding model (runs locally on CPU, no API cost)
        # Suppress symlinks warning on Windows
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        print("[Loading Embedding Model (all-MiniLM-L6-v2)...]")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("[Embedding Model: Loaded]")

    def add_memory(self, text, category="general"):
        """Embeds and saves a memory to MongoDB."""
        if not self.client: return False
        try:
            # Generate vector embedding for the text
            embedding = self.model.encode(text).tolist()
            doc = {
                "text": text,
                "category": category,
                "embedding": embedding,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"[Memory Add Error]: {e}")
            return False

    def search_memory(self, query, top_k=3, threshold=0.3):
        """Searches memory using local cosine similarity."""
        if not self.client: return []
        try:
            query_embedding = self.model.encode(query)
            
            # Fetch all memories
            # For a personal AI, downloading hundreds of memories takes <10ms.
            # This completely avoids needing to configure complex Atlas Vector Search indexes!
            all_docs = list(self.collection.find({}, {"_id": 0, "text": 1, "embedding": 1, "timestamp": 1}))
            if not all_docs: return []
            
            results = []
            for doc in all_docs:
                doc_emb = np.array(doc["embedding"])
                # Calculate Cosine similarity
                similarity = np.dot(query_embedding, doc_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb))
                if similarity >= threshold:
                    results.append({
                        "text": doc["text"], 
                        "score": float(similarity), 
                        "timestamp": doc["timestamp"]
                    })
            
            # Sort by highest score (most relevant first)
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        except Exception as e:
            print(f"[Memory Search Error]: {e}")
            return []

    def add_task(self, task_text):
        """Adds a new task to the persistent to-do list."""
        if not self.client: return False
        try:
            doc = {
                "task": task_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.task_collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"[Task Error]: {e}")
            return False

    def get_tasks(self):
        """Retrieves all tasks from MongoDB."""
        if not self.client: return []
        try:
            tasks = list(self.task_collection.find({}, {"_id": 0, "task": 1}))
            return [t["task"] for t in tasks]
        except Exception as e:
            print(f"[Task Fetch Error]: {e}")
            return []

    def clear_tasks(self):
        """Deletes all tasks from MongoDB."""
        if not self.client: return False
        try:
            self.task_collection.delete_many({})
            return True
        except Exception as e:
            print(f"[Task Clear Error]: {e}")
            return False


# Expose a global instance
memory_db = MemoryManager()
