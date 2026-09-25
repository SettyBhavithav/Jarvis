"""
JARVIS V2 - Storage Layer (Supabase PostgreSQL + pgvector & Offline SQLite Vector Cache)
Unified persistence adapter with native pgvector search and zero-downtime offline fallback.
"""
import os
import time
import json
import sqlite3
import uuid
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import certifi
import httpx
from core.config import config
from core.schemas import MemoryRecord, TaskItem, AuditEntry, TaskStatus, MemoryCategory

DEFAULT_SYSTEM_USER_UUID = "a0000000-0000-0000-0000-000000000001"

def to_uuid(val: Optional[str]) -> str:
    """Ensures any user ID or identifier is formatted as a valid PostgreSQL UUID."""
    if not val or val in ["user_default", "default"]:
        return DEFAULT_SYSTEM_USER_UUID
    try:
        return str(uuid.UUID(val))
    except (ValueError, AttributeError):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(val)))

class StorageAdapter:
    def __init__(self):
        self.supabase_url = config.SUPABASE_URL
        self.supabase_anon_key = config.SUPABASE_KEY
        self.supabase_service_role_key = config.SUPABASE_SERVICE_ROLE_KEY
        # User-facing and RLS operations strictly prefer anon key
        self.supabase_key = self.supabase_anon_key or self.supabase_service_role_key
        self.is_supabase_connected = False
        self.local_db_path = config.LOCAL_DB_PATH
        
        # Initialize local SQLite storage for guaranteed zero-downtime offline fallback
        self._init_local_db()

        # Check Supabase connectivity if credentials provided
        if self.supabase_url and self.supabase_key and "your_" not in self.supabase_url:
            self._verify_supabase_connection()
        else:
            print("[Storage: No Supabase keys detected in .env. Using Local Storage Engine (SQLite + Vector).]")

    def _init_local_db(self):
        """Initializes SQLite local storage schema."""
        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    text TEXT,
                    category TEXT,
                    embedding TEXT,
                    importance REAL,
                    access_count INTEGER,
                    created_at TEXT,
                    last_accessed_at TEXT,
                    synced INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    priority INTEGER,
                    due_date TEXT,
                    created_at TEXT,
                    completed_at TEXT,
                    synced INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    action_type TEXT,
                    schedule_cron TEXT,
                    target_time TEXT,
                    payload TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    user_id TEXT,
                    channel TEXT,
                    action TEXT,
                    tool_name TEXT,
                    arguments_summary TEXT,
                    risk_level INTEGER,
                    confirmed_by_user INTEGER,
                    status TEXT,
                    result_summary TEXT
                )
            """)
            conn.commit()

    def _verify_supabase_connection(self):
        """Pings Supabase Auth/REST API using secure HTTPS client with valid CA certs."""
        try:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}"
            }
            with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                res = client.get(f"{self.supabase_url}/auth/v1/health", headers=headers)
                if res.status_code in [200, 204]:
                    self.is_supabase_connected = True
                    print("[Storage: Successfully connected to Supabase Cloud]")
                else:
                    self.is_supabase_connected = False
        except Exception as e:
            print(f"[Storage Notice: Operating in Local Offline Mode: {e}]")
            self.is_supabase_connected = False

    def _get_headers(self, auth_token: Optional[str] = None, prefer: Optional[str] = None, use_admin: bool = False) -> Dict[str, str]:
        """
        Constructs headers with strict user JWT propagation.
        When auth_token is passed, Authorization: Bearer <USER_JWT> is supplied to PostgREST
        so that PostgreSQL RLS policies evaluate auth.uid() = user_id.
        The service-role key is strictly restricted to explicit admin operations (use_admin=True).
        """
        headers = {
            "apikey": self.supabase_anon_key or self.supabase_key,
            "Content-Type": "application/json"
        }
        if use_admin and self.supabase_service_role_key:
            bearer_token = self.supabase_service_role_key
        elif auth_token:
            bearer_token = auth_token
        else:
            bearer_token = self.supabase_anon_key or self.supabase_key

        headers["Authorization"] = f"Bearer {bearer_token}"
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _should_use_supabase_for_user_op(self, auth_token: Optional[str]) -> bool:
        """
        Gate for user-scoped Supabase operations.

        Returns True only when:
          - Supabase cloud is reachable (is_supabase_connected)
          - A user JWT (auth_token) is present to satisfy RLS (auth.uid() == user_id)

        When online but auth_token is absent, returns False so the caller falls
        through to the offline SQLite path. This prevents user-scoped data from
        being written or read under the anon key, which would:
          - Bypass RLS (anon key has no auth.uid() identity)
          - Mix data across users in multi-tenant contexts

        Admin/system operations (scheduler, provisioning) bypass this entirely
        by calling _get_headers(use_admin=True) directly — they never call this gate.
        """
        if not self.is_supabase_connected:
            return False
        if not auth_token:
            print(
                "[Storage: user-scoped Supabase op skipped — no auth_token supplied. "
                "Routing to offline SQLite. Pass a user JWT to enable cloud persistence.]"
            )
            return False
        return True

    def _write_local_memory(self, memory_id: str, effective_user: str, memory: MemoryRecord, emb_json: Optional[str], synced: int) -> bool:
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO local_memories 
                    (id, user_id, text, category, embedding, importance, access_count, created_at, last_accessed_at, synced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id, effective_user, memory.text, memory.category.value,
                    emb_json, memory.importance, memory.access_count,
                    memory.created_at.isoformat(),
                    memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
                    synced
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"[Local Storage Error in _write_local_memory]: {e}")
            return False

    # --- Supabase Auth Operations ---
    def auth_sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticates user via Supabase Auth API."""
        if self.is_supabase_connected:
            try:
                headers = {"apikey": self.supabase_key, "Content-Type": "application/json"}
                payload = {"email": email, "password": password}
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.post(f"{self.supabase_url}/auth/v1/token?grant_type=password", json=payload, headers=headers)
                    if res.status_code == 200:
                        return {"success": True, "data": res.json()}
                    return {"success": False, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}
        # Local mock authentication
        mock_user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
        return {
            "success": True,
            "data": {
                "access_token": f"jarvis_local_token_{mock_user_id}",
                "user": {"id": mock_user_id, "email": email}
            }
        }

    def auth_verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies JWT token with Supabase or validates local session token."""
        if not token:
            return None
        if token.startswith("jarvis_local_token_"):
            uid = token.replace("jarvis_local_token_", "")
            return {"id": uid, "role": "authenticated"}
        if self.is_supabase_connected:
            try:
                headers = {"apikey": self.supabase_key, "Authorization": f"Bearer {token}"}
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.get(f"{self.supabase_url}/auth/v1/user", headers=headers)
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass
        return None

    # --- Memory Operations ---
    def save_memory(self, memory: MemoryRecord, user_id: Optional[str] = None, auth_token: Optional[str] = None) -> bool:
        """Persists a memory record. Online: Supabase first, then local cache update. Offline: local queue."""
        memory_id = memory.id or str(uuid.uuid4())
        effective_user = to_uuid(user_id or memory.user_id)
        emb_json = json.dumps(memory.embedding) if memory.embedding else None

        # 1. Supabase Authoritative Insertion if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            sb_success = False
            try:
                headers = self._get_headers(auth_token, prefer="return=minimal")
                payload = {
                    "id": memory_id,
                    "user_id": effective_user,
                    "text": memory.text,
                    "category": memory.category.value,
                    "embedding": memory.embedding,
                    "importance": memory.importance,
                    "created_at": memory.created_at.isoformat()
                }
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.post(f"{self.supabase_url}/rest/v1/memories", json=payload, headers=headers)
                    if res.status_code in [200, 201, 204]:
                        sb_success = True
                    else:
                        print(f"[Supabase Sync Notice in save_memory ({res.status_code})]: {res.text}")
            except Exception as e:
                print(f"[Supabase Sync Error in save_memory]: {e}")

            if not sb_success:
                # Cloud authoritative write failed: queue to SQLite as unsynced
                self._write_local_memory(memory_id, effective_user, memory, emb_json, synced=0)
                return False

            # Cloud write succeeded: update local cache with synced=1
            self._write_local_memory(memory_id, effective_user, memory, emb_json, synced=1)
            return True

        # 2. Offline Mode: Record in local SQLite queue with synced=0
        return self._write_local_memory(memory_id, effective_user, memory, emb_json, synced=0)

    def search_memories(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.3,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        True Hybrid Search:
        Combines pgvector dense semantic retrieval with PostgreSQL / SQLite full-text lexical search
        via Reciprocal Rank Fusion (RRF).
        """
        target_uid = to_uuid(user_id)
        vector_results: List[Dict[str, Any]] = []
        lexical_results: List[Dict[str, Any]] = []

        # 1. Supabase Hybrid Execution if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token)
                # A. pgvector RPC Search
                payload = {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": top_k * 2,
                    "p_user_id": target_uid
                }
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    v_res = client.post(f"{self.supabase_url}/rest/v1/rpc/match_memories", json=payload, headers=headers)
                    if v_res.status_code == 200:
                        vector_results = v_res.json()

                    # B. PostgreSQL Lexical Keyword Search
                    if query_text:
                        lex_params = {
                            "user_id": f"eq.{target_uid}",
                            "text": f"ilike.*{query_text}*",
                            "limit": str(top_k * 2)
                        }
                        l_res = client.get(f"{self.supabase_url}/rest/v1/memories", headers=headers, params=lex_params)
                        if l_res.status_code == 200:
                            lexical_results = l_res.json()
            except Exception as e:
                print(f"[Supabase Hybrid Search Notice: {e}]")

        # 2. Local SQLite Hybrid Execution (fallback & hermetic)
        if not vector_results:
            q_emb = np.array(query_embedding, dtype=np.float32)
            norm_q = np.linalg.norm(q_emb)
            if norm_q > 0:
                with sqlite3.connect(self.local_db_path) as conn:
                    cursor = conn.cursor()
                    if user_id:
                        cursor.execute(
                            "SELECT id, text, category, embedding, importance, created_at FROM local_memories WHERE embedding IS NOT NULL AND user_id = ?",
                            (target_uid,)
                        )
                    else:
                        cursor.execute("SELECT id, text, category, embedding, importance, created_at FROM local_memories WHERE embedding IS NOT NULL")
                    for row in cursor.fetchall():
                        mid, text, cat, emb_str, imp, created = row
                        try:
                            doc_emb = np.array(json.loads(emb_str), dtype=np.float32)
                            norm_doc = np.linalg.norm(doc_emb)
                            if norm_doc > 0:
                                sim = float(np.dot(q_emb, doc_emb) / (norm_q * norm_doc))
                                if sim >= threshold:
                                    vector_results.append({
                                        "id": mid,
                                        "text": text,
                                        "category": cat,
                                        "importance": imp,
                                        "similarity": sim,
                                        "created_at": created
                                    })
                        except Exception:
                            continue
            vector_results.sort(key=lambda x: x["similarity"], reverse=True)

        if query_text and not lexical_results:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute(
                        "SELECT id, text, category, importance, created_at FROM local_memories WHERE user_id = ? AND text LIKE ? LIMIT ?",
                        (target_uid, f"%{query_text}%", top_k * 2)
                    )
                else:
                    cursor.execute(
                        "SELECT id, text, category, importance, created_at FROM local_memories WHERE text LIKE ? LIMIT ?",
                        (f"%{query_text}%", top_k * 2)
                    )
                for row in cursor.fetchall():
                    lexical_results.append({
                        "id": row[0],
                        "text": row[1],
                        "category": row[2],
                        "importance": row[3],
                        "similarity": 0.5,
                        "created_at": row[4]
                    })

        # 3. Reciprocal Rank Fusion (RRF) between Dense Vector and Lexical Streams
        if not lexical_results:
            return vector_results[:top_k]

        rrf_scores: Dict[str, float] = {}
        item_map: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60.0

        for rank, item in enumerate(vector_results):
            iid = item["id"]
            item_map[iid] = item
            rrf_scores[iid] = rrf_scores.get(iid, 0.0) + (1.0 / (rrf_k + rank + 1))

        for rank, item in enumerate(lexical_results):
            iid = item["id"]
            if iid not in item_map:
                item_map[iid] = item
            rrf_scores[iid] = rrf_scores.get(iid, 0.0) + (1.0 / (rrf_k + rank + 1))

        fused = sorted(item_map.values(), key=lambda x: rrf_scores.get(x["id"], 0.0), reverse=True)
        return fused[:top_k]

    def delete_memory(self, memory_text_snippet: str, user_id: Optional[str] = None, auth_token: Optional[str] = None) -> bool:
        """Deletes memories matching a text snippet for a specific user (Supabase primary + SQLite cache)."""
        target_uid = to_uuid(user_id)
        # 1. Supabase Primary Deletion (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token)
                params = {"user_id": f"eq.{target_uid}", "text": f"ilike.*{memory_text_snippet}*"}
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    client.delete(f"{self.supabase_url}/rest/v1/memories", headers=headers, params=params)
            except Exception as e:
                print(f"[Supabase Delete Memory Warning]: {e}")

        # 2. Local SQLite Cache Deletion
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("DELETE FROM local_memories WHERE text LIKE ? AND user_id = ?", (f"%{memory_text_snippet}%", target_uid))
                else:
                    cursor.execute("DELETE FROM local_memories WHERE text LIKE ?", (f"%{memory_text_snippet}%",))
                conn.commit()
            return True
        except Exception as e:
            print(f"[Memory Delete Error]: {e}")
            return False

    def get_all_memories(self, limit: int = 50, user_id: Optional[str] = None, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves stored memories (Supabase primary with SQLite fallback), scoped by user_id."""
        target_uid = to_uuid(user_id) if user_id and user_id != "user_default" else DEFAULT_SYSTEM_USER_UUID
        # 1. Supabase Authoritative Query if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token)
                params = {"user_id": f"eq.{target_uid}", "order": "created_at.desc", "limit": str(limit)}
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.get(f"{self.supabase_url}/rest/v1/memories", headers=headers, params=params)
                    if res.status_code == 200:
                        return [{
                            "id": r["id"],
                            "text": r["text"],
                            "category": r["category"],
                            "importance": r.get("importance", 0.5),
                            "created_at": r["created_at"]
                        } for r in res.json()]
            except Exception as e:
                print(f"[Supabase Get Memories Fallback: {e}]")

        # 2. Local SQLite Fallback
        items = []
        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT id, text, category, importance, created_at FROM local_memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (target_uid, limit)
                )
            else:
                cursor.execute(
                    "SELECT id, text, category, importance, created_at FROM local_memories ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            for r in cursor.fetchall():
                items.append({
                    "id": r[0],
                    "text": r[1],
                    "category": r[2],
                    "importance": r[3],
                    "created_at": r[4]
                })
        return items

    def clear_all_memories(self, user_id: Optional[str] = None, auth_token: Optional[str] = None) -> bool:
        """Clears memories for a user (Supabase primary + SQLite cache)."""
        target_uid = to_uuid(user_id) if user_id and user_id != "user_default" else DEFAULT_SYSTEM_USER_UUID
        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token)
                endpoint = f"{self.supabase_url}/rest/v1/memories?user_id=eq.{target_uid}" if user_id else f"{self.supabase_url}/rest/v1/memories"
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    client.delete(endpoint, headers=headers)
            except Exception as e:
                print(f"[Supabase Clear Memories Warning]: {e}")

        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("DELETE FROM local_memories WHERE user_id = ?", (target_uid,))
                else:
                    cursor.execute("DELETE FROM local_memories")
                conn.commit()
            return True
        except Exception:
            return False

    # --- Task Operations (Authoritative Supabase Primary + Local SQLite Fallback/Queue) ---
    def add_task(self, title: str, description: Optional[str] = None, user_id: str = DEFAULT_SYSTEM_USER_UUID, auth_token: Optional[str] = None) -> bool:
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        effective_user = to_uuid(user_id)

        # 1. Supabase Authoritative Insertion if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            sb_success = False
            try:
                headers = self._get_headers(auth_token, prefer="return=minimal")
                payload = {
                    "id": task_id,
                    "user_id": effective_user,
                    "title": title,
                    "description": description,
                    "status": "pending",
                    "priority": 1,
                    "created_at": created_at
                }
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.post(f"{self.supabase_url}/rest/v1/tasks", json=payload, headers=headers)
                    if res.status_code in [200, 201, 204]:
                        sb_success = True
                    else:
                        print(f"[Supabase Task Insert Error ({res.status_code})]: {res.text}")
            except Exception as e:
                print(f"[Supabase Task Exception]: {e}")

            if not sb_success:
                # Cloud write failed: queue locally as unsynced offline record and truthfully return False
                try:
                    with sqlite3.connect(self.local_db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO local_tasks (id, user_id, title, description, status, priority, created_at, synced)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                        """, (task_id, effective_user, title, description, "pending", 1, created_at))
                        conn.commit()
                except Exception:
                    pass
                return False

            # Cloud write succeeded: update local cache with synced=1
            try:
                with sqlite3.connect(self.local_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO local_tasks (id, user_id, title, description, status, priority, created_at, synced)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """, (task_id, effective_user, title, description, "pending", 1, created_at))
                    conn.commit()
            except Exception:
                pass
            return True

        # 2. Offline Mode: Record in local SQLite queue with synced=0
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO local_tasks (id, user_id, title, description, status, priority, created_at, synced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (task_id, effective_user, title, description, "pending", 1, created_at))
                conn.commit()
            return True
        except Exception as e:
            print(f"[Task Storage Error]: {e}")
            return False

    def get_tasks(self, status: Optional[str] = "pending", user_id: Optional[str] = None, auth_token: Optional[str] = None) -> List[TaskItem]:
        target_user = to_uuid(user_id) if user_id and user_id != "user_default" else DEFAULT_SYSTEM_USER_UUID
        # 1. Supabase Authoritative Query if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token)
                params = {"user_id": f"eq.{target_user}"}
                if status:
                    params["status"] = f"eq.{status}"
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.get(f"{self.supabase_url}/rest/v1/tasks", headers=headers, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        return [TaskItem(
                            id=item["id"],
                            user_id=item["user_id"],
                            title=item["title"],
                            description=item.get("description"),
                            status=TaskStatus(item["status"]),
                            priority=item.get("priority", 1),
                            created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                        ) for item in data]
            except Exception as e:
                print(f"[Supabase Get Tasks Fallback to Offline: {e}]")

        # 2. Local SQLite Fallback
        tasks = []
        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT id, title, description, status, priority, created_at, user_id FROM local_tasks WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if user_id:
                query += " AND user_id = ?"
                params.append(target_user)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            for r in rows:
                tasks.append(TaskItem(
                    id=r[0],
                    title=r[1],
                    description=r[2],
                    status=TaskStatus(r[3]),
                    priority=r[4],
                    created_at=datetime.fromisoformat(r[5]),
                    user_id=r[6] if len(r) > 6 else target_user
                ))
        return tasks

    def clear_tasks(self, user_id: Optional[str] = None, auth_token: Optional[str] = None) -> bool:
        target_user = to_uuid(user_id) if user_id and user_id != "user_default" else DEFAULT_SYSTEM_USER_UUID
        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token)
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    client.delete(f"{self.supabase_url}/rest/v1/tasks?user_id=eq.{target_user}", headers=headers)
            except Exception:
                pass

        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("DELETE FROM local_tasks WHERE user_id = ?", (target_user,))
                else:
                    cursor.execute("DELETE FROM local_tasks")
                conn.commit()
            return True
        except Exception:
            return False

    # --- Audit Logging (Supabase Primary with Local SQLite Fallback) ---
    def log_audit(self, entry: AuditEntry, auth_token: Optional[str] = None):
        entry_id = entry.id or str(uuid.uuid4())
        user_uuid = to_uuid(entry.user_id)

        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token, prefer="return=minimal")
                payload = {
                    "id": entry_id,
                    "timestamp": entry.timestamp.isoformat(),
                    "user_id": user_uuid,
                    "channel": entry.channel,
                    "action": entry.action,
                    "tool_name": entry.tool_name,
                    "arguments_summary": entry.arguments_summary,
                    "risk_level": entry.risk_level,
                    "confirmed_by_user": entry.confirmed_by_user,
                    "status": entry.status,
                    "result_summary": entry.result_summary
                }
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    client.post(f"{self.supabase_url}/rest/v1/audit_logs", json=payload, headers=headers)
            except Exception as e:
                print(f"[Supabase Audit Log Error: {e}]")

        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO local_audit_logs 
                    (id, timestamp, user_id, channel, action, tool_name, arguments_summary, risk_level, confirmed_by_user, status, result_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry_id, entry.timestamp.isoformat(), user_uuid, entry.channel,
                    entry.action, entry.tool_name, entry.arguments_summary, entry.risk_level,
                    1 if entry.confirmed_by_user else 0, entry.status, entry.result_summary
                ))
                conn.commit()
        except Exception:
            pass

    # --- Scheduled Tasks (Supabase Authoritative Primary with Local Queue/Cache) ---
    def add_scheduled_task(
        self,
        action_type: str,
        target_time: float,
        payload: Dict[str, Any],
        user_id: str = DEFAULT_SYSTEM_USER_UUID,
        auth_token: Optional[str] = None
    ) -> Optional[str]:
        job_id = str(uuid.uuid4())
        effective_user = to_uuid(user_id)
        target_iso = datetime.fromtimestamp(target_time, tz=timezone.utc).isoformat()
        payload_str = json.dumps(payload) if isinstance(payload, dict) else str(payload)

        # 1. Supabase Authoritative Insertion if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            sb_success = False
            try:
                headers = self._get_headers(auth_token, prefer="return=minimal")
                body = {
                    "id": job_id,
                    "user_id": effective_user,
                    "action_type": action_type,
                    "target_time": target_iso,
                    "payload": payload,
                    "is_active": True
                }
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.post(f"{self.supabase_url}/rest/v1/scheduled_tasks", json=body, headers=headers)
                    if res.status_code in [200, 201, 204]:
                        sb_success = True
                    else:
                        print(f"[Supabase Schedule Error ({res.status_code})]: {res.text}")
            except Exception as e:
                print(f"[Supabase Schedule Exception]: {e}")

            if sb_success:
                try:
                    with sqlite3.connect(self.local_db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO local_scheduled_tasks (id, user_id, action_type, target_time, payload, is_active)
                            VALUES (?, ?, ?, ?, ?, 1)
                        """, (job_id, effective_user, action_type, str(target_time), payload_str))
                        conn.commit()
                except Exception:
                    pass
                return job_id
            else:
                # Online write failed
                return None

        # 2. Offline Mode: Local SQLite
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO local_scheduled_tasks (id, user_id, action_type, target_time, payload, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (job_id, effective_user, action_type, str(target_time), payload_str))
                conn.commit()
            return job_id
        except Exception:
            return None

    def get_due_scheduled_tasks(self, user_id: Optional[str] = None, auth_token: Optional[str] = None, use_admin: bool = False) -> List[Dict[str, Any]]:
        now_ts = time.time()
        now_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat()
        due = []

        # 1. Supabase Authoritative Query if online
        if self.is_supabase_connected:
            try:
                headers = self._get_headers(auth_token, use_admin=use_admin)
                params = {"is_active": "eq.true", "target_time": f"lte.{now_iso}"}
                if user_id:
                    params["user_id"] = f"eq.{to_uuid(user_id)}"
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.get(f"{self.supabase_url}/rest/v1/scheduled_tasks", headers=headers, params=params)
                    if res.status_code == 200:
                        for r in res.json():
                            p_load = r.get("payload", {})
                            if isinstance(p_load, str):
                                try:
                                    p_load = json.loads(p_load)
                                except Exception:
                                    pass
                            due.append({
                                "id": r["id"],
                                "user_id": r["user_id"],
                                "action_type": r["action_type"],
                                "payload": json.dumps(p_load) if isinstance(p_load, dict) else str(p_load)
                            })
                        return due
            except Exception as e:
                print(f"[Supabase Get Due Tasks Fallback to Offline: {e}]")

        # 2. Local SQLite Fallback
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute(
                        "SELECT id, user_id, action_type, payload FROM local_scheduled_tasks WHERE is_active = 1 AND user_id = ? AND CAST(target_time AS REAL) <= ?",
                        (to_uuid(user_id), now_ts)
                    )
                else:
                    cursor.execute(
                        "SELECT id, user_id, action_type, payload FROM local_scheduled_tasks WHERE is_active = 1 AND CAST(target_time AS REAL) <= ?",
                        (now_ts,)
                    )
                for r in cursor.fetchall():
                    due.append({"id": r[0], "user_id": r[1], "action_type": r[2], "payload": r[3]})
        except Exception:
            pass

        return due

    def claim_scheduled_task(self, job_id: str, auth_token: Optional[str] = None, use_admin: bool = False) -> bool:
        """
        Atomically claims a due scheduled task by setting is_active = false.
        Online: Performs conditional PATCH on Supabase with Prefer: return=representation.
        Offline: Atomically updates SQLite where is_active = 1.
        """
        if self.is_supabase_connected:
            try:
                headers = self._get_headers(auth_token, prefer="return=representation", use_admin=use_admin)
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.patch(
                        f"{self.supabase_url}/rest/v1/scheduled_tasks?id=eq.{job_id}&is_active=eq.true",
                        json={"is_active": False},
                        headers=headers
                    )
                    if res.status_code in [200, 204]:
                        data = res.json() if res.content else []
                        if isinstance(data, list) and len(data) > 0:
                            try:
                                with sqlite3.connect(self.local_db_path) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE local_scheduled_tasks SET is_active = 0 WHERE id = ?", (job_id,))
                                    conn.commit()
                            except Exception:
                                pass
                            return True
                        return False
            except Exception as e:
                print(f"[Supabase Claim Task Warning: {e}]")

        # 2. Local SQLite Atomic Claim
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE local_scheduled_tasks SET is_active = 0 WHERE id = ? AND is_active = 1",
                    (job_id,)
                )
                conn.commit()
                return cursor.rowcount == 1
        except Exception:
            return False

    def mark_scheduled_task_completed(self, job_id: str, auth_token: Optional[str] = None, use_admin: bool = False):
        if self.is_supabase_connected:
            try:
                headers = self._get_headers(auth_token, use_admin=use_admin)
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    client.patch(f"{self.supabase_url}/rest/v1/scheduled_tasks?id=eq.{job_id}", json={"is_active": False}, headers=headers)
            except Exception:
                pass
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE local_scheduled_tasks SET is_active = 0 WHERE id = ?", (job_id,))
                conn.commit()
        except Exception:
            pass

    # --- Knowledge Graph / Memory Links (Authoritative Supabase + Local Cache) ---
    def save_memory_link(
        self,
        source_entity: str,
        relationship: str,
        target_entity: str,
        user_id: str = DEFAULT_SYSTEM_USER_UUID,
        auth_token: Optional[str] = None
    ) -> bool:
        link_id = str(uuid.uuid4())
        effective_user = to_uuid(user_id)

        # 1. Supabase Authoritative Insertion if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            sb_success = False
            try:
                headers = self._get_headers(auth_token, prefer="return=minimal")
                payload = {
                    "id": link_id,
                    "user_id": effective_user,
                    "source_entity": source_entity.strip(),
                    "relationship": relationship.strip(),
                    "target_entity": target_entity.strip(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.post(f"{self.supabase_url}/rest/v1/memory_links", json=payload, headers=headers)
                    if res.status_code in [200, 201, 204]:
                        sb_success = True
                    else:
                        print(f"[Supabase Knowledge Link Error ({res.status_code})]: {res.text}")
            except Exception as e:
                print(f"[Supabase Knowledge Link Exception]: {e}")

            if not sb_success:
                # Cloud write failed: record locally as unsynced and truthfully return False
                self._write_local_link(link_id, effective_user, source_entity, relationship, target_entity, synced=0)
                return False

            # Cloud write succeeded: record locally as synced=1
            self._write_local_link(link_id, effective_user, source_entity, relationship, target_entity, synced=1)
            return True

        # 2. Offline Mode: Record in local SQLite queue with synced=0
        return self._write_local_link(link_id, effective_user, source_entity, relationship, target_entity, synced=0)

    def _write_local_link(self, link_id: str, user_id: str, source: str, rel: str, target: str, synced: int) -> bool:
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS local_knowledge_graph (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        subject TEXT,
                        predicate TEXT,
                        object TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        synced INTEGER DEFAULT 0
                    )
                """)
                cursor.execute("""
                    INSERT INTO local_knowledge_graph (id, user_id, subject, predicate, object, synced)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (link_id, user_id, source.strip(), rel.strip(), target.strip(), synced))
                conn.commit()
            return True
        except Exception:
            return False

    def query_memory_links(
        self,
        entity: str,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, str]]:
        target_user = to_uuid(user_id) if user_id and user_id != "user_default" else DEFAULT_SYSTEM_USER_UUID

        # 1. Supabase Authoritative Query if online (requires user JWT)
        if self._should_use_supabase_for_user_op(auth_token):
            try:
                headers = self._get_headers(auth_token)
                params = {
                    "user_id": f"eq.{target_user}",
                    "or": f"(source_entity.ilike.*{entity}*,target_entity.ilike.*{entity}*)"
                }
                with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
                    res = client.get(f"{self.supabase_url}/rest/v1/memory_links", headers=headers, params=params)
                    if res.status_code == 200:
                        return [{
                            "subject": r["source_entity"],
                            "predicate": r["relationship"],
                            "object": r["target_entity"]
                        } for r in res.json()]
            except Exception as e:
                print(f"[Supabase Query Memory Links Fallback: {e}]")

        # 2. Local SQLite Fallback
        results = []
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS local_knowledge_graph (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        subject TEXT,
                        predicate TEXT,
                        object TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        synced INTEGER DEFAULT 0
                    )
                """)
                if user_id:
                    cursor.execute("""
                        SELECT subject, predicate, object FROM local_knowledge_graph
                        WHERE user_id = ? AND (subject LIKE ? OR object LIKE ?)
                    """, (target_user, f"%{entity}%", f"%{entity}%"))
                else:
                    cursor.execute("""
                        SELECT subject, predicate, object FROM local_knowledge_graph
                        WHERE subject LIKE ? OR object LIKE ?
                    """, (f"%{entity}%", f"%{entity}%"))
                for r in cursor.fetchall():
                    results.append({"subject": r[0], "predicate": r[1], "object": r[2]})
        except Exception:
            pass
        return results

# Global Storage Adapter Singleton
storage_adapter = StorageAdapter()

