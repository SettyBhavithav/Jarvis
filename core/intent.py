"""
JARVIS V2 - Intelligent Intent & Task Complexity Classifier
Categorizes user goals into direct conversation, fast single tools, multimodal vision,
or multi-step tasks requiring the neural Planner.
"""
from enum import Enum
from typing import Dict, Any, Optional

class IntentType(str, Enum):
    CONVERSATION = "conversation"
    DETERMINISTIC_TOOL = "deterministic_tool"
    MULTIMODAL = "multimodal"
    COMPLEX_TASK = "complex_task"
    SENSITIVE_ACTION = "sensitive_action"

class IntentClassifier:
    """Pre-planner classifier distinguishing simple questions, single tools, and multi-step plans."""

    DETERMINISTIC_FAST_PATTERNS = [
        "what time is it", "current time", "what's the time",
        "cpu usage", "system status", "battery level", "pc health",
        "pause music", "resume music", "next track", "skip song",
        "mute volume", "mute audio", "unmute",
        "minimize windows", "show desktop",
        "show tasks", "view tasks", "clear tasks",
        "upcoming events", "my schedule"
    ]

    COMPLEX_CONJUNCTIONS = [
        " and then ", " after that ", " next ", " then ",
        " first ", " also ", " compare ", " research "
    ]

    def classify(self, text: str) -> IntentType:
        txt = text.lower().strip()

        # 1. Check for multimodal requests (screen, visual, audio analysis)
        if any(w in txt for w in ["look at my screen", "what's on my screen", "see this", "capture screen", "screenshot"]):
            return IntentType.MULTIMODAL

        # 2. Check for critical sensitive actions requiring gatekeeper
        if any(w in txt for w in ["shutdown", "shut down", "restart pc", "lock workstation", "lock screen", "delete all"]):
            return IntentType.SENSITIVE_ACTION

        # 3. Check for simple single deterministic tools
        if any(txt == p or txt.startswith(p) for p in self.DETERMINISTIC_FAST_PATTERNS):
            return IntentType.DETERMINISTIC_TOOL

        # 4. Check for complex multi-step goals
        has_conjunction = any(c in txt for c in self.COMPLEX_CONJUNCTIONS)
        action_verbs = [
            "research", "summarize", "find", "extract", "email", "send",
            "create task", "add task", "schedule", "calendar", "compare", "verify"
        ]
        action_count = sum(1 for v in action_verbs if v in txt)

        if (has_conjunction and action_count >= 2) or action_count >= 3:
            return IntentType.COMPLEX_TASK

        # 5. Default to conversational turn
        return IntentType.CONVERSATION

    def is_complex_task(self, text: str) -> bool:
        return self.classify(text) == IntentType.COMPLEX_TASK

intent_classifier = IntentClassifier()
