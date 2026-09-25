"""
JARVIS V2 - Browser Automation Specialist Agent
Handles automated web scraping, search queries, Playwright DOM interactions, and webpage summarization.
"""
from typing import List, Generator
from core.schemas import ChatMessage
from agents.base_agent import BaseAgent
from tools.registry import tool_registry
from core.orchestrator import orchestrator

class BrowserAgent(BaseAgent):
    """Specialized agent for web navigation, live DOM extraction, and web research."""

    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        enhanced_prompt = (
            "You are Jarvis Web Browser Specialist. Extract accurate information from the live internet, "
            "navigate websites when needed, and summarize web content with clear source attribution.\n"
            f"User request: {prompt}"
        )
        return orchestrator.execute_turn(enhanced_prompt, history, channel="text")

    def search_web(self, query: str, max_results: int = 5) -> dict:
        return tool_registry.execute_tool("browser_search", {"query": query, "max_results": max_results})

    def navigate_url(self, url: str) -> dict:
        return tool_registry.execute_tool("browser_navigate", {"url": url})
