"""
JARVIS V2 - Computer & OS Automation Specialist Agent
Handles Windows desktop operations, file browsing, system diagnostics, window management, and hardware controls.
"""
from typing import List, Generator
from core.schemas import ChatMessage
from agents.base_agent import BaseAgent
from tools.registry import tool_registry
from core.orchestrator import orchestrator

class ComputerAgent(BaseAgent):
    """Specialized agent for OS-level automation, system diagnostics, and window/process control."""

    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        enhanced_prompt = (
            "You are Jarvis Computer Control Specialist. Use system tools safely to inspect, "
            "manage windows, monitor CPU/RAM/Battery, and perform desktop tasks.\n"
            f"User request: {prompt}"
        )
        return orchestrator.execute_turn(enhanced_prompt, history, channel="text")

    def get_system_stats(self) -> dict:
        res = tool_registry.execute_tool("system_get_stats", {})
        return {"success": True, "data": res, "stats_string": res}

    def control_volume(self, action: str, level: int = 50) -> dict:
        return tool_registry.execute_tool("media_volume_control", {"action": action, "level": level})

    def list_files(self, target_folder: str = "Desktop") -> dict:
        return tool_registry.execute_tool("files_list_directory", {"target_folder": target_folder})
