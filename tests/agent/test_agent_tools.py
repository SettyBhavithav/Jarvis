"""
JARVIS V2 - Automated Agent ↔ Tool Compatibility Audit Test
Ensures every tool referenced by any Agent class is registered, has a valid Pydantic schema,
and provides state verification.
"""
import pytest
from pydantic import BaseModel
from tools.registry import tool_registry
from agents.browser_agent import BrowserAgent
from agents.calendar_agent import CalendarAgent
from agents.computer_agent import ComputerAgent
from agents.document_agent import DocumentAgent
from agents.email_agent import EmailAgent
from agents.task_agent import TaskAgent

def test_all_agent_tools_exist_in_registry():
    """Validates that all tools explicitly called by specialized agents are registered in ToolRegistry."""
    expected_agent_tools = [
        "browser_search",
        "browser_navigate",
        "productivity_calendar_list",
        "productivity_calendar_create",
        "system_get_stats",
        "media_volume_control",
        "files_list_directory",
        "communication_gmail_list",
        "communication_gmail_send",
        "task_add",
        "task_list"
    ]

    for tool_name in expected_agent_tools:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"Agent tool '{tool_name}' is NOT registered in ToolRegistry!"
        assert issubclass(tool.args_schema, BaseModel), f"Tool '{tool_name}' lacks a valid Pydantic args_schema!"
        assert hasattr(tool, "verify"), f"Tool '{tool_name}' lacks a verify method!"
        assert hasattr(tool, "risk_level"), f"Tool '{tool_name}' lacks a risk_level definition!"

def test_all_registered_tools_valid_schemas():
    """Ensures every tool registered in the catalog outputs valid OpenAI-compatible schemas."""
    schemas = tool_registry.get_schemas()
    assert len(schemas) >= 20, f"Expected at least 20 registered tools, found {len(schemas)}"

    for s in schemas:
        assert s.get("type") == "function"
        fn = s.get("function", {})
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert fn["parameters"].get("type") == "object"
