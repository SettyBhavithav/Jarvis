"""
JARVIS V2 - Base Tool Interface
Pydantic-typed tool contract with risk level, timeout, retries, and action verification.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel
from core.schemas import RiskLevel

class BaseTool(ABC):
    name: str
    description: str
    risk_level: RiskLevel = RiskLevel.LEVEL_1
    args_schema: Type[BaseModel]
    timeout_seconds: float = 20.0
    max_retries: int = 1

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Executes the tool logic."""
        pass

    def verify(self, execution_result: Any) -> bool:
        """Verifies if the action achieved its desired state. Defaults to True if result is not None/Error."""
        if execution_result is None:
            return False
        if isinstance(execution_result, str) and execution_result.lower().startswith("failed"):
            return False
        return True
