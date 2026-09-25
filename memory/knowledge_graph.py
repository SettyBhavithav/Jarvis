"""
JARVIS V2 - Personal Knowledge Graph
Relational knowledge graph representing entities and facts on top of Supabase memory_links table with local fallback.
"""
from typing import List, Dict, Any, Optional
from storage.supabase import storage_adapter, DEFAULT_SYSTEM_USER_UUID

class KnowledgeGraph:
    def __init__(self):
        self.storage = storage_adapter

    def add_relation(self, subject: str, predicate: str, obj: str, user_id: str = DEFAULT_SYSTEM_USER_UUID, auth_token: Optional[str] = None) -> bool:
        """Stores subject-predicate-object semantic relation in Supabase memory_links."""
        return self.storage.save_memory_link(
            source_entity=subject,
            relationship=predicate,
            target_entity=obj,
            user_id=user_id,
            auth_token=auth_token
        )

    def query_entity(self, entity: str, user_id: Optional[str] = None, auth_token: Optional[str] = None) -> List[Dict[str, str]]:
        """Queries graph relations matching an entity."""
        return self.storage.query_memory_links(entity=entity, user_id=user_id, auth_token=auth_token)

# Global Knowledge Graph Singleton
knowledge_graph = KnowledgeGraph()

