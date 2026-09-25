"""
Pytest configuration and hermetic test isolation fixtures for JARVIS V2.
Ensures tests run deterministically and independently in any environment (CI, Linux, Windows, offline).
"""
import pytest
from core.config import config
from storage.supabase import storage_adapter

@pytest.fixture(autouse=True)
def hermetic_test_storage(request, monkeypatch, tmp_path):
    """
    Ensures unit and benchmark tests execute in an isolated, hermetic SQLite environment.
    Prevents standard test runs from polluting production cloud databases or failing on missing network.
    Live integration tests marked with @pytest.mark.integration run against the real Supabase cloud instance.
    """
    if "integration" in request.keywords:
        # Re-verify live connection if credentials are configured
        if storage_adapter.supabase_url and storage_adapter.supabase_key:
            storage_adapter._verify_supabase_connection()
        yield
        return

    temp_db = str(tmp_path / "test_jarvis.db")
    orig_db = storage_adapter.local_db_path
    orig_sb_status = storage_adapter.is_supabase_connected

    storage_adapter.local_db_path = temp_db
    storage_adapter._init_local_db()
    # Offline hermetic mode for unit and evaluation test suites
    storage_adapter.is_supabase_connected = False

    yield

    storage_adapter.local_db_path = orig_db
    storage_adapter.is_supabase_connected = orig_sb_status
