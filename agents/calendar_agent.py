"""
JARVIS V2 - Calendar & Schedule Specialist Agent
Handles Google Calendar event retrieval, scheduling, and conflict checking.
"""
from typing import List, Generator
from core.schemas import ChatMessage
from agents.base_agent import BaseAgent
from tools.registry import tool_registry
from core.orchestrator import orchestrator

class CalendarAgent(BaseAgent):
    """Specialized agent for managing schedules, appointments, and calendar events."""

    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        enhanced_prompt = (
            "You are Jarvis Calendar Specialist. Assist the user in viewing and managing schedule events.\n"
            f"User request: {prompt}"
        )
        return orchestrator.execute_turn(enhanced_prompt, history, channel="text")

    def list_events(self, days_ahead: int = 7) -> dict:
        """Fetch upcoming calendar events."""
        return tool_registry.execute_tool("productivity_calendar_list", {"days_ahead": days_ahead})

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> dict:
        """Create a new calendar entry."""
        return tool_registry.execute_tool("productivity_calendar_create", {
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "description": description
        })
