"""
JARVIS V2 - Email & Messaging Specialist Agent
Handles Gmail drafting, searching, and sending with strict security verification.
"""
from typing import List, Generator
from core.schemas import ChatMessage
from agents.base_agent import BaseAgent
from tools.registry import tool_registry
from core.orchestrator import orchestrator

class EmailAgent(BaseAgent):
    """Specialized agent for managing Gmail correspondence and communications safely."""

    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        enhanced_prompt = (
            "You are Jarvis Email Specialist. Analyze user request regarding email/messages. "
            "Never send an email without user confirmation. Draft first or query existing messages.\n"
            f"User request: {prompt}"
        )
        return orchestrator.execute_turn(enhanced_prompt, history, channel="text")

    def search_emails(self, query: str = "is:unread", max_results: int = 5) -> dict:
        """Query emails via Gmail tool."""
        return tool_registry.execute_tool("communication_gmail_list", {"query": query, "max_results": max_results})

    def draft_or_send_email(self, to: str, subject: str, body: str, send_immediately: bool = False) -> dict:
        """Create a draft or send email."""
        return tool_registry.execute_tool("communication_gmail_send", {
            "to": to,
            "subject": subject,
            "body": body,
            "send_immediately": send_immediately
        })
