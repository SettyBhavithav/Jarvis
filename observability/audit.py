"""
JARVIS V2 - Security Audit Trail
Persists structured records of all sensitive operations (Levels 2-4).
"""
from typing import Optional
from core.schemas import AuditEntry
from storage.supabase import storage_adapter

class AuditLogger:
    @staticmethod
    def record(entry: AuditEntry, auth_token: Optional[str] = None):
        storage_adapter.log_audit(entry, auth_token=auth_token)

audit_logger = AuditLogger()
