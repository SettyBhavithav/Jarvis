"""
Unit Tests for JARVIS V2 - Tool Registry & Execution
"""
import pytest
from tools.registry import tool_registry

def test_tool_registry_contains_core_tools():
    tool_names = [t.name for t in tool_registry.list_tools()]
    assert "system_get_stats" in tool_names
    assert "media_toggle_play_pause" in tool_names
    assert "task_add" in tool_names
    assert "task_list" in tool_names
    assert "communication_gmail_send" in tool_names
    assert "browser_scrape" in tool_names
    assert "vision_analyze_screen" in tool_names


def test_system_stats_tool_execution():
    result = tool_registry.execute_tool("system_get_stats", {}, user_id="test_user", channel="voice")
    assert "CPU Load:" in result
    assert "RAM Usage:" in result

def test_task_tools_execution():
    add_res = tool_registry.execute_tool("task_add", {"title": "Verify JARVIS V2 Deployment"}, user_id="test_user", channel="voice")
    assert "added 'Verify JARVIS V2 Deployment'" in add_res

    list_res = tool_registry.execute_tool("task_list", {}, user_id="test_user", channel="voice")
    assert "Verify JARVIS V2 Deployment" in list_res
