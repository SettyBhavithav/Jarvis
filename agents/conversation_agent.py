"""
JARVIS V2 - Specialized Agents Package
Specialized agents leveraging the central orchestrator and model gateway.
"""
from typing import List, Generator
from core.schemas import ChatMessage, MessageRole
from agents.base_agent import BaseAgent
from core.orchestrator import orchestrator
from tools.registry import tool_registry

class ConversationAgent(BaseAgent):
    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        return orchestrator.execute_turn(prompt, history, channel="voice")

class CodingAgent(BaseAgent):
    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        enhanced_prompt = f"You are Jarvis Coding Specialist. Write high-quality, production-ready, clean code for:\n{prompt}"
        return orchestrator.execute_turn(enhanced_prompt, history, channel="voice")

class ResearchAgent(BaseAgent):
    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        # Synthesizes research with source verification
        enhanced_prompt = f"Conduct in-depth research on this topic with clear citations and structured findings:\n{prompt}"
        return orchestrator.execute_turn(enhanced_prompt, history, channel="voice")

class VisionAgent(BaseAgent):
    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        result = tool_registry.execute_tool("vision_analyze_screen", {"question": prompt})
        yield str(result)
