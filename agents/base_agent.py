"""
JARVIS V2 - Base Agent Interface
"""
from abc import ABC, abstractmethod
from typing import List, Generator
from core.schemas import ChatMessage

class BaseAgent(ABC):
    @abstractmethod
    def run(self, prompt: str, history: List[ChatMessage]) -> Generator[str, None, None]:
        pass
