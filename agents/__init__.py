"""
JARVIS V2 Agents Package
Exports all modular and specialized agents.
"""
from agents.base_agent import BaseAgent
from agents.conversation_agent import ConversationAgent, CodingAgent, ResearchAgent, VisionAgent
from agents.document_agent import DocumentAgent
from agents.email_agent import EmailAgent
from agents.calendar_agent import CalendarAgent
from agents.task_agent import TaskAgent
from agents.browser_agent import BrowserAgent
from agents.computer_agent import ComputerAgent
from agents.discord_agent import discord_agent

__all__ = [
    "BaseAgent",
    "ConversationAgent",
    "CodingAgent",
    "ResearchAgent",
    "VisionAgent",
    "DocumentAgent",
    "EmailAgent",
    "CalendarAgent",
    "TaskAgent",
    "BrowserAgent",
    "ComputerAgent",
    "discord_agent"
]
