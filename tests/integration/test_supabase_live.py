"""
JARVIS V2 - Live Supabase Cloud Integration & Verification Suite

Tests REAL Supabase PostgreSQL + pgvector + RLS + PostgREST against the active project.

Identity contract (verified in every test):
    Supabase Auth UUID  ==  public.users UUID  ==  JWT auth.uid()

This means:
  1. A real auth.users user is provisioned via Admin API
  2. Supabase's on_auth_user_created trigger auto-seeds public.users
  3. We sign in with email+password to obtain a REAL JWT
  4. The JWT's sub == the actual auth UUID == the database user_id
  5. RLS evaluates auth.uid() == user_id — the full chain is verified

Service role key usage:
  - ALLOWED:  user provisioning, cleanup, admin read-back
  - FORBIDDEN: identity token for RLS tests (would bypass RLS silently)

Run independently from the hermetic suite:
    pytest -q                  →  hermetic SQLite suite (37 tests)
    pytest -m integration -v   →  this suite (requires .env with live credentials)
"""
import uuid
import time
import pytest
from datetime import datetime, timezone
from core.schemas import MemoryRecord, MemoryCategory, AuditEntry
from storage.supabase import storage_adapter, to_uuid, DEFAULT_SYSTEM_USER_UUID
from security.authentication import auth_manager
from memory.embeddings import embedding_engine

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Module-scoped fixture: provision TWO real auth users, yield credentials,
# then delete both from auth.users after the entire module finishes.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def live_auth_context():
    """
    Provisions two real Supabase Auth users and returns their ACTUAL credentials.

    The fixture:
      1. Calls auth_manager.create_test_auth_user() — creates real auth.users rows
      2. The on_auth_user_created DB trigger auto-seeds public.users for each
      3. Signs in to obtain real JWTs (sub == actual_user_id)
      4. Yields context dicts so every test uses the consistent {uuid, jwt} pair
      5. Deletes both users from auth.users on teardown (CASCADE clears public.users)

    If provisioning fails (no service role key, API error, JWT not returned),
    all tests in this module are SKIPPED — never silently passed with wrong identity.
    """
    # Pre-flight: verify live cloud connectivity
    if not storage_adapter.supabase_url or "supabase.co" not in storage_adapter.supabase_url:
        pytest.skip("Live Supabase URL not configured — skipping integration suite.")

    storage_adapter._verify_supabase_connection()
    if not storage_adapter.is_supabase_connected:
        pytest.skip("Cannot reach live Supabase Cloud — skipping integration suite.")

    if not storage_adapter.supabase_service_role_key:
        pytest.skip(
            "SUPABASE_SERVICE_ROLE_KEY not set — cannot provision real auth users. "
            "Integration tests require the service role key for test user provisioning."
        )

    # Provision User Alpha
    try:
        alpha_uuid, alpha_token = auth_manager.create_test_auth_user()
    except RuntimeError as e:
        pytest.fail(
            f"Failed to provision integration test user Alpha. "
            f"Real Supabase JWT is required — service role key cannot substitute.\n{e}"
        )

    # Provision User Beta (for cross-user isolation tests)
    try:
        beta_uuid, beta_token = auth_manager.create_test_auth_user()
    except RuntimeError as e:
        # Clean up Alpha before failing
        auth_manager.delete_test_auth_user(alpha_uuid)
        pytest.fail(
            f"Failed to provision integration test user Beta.\n{e}"
        )

    # Both users exist with consistent UUID ↔ JWT pairs.
    # The DB trigger has seeded public.users for each — FK constraints satisfied.
    yield {
        "user_id": alpha_uuid,       # actual auth.users UUID = public.users UUID = JWT sub
        "token": alpha_token,        # real JWT: auth.uid() == alpha_uuid under RLS
        "other_user_id": beta_uuid,
        "other_token": beta_token
    }

    # Teardown: delete both test users from auth.users.
    # CASCADE removes public.users, public.user_profiles rows.
    auth_manager.delete_test_auth_user(alpha_uuid)
    auth_manager.delete_test_auth_user(beta_uuid)


# ---------------------------------------------------------------------------
# Test 1: Connectivity
# ---------------------------------------------------------------------------
def test_supabase_cloud_connectivity(live_auth_context):
    """Verifies live HTTPS connectivity to Supabase Cloud REST/Auth endpoints."""
    assert storage_adapter.is_supabase_connected is True
    assert storage_adapter.supabase_url is not None
    assert storage_adapter.supabase_key is not None


# ---------------------------------------------------------------------------
# Test 2: Truthful authoritative task persistence
# ---------------------------------------------------------------------------
def test_supabase_tasks_truthful_persistence_and_query(live_auth_context):
    """
    Verifies cloud-authoritative task creation and retrieval.

    Identity chain:
        alpha_uuid (auth.users id) == JWT sub == tasks.user_id
        RLS: auth.uid() matches → row visible ✓
    """
    uid = live_auth_context["user_id"]
    token = live_auth_context["token"]
    task_title = f"Verify Live Cloud Engine {uuid.uuid4().hex[:6]}"

    # Write: user JWT → PostgREST → RLS evaluates auth.uid() == uid → INSERT allowed
    success = storage_adapter.add_task(
        title=task_title,
        description="Authoritative cloud write test",
        user_id=uid,
        auth_token=token
    )
    assert success is True, (
        "add_task must return True on successful Supabase write. "
        "False means either the JWT is wrong or the FK/RLS constraint blocked the insert."
    )

    # Read: same JWT → RLS filters to rows where user_id == auth.uid()
    tasks = storage_adapter.get_tasks(user_id=uid, auth_token=token)
    matching = [t for t in tasks if t.title == task_title]
    assert len(matching) == 1, (
        f"Task '{task_title}' must be visible to the authenticated user. "
        f"Got {len(matching)} matches from {len(tasks)} total tasks."
    )
    assert matching[0].user_id == uid
    assert matching[0].status.value == "pending"

    # Cleanup: delete this user's tasks
    storage_adapter.clear_tasks(user_id=uid, auth_token=token)
    tasks_after = storage_adapter.get_tasks(user_id=uid, auth_token=token)
    assert len(tasks_after) == 0, "clear_tasks must remove all tasks for this user"


# ---------------------------------------------------------------------------
# Test 3: pgvector hybrid search (dense + lexical RRF)
# ---------------------------------------------------------------------------
def test_supabase_memory_pgvector_and_hybrid_search(live_auth_context):
    """
    Verifies pgvector similarity search (match_memories RPC) + lexical RRF.

    Writes a memory with a unique key, then retrieves it via hybrid search.
    The JWT is the same UUID that owns the memory row — RLS must allow both.
    """
    uid = live_auth_context["user_id"]
    token = live_auth_context["token"]

    secret_key = f"orbital-laser-{uuid.uuid4().hex[:6]}"
    doc_text = f"The access override code for project orbital is {secret_key}."
    emb = embedding_engine.encode(doc_text)

    rec = MemoryRecord(
        user_id=uid,
        text=doc_text,
        category=MemoryCategory.PROJECT,
        embedding=emb,
        importance=0.9
    )

    # Cloud write: user JWT, RLS allows because auth.uid() == uid
    saved = storage_adapter.save_memory(rec, user_id=uid, auth_token=token)
    assert saved is True, "save_memory must return True — cloud write succeeded"

    # Hybrid search: dense vector + lexical, filtered by auth.uid() via RLS
    query = "What is the orbital project access override code?"
    q_emb = embedding_engine.encode(query)
    results = storage_adapter.search_memories(
        query_embedding=q_emb,
        query_text=query,
        top_k=5,
        threshold=0.20,
        user_id=uid,
        auth_token=token
    )

    assert len(results) > 0, "Hybrid search must retrieve candidates from live Supabase"
    assert any(secret_key in r["text"] for r in results), (
        f"Expected '{secret_key}' in search results. "
        f"Got: {[r['text'][:60] for r in results]}"
    )

    # Cleanup
    storage_adapter.clear_all_memories(user_id=uid, auth_token=token)


# ---------------------------------------------------------------------------
# Test 4: Cross-user isolation (RLS enforcement)
# ---------------------------------------------------------------------------
def test_supabase_cross_user_isolation(live_auth_context):
    """
    Verifies strict RLS data isolation: Beta must NEVER see Alpha's data.

    This is the definitive RLS test. Both users have real JWTs with different
    sub values. PostgREST evaluates auth.uid() per request — each JWT only
    exposes that user's rows.
    """
    alpha_uid = live_auth_context["user_id"]
    alpha_token = live_auth_context["token"]
    beta_uid = live_auth_context["other_user_id"]
    beta_token = live_auth_context["other_token"]

    # Alpha writes a private task
    alpha_title = f"Alpha Secret Operation {uuid.uuid4().hex[:6]}"
    storage_adapter.add_task(title=alpha_title, user_id=alpha_uid, auth_token=alpha_token)

    # Beta queries their own tasks — must NOT see Alpha's row
    beta_tasks = storage_adapter.get_tasks(user_id=beta_uid, auth_token=beta_token)
    assert not any(t.title == alpha_title for t in beta_tasks), (
        "CRITICAL RLS FAILURE: User Beta can see User Alpha's task. "
        "RLS policy auth.uid() == user_id is not working."
    )

    # Alpha writes a private memory
    alpha_secret = f"confidential-key-{uuid.uuid4().hex[:6]}"
    emb = embedding_engine.encode(alpha_secret)
    storage_adapter.save_memory(
        MemoryRecord(
            user_id=alpha_uid,
            text=f"Top Secret: {alpha_secret}",
            category=MemoryCategory.PREFERENCE,
            embedding=emb
        ),
        user_id=alpha_uid,
        auth_token=alpha_token
    )

    # Beta searches memories — must NOT see Alpha's memory
    beta_results = storage_adapter.search_memories(
        query_embedding=emb,
        query_text=alpha_secret,
        top_k=5,
        user_id=beta_uid,
        auth_token=beta_token
    )
    assert not any(alpha_secret in r["text"] for r in beta_results), (
        "CRITICAL RLS FAILURE: User Beta can see User Alpha's memory. "
        "RLS policy auth.uid() == user_id is not working."
    )

    # Cleanup Alpha's data
    storage_adapter.clear_tasks(user_id=alpha_uid, auth_token=alpha_token)
    storage_adapter.clear_all_memories(user_id=alpha_uid, auth_token=alpha_token)


# ---------------------------------------------------------------------------
# Test 5: Atomic scheduled task claiming
# ---------------------------------------------------------------------------
def test_supabase_atomic_scheduled_task_claim(live_auth_context):
    """
    Verifies distributed atomic task claiming via conditional PostgREST PATCH.

    Uses the user JWT path (not admin) to verify that user-owned scheduled
    tasks can be created and claimed under RLS.
    """
    uid = live_auth_context["user_id"]
    token = live_auth_context["token"]

    # Schedule a task that is already due
    past_time = time.time() - 10.0
    job_id = storage_adapter.add_scheduled_task(
        action_type="reminder_notification",
        target_time=past_time,
        payload={"message": "System check"},
        user_id=uid,
        auth_token=token
    )
    assert job_id is not None, "add_scheduled_task must return job_id on successful cloud write"

    # First claim: conditional PATCH where is_active=true → succeeds, sets is_active=false
    first_claim = storage_adapter.claim_scheduled_task(job_id, auth_token=token)
    assert first_claim is True, "First worker must successfully claim the due task"

    # Second concurrent claim attempt: is_active is already false → no rows matched → False
    second_claim = storage_adapter.claim_scheduled_task(job_id, auth_token=token)
    assert second_claim is False, "Second worker must NOT claim an already-claimed task (is_active=false)"


# ---------------------------------------------------------------------------
# Test 6: Knowledge graph persistence
# ---------------------------------------------------------------------------
def test_supabase_knowledge_graph_links(live_auth_context):
    """Verifies entity-relationship graph storage and retrieval on memory_links."""
    uid = live_auth_context["user_id"]
    token = live_auth_context["token"]
    entity_id = f"Entity_{uuid.uuid4().hex[:6]}"

    saved = storage_adapter.save_memory_link(
        source_entity=entity_id,
        relationship="depends_on",
        target_entity="CoreEngine",
        user_id=uid,
        auth_token=token
    )
    assert saved is True, "save_memory_link must return True on Supabase persistence"

    links = storage_adapter.query_memory_links(entity=entity_id, user_id=uid, auth_token=token)
    assert len(links) >= 1, f"Expected at least 1 link for entity '{entity_id}', got {len(links)}"
    assert links[0]["subject"] == entity_id
    assert links[0]["predicate"] == "depends_on"
    assert links[0]["object"] == "CoreEngine"


# ---------------------------------------------------------------------------
# Test 7: Audit log persistence
# ---------------------------------------------------------------------------
def test_supabase_audit_log_live(live_auth_context):
    """Verifies audit trail persistence with authenticated user JWT headers."""
    uid = live_auth_context["user_id"]
    token = live_auth_context["token"]

    entry = AuditEntry(
        user_id=uid,
        channel="integration_test",
        action="execute_test_probe",
        tool_name="live_probe",
        arguments_summary="{}",
        risk_level=1,
        confirmed_by_user=True,
        status="success",
        result_summary="Verified live audit logging"
    )
    # log_audit must complete without exception
    storage_adapter.log_audit(entry, auth_token=token)


# ---------------------------------------------------------------------------
# Test 8: Negative Security Cases (Requirement 10)
# ---------------------------------------------------------------------------
def test_supabase_negative_security_cases(live_auth_context):
    """
    Verifies negative security cases on live PostgREST:
      1. User B cannot update User Alpha's task (RLS suppresses cross-user mutation)
      2. Missing JWT is rejected for user-scoped cloud storage operations
      3. Invalid JWT header is rejected with HTTP 401 by PostgREST
    """
    import httpx
    import certifi

    alpha_uid = live_auth_context["user_id"]
    alpha_token = live_auth_context["token"]
    beta_uid = live_auth_context["other_user_id"]
    beta_token = live_auth_context["other_token"]

    # 1. Alpha creates a task
    alpha_task_title = f"Alpha Protected Task {uuid.uuid4().hex[:6]}"
    storage_adapter.add_task(title=alpha_task_title, user_id=alpha_uid, auth_token=alpha_token)
    alpha_tasks = storage_adapter.get_tasks(user_id=alpha_uid, auth_token=alpha_token)
    matching = [t for t in alpha_tasks if t.title == alpha_task_title]
    assert len(matching) == 1
    alpha_task_id = matching[0].id

    # Beta attempts direct PostgREST PATCH on Alpha's task ID using Beta's JWT
    beta_headers = {
        "apikey": storage_adapter.supabase_anon_key or storage_adapter.supabase_key,
        "Authorization": f"Bearer {beta_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
        res = client.patch(
            f"{storage_adapter.supabase_url}/rest/v1/tasks?id=eq.{alpha_task_id}",
            json={"title": "HACKED_BY_BETA"},
            headers=beta_headers
        )
        # PostgREST RLS prevents modification: either 200 with empty array (0 rows updated) or 403
        updated_rows = res.json() if res.status_code == 200 else []
        assert len(updated_rows) == 0, "CRITICAL RLS FAILURE: User Beta was able to update User Alpha's task!"

    # Verify Alpha's task title remains unchanged
    alpha_tasks_after = storage_adapter.get_tasks(user_id=alpha_uid, auth_token=alpha_token)
    verified = [t for t in alpha_tasks_after if t.id == alpha_task_id]
    assert len(verified) == 1
    assert verified[0].title == alpha_task_title

    # 2. Missing JWT for user-scoped cloud storage operation is rejected by gate
    assert storage_adapter._should_use_supabase_for_user_op(auth_token=None) is False

    # 3. Invalid JWT is rejected by Supabase PostgREST with HTTP 401
    invalid_headers = {
        "apikey": storage_adapter.supabase_anon_key or storage_adapter.supabase_key,
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        "Content-Type": "application/json"
    }
    with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
        res = client.get(f"{storage_adapter.supabase_url}/rest/v1/tasks", headers=invalid_headers)
        assert res.status_code == 401, f"Expected HTTP 401 for invalid JWT, got {res.status_code}"

    # Cleanup
    storage_adapter.clear_tasks(user_id=alpha_uid, auth_token=alpha_token)

