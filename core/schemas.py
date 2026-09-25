"""
JARVIS V2 - Core Data Schemas
Pydantic contracts for sessions, messages, plans, memory, and audit logs.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import IntEnum, Enum
from pydantic import BaseModel, Field

class RiskLevel(IntEnum):
    LEVEL_0 = 0  # Conversational / informational
    LEVEL_1 = 1  # Read-only queries (system diagnostics, calendar list)
    LEVEL_2 = 2  # Low-risk automation (open app, search web, media toggle)
    LEVEL_3 = 3  # Sensitive external actions (send email, WhatsApp file, delete task) -> REQUIRES CONFIRMATION
    LEVEL_4 = 4  # Critical system actions (shutdown, reboot, workstation lock) -> REQUIRES CONFIRMATION

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class ChatMessage(BaseModel):
    role: MessageRole
    content: Optional[str] = ""
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryCategory(str, Enum):
    GENERAL = "general"
    PREFERENCE = "preference"
    PROJECT = "project"
    CONTACT = "contact"
    HABIT = "habit"
    PERSONAL = "personal"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    TASK_PATTERN = "task_pattern"

DEFAULT_SYSTEM_USER_UUID = "a0000000-0000-0000-0000-000000000001"

class ModelResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None

class MemoryRecord(BaseModel):
    id: Optional[str] = None
    user_id: str = DEFAULT_SYSTEM_USER_UUID
    text: str
    category: MemoryCategory = MemoryCategory.GENERAL
    embedding: Optional[List[float]] = None
    importance: float = 0.5
    access_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: Optional[datetime] = None

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskItem(BaseModel):
    id: Optional[str] = None
    user_id: str = DEFAULT_SYSTEM_USER_UUID
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class PlanStep(BaseModel):
    step_number: int
    description: str
    tool_name: Optional[str] = None
    tool_arguments: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LEVEL_0
    requires_confirmation: bool = False
    status: str = "pending"  # pending, executing, verified, failed
    result: Optional[Any] = None

class Plan(BaseModel):
    goal: str
    steps: List[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed: bool = False

class AuditEntry(BaseModel):
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = DEFAULT_SYSTEM_USER_UUID
    channel: str  # "voice", "discord", "api"
    action: str
    tool_name: Optional[str] = None
    arguments_summary: str
    risk_level: int
    confirmed_by_user: bool
    status: str  # "success", "failed", "denied"
    result_summary: Optional[str] = None

