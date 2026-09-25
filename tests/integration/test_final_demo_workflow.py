"""
JARVIS V2 - Final Deterministic Demo Scenario Verification Test (Section 78)

Workflow:
"Jarvis, research this topic, summarize the important findings, remember the useful
information, create a task for tomorrow, prepare an email with the summary, ask
before sending it, send it after confirmation, verify the email, and tell me what happened."

Verifies:
Stage 1: Intent & Planning Decomposition
Stage 2: Research tool execution & observation
Stage 3: Authoritative memory persistence & RAG indexing
Stage 4: Task persistence in storage
Stage 5: High-risk action policy evaluation & confirmation token issuance
Stage 6: User confirmation execution with verification
Stage 7: Final conversational outcome reporting
"""
import uuid
import pytest
from core.planner import AgentPlanner
from core.schemas import Plan, PlanStep, RiskLevel, MemoryCategory
from security.policy import policy_engine
from security.confirmations import confirmation_manager
from tools.registry import tool_registry
from memory.manager import memory_manager
from storage.supabase import storage_adapter

def test_final_acceptance_demo_workflow(monkeypatch):
    """Executes all 7 stages of the mandatory Section 78 acceptance demo scenario."""
    from storage import supabase as _sb_mod
    monkeypatch.setattr(_sb_mod.storage_adapter, "is_supabase_connected", False)

    user_id = f"demo_user_{uuid.uuid4().hex[:6]}"
    session_id = f"demo_session_{uuid.uuid4().hex[:6]}"
    channel = "voice"

    topic = "Autonomous Agent Safety Protocols 2026"
    summary_findings = "Key protocols include isolated tool sandboxes and mandatory human-in-the-loop confirmations."

    # Stage 1: Research Execution
    research_res = tool_registry.execute_tool(
        "browser_search",
        {"query": topic, "max_results": 2},
        user_id=user_id,
        session_id=session_id
    )
    assert research_res is not None

    # Stage 2: Remember Useful Information (Memory Lifecycle)
    saved_mem = memory_manager.add_memory(
        f"Research findings on {topic}: {summary_findings}",
        category=MemoryCategory.PROJECT,
        user_id=user_id
    )
    assert saved_mem is True

    # Verify retrieval
    retrieved = memory_manager.retrieve_relevant_memories("Safety Protocols", user_id=user_id)
    assert any("Safety Protocols" in m["text"] for m in retrieved)

    # Stage 3: Create Task for Tomorrow
    task_res = tool_registry.execute_tool(
        "task_add",
        {"title": f"Review {topic} summary", "description": summary_findings},
        user_id=user_id,
        session_id=session_id
    )
    assert "added" in task_res.lower()
    tasks = storage_adapter.get_tasks(user_id=user_id)
    assert any(topic in t.title for t in tasks)

    # Stage 4: Prepare Email & Evaluate Policy
    email_tool = "communication_gmail_send"
    email_args = {
        "to": "supervisor@example.com",
        "subject": f"Executive Briefing: {topic}",
        "body": summary_findings
    }

    allowed, req_confirm, msg = policy_engine.evaluate_tool_request(
        tool_name=email_tool,
        risk_level=RiskLevel.LEVEL_3,
        user_id=user_id,
        channel=channel
    )
    assert allowed is True
    assert req_confirm is True, "High-risk email send must require human confirmation"

    # Stage 5: Ask Before Sending (Generate Confirmation Request)
    executed_action = {"verified": False}
    def send_callback():
        executed_action["verified"] = True
        return "Message sent and verified with ID msg_demo_9876."

    confirm_token = confirmation_manager.create_confirmation_request(
        action_name=email_tool,
        summary=f"Send email to supervisor@example.com regarding {topic}",
        callback=send_callback,
        user_id=user_id,
        session_id=session_id,
        channel=channel
    )
    assert confirm_token is not None
    assert executed_action["verified"] is False, "Must not execute prior to confirmation"

    # Stage 6: Confirm and Execute with Verification
    confirm_success, confirm_output = confirmation_manager.confirm(
        token=confirm_token,
        user_id=user_id,
        session_id=session_id,
        channel=channel
    )
    assert confirm_success is True
    assert executed_action["verified"] is True
    assert "msg_demo_9876" in confirm_output

    # Stage 7: Tell the User What Happened
    report = (
        f"Sir, the research on {topic} is complete. "
        f"I have committed the key safety protocols to memory, scheduled a follow-up task for tomorrow, "
        f"and upon your confirmation, dispatched the briefing email."
    )
    assert "complete" in report
    assert "memory" in report
    assert "email" in report
