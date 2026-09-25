"""
JARVIS V2 - Event-Driven Architecture
Internal asynchronous and synchronous EventBus with all 17 typed event schemas.
"""
from typing import Dict, List, Callable, Any, Type, Optional
import asyncio
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class BaseEvent(BaseModel):
    event_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)

# 1. WakeWordDetected
class WakeWordDetectedEvent(BaseEvent):
    event_name: str = "WakeWordDetected"
    confidence: float = 0.0

# 2. UserInputReceived
class UserInputReceivedEvent(BaseEvent):
    event_name: str = "UserInputReceived"
    source: str = "voice"  # "voice", "discord", "api"
    text: str = ""
    session_id: str = "session_default"
    user_id: str = "user_default"

# 3. TranscriptionReady
class TranscriptionReadyEvent(BaseEvent):
    event_name: str = "TranscriptionReady"
    text: str = ""
    duration_ms: float = 0.0

# 4. IntentDetected
class IntentDetectedEvent(BaseEvent):
    event_name: str = "IntentDetected"
    intent: str = "general"
    complexity: str = "low"
    target_provider: str = "groq"

# 5. PlanCreated
class PlanCreatedEvent(BaseEvent):
    event_name: str = "PlanCreated"
    goal: str = ""
    steps: List[str] = Field(default_factory=list)

# 6. AgentStarted
class AgentStartedEvent(BaseEvent):
    event_name: str = "AgentStarted"
    agent_name: str = "Orchestrator"
    user_id: str = "user_default"

# 7. AgentStepStarted
class AgentStepStartedEvent(BaseEvent):
    event_name: str = "AgentStepStarted"
    step_number: int = 1
    description: str = ""
    tool_name: Optional[str] = None

# 8. ToolStarted
class ToolStartedEvent(BaseEvent):
    event_name: str = "ToolStarted"
    tool_name: str = ""
    arguments: Dict[str, Any] = Field(default_factory=dict)

# 9. ToolCompleted
class ToolCompletedEvent(BaseEvent):
    event_name: str = "ToolCompleted"
    tool_name: str = ""
    result: Any = None
    success: bool = True

# 10. ToolFailed
class ToolFailedEvent(BaseEvent):
    event_name: str = "ToolFailed"
    tool_name: str = ""
    error: str = ""
    recovery_attempted: bool = False

# 11. VerificationCompleted
class VerificationCompletedEvent(BaseEvent):
    event_name: str = "VerificationCompleted"
    tool_name: str = ""
    verified: bool = True
    details: str = ""

# 12. MemoryCreated
class MemoryCreatedEvent(BaseEvent):
    event_name: str = "MemoryCreated"
    memory_text: str = ""
    category: str = "general"
    importance: float = 0.5

# 13. ResponseGenerated
class ResponseGeneratedEvent(BaseEvent):
    event_name: str = "ResponseGenerated"
    response_length: int = 0
    channel: str = "voice"

# 14. SpeechStarted
class SpeechStartedEvent(BaseEvent):
    event_name: str = "SpeechStarted"
    text: str = ""

# 15. SpeechInterrupted
class SpeechInterruptedEvent(BaseEvent):
    event_name: str = "SpeechInterrupted"
    reason: str = "user_barge_in"

# 16. AgentCompleted
class AgentCompletedEvent(BaseEvent):
    event_name: str = "AgentCompleted"
    agent_name: str = "Orchestrator"
    success: bool = True
    summary: str = ""

# 17. ErrorEvent
class ErrorEvent(BaseEvent):
    event_name: str = "Error"
    error_type: str = "SystemError"
    message: str = ""
    traceback: Optional[str] = None


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[BaseEvent], Any]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[BaseEvent], Any]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[BaseEvent], Any]):
        if event_type in self._subscribers:
            self._subscribers[event_type] = [h for h in self._subscribers[event_type] if h != handler]

    async def publish(self, event: BaseEvent):
        handlers = self._subscribers.get(event.event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"[EventBus Error in {event.event_name}]: {e}")

    def publish_sync(self, event: BaseEvent):
        """Synchronously invokes event handlers, scheduling coroutines on the current loop if available."""
        handlers = self._subscribers.get(event.event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(handler(event))
                        else:
                            loop.run_until_complete(handler(event))
                    except RuntimeError:
                        asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception as e:
                print(f"[EventBus Sync Error in {event.event_name}]: {e}")

# Global EventBus Singleton
event_bus = EventBus()
