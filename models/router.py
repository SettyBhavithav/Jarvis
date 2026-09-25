"""
JARVIS V2 - Intelligent Model Router
Classifies user intent, complexity, tool requirements, and selects optimal AI provider.
"""
from typing import Dict, Any
from pydantic import BaseModel
from core.config import config

class RouteDecision(BaseModel):
    intent: str
    complexity: str  # "low", "medium", "high"
    target_provider: str  # "groq", "nim", "deepseek", "gemini", "ollama"
    model_name: str
    requires_vision: bool = False
    requires_audio_vision: bool = False
    requires_tools: bool = False
    thinking_mode: bool = False

class ModelRouter:
    def route(self, prompt: str) -> RouteDecision:
        """Alias for classify_and_route."""
        return self.classify_and_route(prompt)

    def classify_and_route(self, prompt: str) -> RouteDecision:
        prompt_lower = prompt.lower().strip()

        # 1. Vision Intent
        vision_keywords = ["what's on my screen", "what is on my screen", "look at my screen", "what do you see", "read the screen", "describe the screen", "what's open", "what is this error", "look at this", "what am i looking at", "can you see this"]
        if any(w in prompt_lower for w in vision_keywords):
            return RouteDecision(
                intent="vision",
                complexity="medium",
                target_provider="nim" if config.NIM_VISION_API_KEY or config.NIM_API_KEY else "gemini",
                model_name=config.VISION_MODEL,
                requires_vision=True
            )

        # 2. Audio + Vision Multimodal Intent
        if any(w in prompt_lower for w in ["listen to this", "what song is this", "what do you hear", "listen and look", "what's playing", "analyze what you hear"]):
            return RouteDecision(
                intent="audio_vision",
                complexity="high",
                target_provider="nim",
                model_name=config.AUDIO_VISION_MODEL,
                requires_audio_vision=True
            )

        # 3. Coding & Software Engineering Intent
        coding_keywords = ["code", "script", "python", "html", "debug", "refactor", "function", "regex", "algorithm"]
        if any(w in prompt_lower for w in coding_keywords):
            if config.DEEPSEEK_API_KEY:
                return RouteDecision(
                    intent="coding",
                    complexity="high",
                    target_provider="deepseek",
                    model_name=config.CODING_MODEL,
                    requires_tools=True
                )
            elif config.NIM_QWEN_API_KEY or config.NIM_API_KEY:
                return RouteDecision(
                    intent="coding",
                    complexity="high",
                    target_provider="nim",
                    model_name=config.NIM_BACKUP_CODE_MODEL,
                    requires_tools=True
                )

        # 4. Deep Reasoning / Math Intent
        reasoning_keywords = ["research", "think", "explain why", "complex logic", "proof", "derivation"]
        if any(w in prompt_lower for w in reasoning_keywords):
            if config.DEEPSEEK_API_KEY:
                return RouteDecision(
                    intent="reasoning",
                    complexity="high",
                    target_provider="deepseek",
                    model_name=config.REASONING_MODEL,
                    thinking_mode=True
                )
            elif config.NIM_API_KEY:
                return RouteDecision(
                    intent="reasoning",
                    complexity="high",
                    target_provider="nim",
                    model_name=config.NIM_BACKUP_REASONING_MODEL,
                    thinking_mode=True
                )

        # 5. Fast Conversational Chat (Default)
        if config.GROQ_API_KEY and "your_" not in config.GROQ_API_KEY:
            return RouteDecision(
                intent="chat",
                complexity="low",
                target_provider="groq",
                model_name=config.FAST_CHAT_MODEL
            )
        elif config.NIM_GEMMA_API_KEY or config.NIM_API_KEY:
            return RouteDecision(
                intent="chat",
                complexity="low",
                target_provider="nim",
                model_name=config.NIM_BACKUP_CHAT_MODEL
            )
        elif config.GEMINI_API_KEY and "your_" not in config.GEMINI_API_KEY:
            return RouteDecision(
                intent="chat",
                complexity="low",
                target_provider="gemini",
                model_name="gemini-3.6-flash"
            )

        # 6. Offline Local Brain Fallback
        return RouteDecision(
            intent="offline_fallback",
            complexity="medium",
            target_provider="ollama",
            model_name=config.OFFLINE_MODEL
        )

# Global Router Singleton
model_router = ModelRouter()
