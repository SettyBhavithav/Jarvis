"""
JARVIS V2 - Evaluation Benchmark Suite
Validates end-to-end agent planning, ReAct loop execution, model routing, specialized agents,
idempotency, and EventBus event flow.
"""
import pytest
from core.planner import AgentPlanner
from core.orchestrator import orchestrator
from models.router import ModelRouter, RouteDecision
from tools.registry import tool_registry
from security.policy import policy_engine
from core.events import event_bus
from agents import (
    ConversationAgent,
    CodingAgent,
    ResearchAgent,
    VisionAgent,
    DocumentAgent,
    EmailAgent,
    CalendarAgent,
    TaskAgent,
    BrowserAgent,
    ComputerAgent
)

def test_multi_step_planner_decomposition():
    """Validates that multi-step goals are properly decomposed into plan steps."""
    planner = AgentPlanner()
    complex_prompt = "First check system stats, then create a task to review system logs"
    plan = planner.create_plan(complex_prompt)
    assert len(plan.steps) >= 1
    assert all(hasattr(s, "tool_name") for s in plan.steps)
    assert all(hasattr(s, "description") for s in plan.steps)

def test_planner_execution_concise_updates():
    """Validates that plan execution emits concise updates without exposing internal chain of thought."""
    planner = AgentPlanner()
    plan = planner.create_plan("Check system performance and stats")
    result = planner.execute_plan(plan)
    assert "Sir, here is the outcome of your request:" in result
    assert "•" in result

def test_action_idempotency():
    """Validates that non-idempotent actions cannot be executed twice within the idempotency window."""
    unique_task = "Idempotency validation task - alpha"
    res1 = tool_registry.execute_tool("task_add", {"title": unique_task}, user_id="idemp_user")
    assert "added" in res1.lower()

    # Second immediate execution with identical args must be suppressed
    res2 = tool_registry.execute_tool("task_add", {"title": unique_task}, user_id="idemp_user")
    assert "Duplicate Action Suppressed" in res2

def test_event_bus_wiring():
    """Validates that EventBus publishes and delivers typed events across components."""
    received = []
    def handler(ev):
        received.append(ev.event_name)

    event_bus.subscribe("AgentStepStarted", handler)
    planner = AgentPlanner()
    plan = planner.create_plan("Check system status")
    planner.execute_plan(plan)
    assert "AgentStepStarted" in received
    event_bus.unsubscribe("AgentStepStarted", handler)

def test_model_router_benchmark():
    """Evaluates that queries are routed to optimal models based on capability requirements."""
    router = ModelRouter()
    
    # Coding query
    code_route = router.route("Write a python script with asyncio to scrape quotes")
    assert code_route.intent == "coding"
    assert code_route.target_provider in ["deepseek", "nim", "groq", "ollama"]

    # Vision query
    vision_route = router.route("Can you look at my screen and tell me what error is showing?")
    assert vision_route.requires_vision is True

    # Fast conversational query
    fast_route = router.route("Hey what's the weather like today?")
    assert fast_route.intent in ["chat", "conversation", "general", "offline_fallback"]

def test_specialized_agents_instantiation():
    """Validates that all specialized agents initialize properly and expose execution interfaces."""
    agents = [
        ConversationAgent(),
        CodingAgent(),
        ResearchAgent(),
        VisionAgent(),
        DocumentAgent(),
        EmailAgent(),
        CalendarAgent(),
        TaskAgent(),
        BrowserAgent(),
        ComputerAgent()
    ]
    for agent in agents:
        assert hasattr(agent, "run")

def test_computer_agent_direct_tools():
    """Validates ComputerAgent diagnostic methods."""
    comp_agent = ComputerAgent()
    stats = comp_agent.get_system_stats()
    assert stats.get("success") is True
    assert "CPU Load" in stats.get("data", "")

def test_task_agent_lifecycle():
    """Validates TaskAgent task creation and listing."""
    task_agent = TaskAgent()
    create_res = task_agent.create_task("Evaluation benchmark task unique", "Testing TaskAgent", "high")
    assert create_res.get("success") is True
    
    list_res = task_agent.list_tasks(status="pending")
    assert list_res.get("success") is True
    assert any("Evaluation benchmark task" in t.get("title", "") for t in list_res.get("tasks", []))


def test_policy_engine_escalation():
    """Validates that Level 3 and 4 actions always enforce confirmation."""
    level0 = policy_engine.evaluate_action("system_get_stats", {})
    assert level0.requires_confirmation is False

    level3 = policy_engine.evaluate_action("communication_gmail_send", {"to": "test@example.com", "send_immediately": True})
    assert level3.requires_confirmation is True

    level4 = policy_engine.evaluate_action("system_shutdown", {})
    assert level4.requires_confirmation is True
    assert level4.risk_level.value >= 3
