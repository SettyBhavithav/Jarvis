"""
JARVIS V2 - ReAct Observation Loop, Self-Correction & State Verification Tests
"""
import pytest
from core.schemas import Plan, PlanStep, RiskLevel
from core.planner import agent_planner
from tools.registry import tool_registry

def test_planner_self_correction_recovery():
    """Verifies that when a primary tool fails, the planner executes an alternative recovery action."""
    step = PlanStep(
        step_number=1,
        description="Search web for live information",
        tool_name="browser_search",
        tool_arguments={"query": "test query"},
        risk_level=RiskLevel.LEVEL_1
    )
    plan = Plan(goal="Search web and fallback if needed", steps=[step])

    # Simulate error and recovery
    recovery_msg = agent_planner._recover_step(
        step=step,
        error_msg="Network timeout connecting to search provider",
        user_id="test_recovery_user",
        channel="text"
    )

    assert step.status == "recovered"
    assert "recovered" in recovery_msg.lower() or "search" in recovery_msg.lower() or "query" in recovery_msg.lower()
    assert step.result is not None

def test_email_failure_recovery_to_task():
    """Verifies that failed email action self-corrects by preserving draft in task list."""
    step = PlanStep(
        step_number=1,
        description="Prepare formal email draft",
        tool_name="communication_gmail_send",
        tool_arguments={"subject": "Critical architecture update", "body": "Notes"},
        risk_level=RiskLevel.LEVEL_3
    )

    recovery_msg = agent_planner._recover_step(
        step=step,
        error_msg="Gmail API 503 Service Unavailable",
        user_id="test_recovery_user",
        channel="text"
    )

    assert step.status == "recovered"
    assert "to-do list" in recovery_msg

def test_tool_state_verification():
    """Verifies tool-specific post-execution verification."""
    add_tool = tool_registry.get_tool("task_add")
    assert add_tool is not None

    res = add_tool.execute(title="Verification testing item")
    verified = add_tool.verify(res)
    assert verified is True

    clear_tool = tool_registry.get_tool("task_clear")
    assert clear_tool is not None
    clear_res = clear_tool.execute()
    assert clear_tool.verify(clear_res) is True
