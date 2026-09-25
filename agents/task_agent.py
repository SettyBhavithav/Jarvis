"""
JARVIS V2 - Task & Productivity Specialist Agent
Handles task tracking, todo lists, status updates, and priority queues.
"""
from typing import List, Generator
from core.schemas import ChatMessage
from agents.base_agent import BaseAgent
from tools.registry import tool_registry
from core.orchestrator import orchestrator

class TaskAgent(BaseAgent):
    """Specialized agent for managing user tasks, action items, and productivity workflows."""

    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        enhanced_prompt = (
            "You are Jarvis Task Management Specialist. Help organize user goals into concrete actionable tasks.\n"
            f"User request: {prompt}"
        )
        return orchestrator.execute_turn(enhanced_prompt, history, channel="text")

    def create_task(self, title: str, description: str = "", priority: str = "medium") -> dict:
        result = tool_registry.execute_tool("task_add", {"title": title})
        return {"success": True, "result": result, "title": title}

    def list_tasks(self, status: str = "pending") -> dict:
        result = tool_registry.execute_tool("task_list", {})
        from storage.supabase import storage_adapter
        real_tasks = storage_adapter.get_tasks(status=status)
        return {"success": True, "tasks": [t.model_dump() for t in real_tasks], "result": result}

