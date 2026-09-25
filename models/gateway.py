"""
JARVIS V2 - Unified Intelligent Model Gateway
Central dispatching layer with health monitoring, automatic retries, circuit breaker, and offline fallback.
"""
import time
from typing import List, Dict, Any, Generator, Optional
from core.config import config
from core.schemas import ChatMessage, ModelResponse, ToolCall
from models.router import model_router, RouteDecision

from models.health import provider_health
from models.providers.groq_provider import GroqProvider
from models.providers.nim_provider import NIMProvider
from models.providers.deepseek_provider import DeepSeekProvider
from models.providers.gemini_provider import GeminiProvider
from models.providers.ollama_provider import OllamaProvider

class ModelGateway:
    def __init__(self):
        self.router = model_router
        self.health = provider_health
        self.providers = {
            "groq": GroqProvider(),
            "nim": NIMProvider(),
            "deepseek": DeepSeekProvider(),
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider()
        }

    def check_safety(self, prompt: str) -> bool:
        """Evaluates safety using Llama-Guard-4 via NIM if available."""
        if not config.ENABLE_LLAMA_GUARD:
            return True
        try:
            nim = self.providers.get("nim")
            if nim and nim.client:
                res = nim.client.chat.completions.create(
                    model=config.SAFETY_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=10
                )
                txt = res.choices[0].message.content.strip().lower()
                if "unsafe" in txt:
                    return False
        except Exception as e:
            print(f"[Safety Filter Warning]: {e}")
        return True

    def _get_target_model(self, prov_name: str, primary_provider: str, primary_model: str, intent: str = "chat") -> str:
        """Determines target model, prioritizing NVIDIA NIM as the primary backup provider."""
        if prov_name == primary_provider:
            return primary_model

        if prov_name == "nim":
            if intent == "coding":
                return config.NIM_BACKUP_CODE_MODEL
            elif intent == "reasoning":
                return config.NIM_BACKUP_REASONING_MODEL
            elif intent == "vision":
                return config.NIM_BACKUP_VISION_MODEL
            return config.NIM_BACKUP_CHAT_MODEL

        if prov_name == "groq":
            return config.FAST_CHAT_MODEL
        if prov_name == "deepseek":
            return config.CODING_MODEL if intent == "coding" else config.REASONING_MODEL
        if prov_name == "gemini":
            return "gemini-2.0-flash"
        return config.OFFLINE_MODEL

    def generate(
        self,
        messages: List[ChatMessage],
        route: Optional[RouteDecision] = None,
        json_mode: bool = False,
        extra_kwargs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generates a complete response with provider fallback, prioritizing NIM as backup."""
        if not messages:
            return ""

        last_user_msg = messages[-1].content if messages[-1].role.value == "user" else ""
        chosen_route = route or self.router.classify_and_route(last_user_msg)
        primary_provider = chosen_route.target_provider
        model_name = chosen_route.model_name
        intent = getattr(chosen_route, "intent", "chat")

        # Cascade order: Primary -> NIM (Backup) -> Groq -> DeepSeek -> Gemini -> Ollama
        candidate_order = list(dict.fromkeys([primary_provider, "nim", "groq", "deepseek", "gemini", "ollama"]))

        merged_kwargs = dict(extra_kwargs or {})
        if json_mode:
            merged_kwargs["response_format"] = {"type": "json_object"}

        for prov_name in candidate_order:
            if not self.health.is_available(prov_name):
                continue

            provider = self.providers.get(prov_name)
            if not provider:
                continue

            target_model = self._get_target_model(prov_name, primary_provider, model_name, intent)

            start_time = time.time()
            try:
                # JSON mode is specifically supported by OpenAI-compatible endpoints
                kwargs = merged_kwargs if prov_name in ["groq", "nim", "deepseek"] else extra_kwargs
                result = provider.generate(messages, target_model, kwargs)
                if result:
                    self.health.record_success(prov_name, time.time() - start_time)
                    return result
            except Exception as e:
                print(f"⚠️ [Provider '{prov_name}' Generate Failed: {e}. Cascading...]")
                self.health.record_failure(prov_name)

        return "Sir, I encountered an error communicating with neural model providers."

    def generate_with_tools(
        self,
        messages: List[ChatMessage],
        tools: List[Dict[str, Any]],
        route: Optional[RouteDecision] = None,
        extra_kwargs: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """Generates response using genuine provider-native tool calling with fallback."""
        if not messages:
            return ModelResponse(content="", tool_calls=None)

        last_user_msg = messages[-1].content if messages[-1].role.value == "user" else ""
        chosen_route = route or self.router.classify_and_route(last_user_msg)
        primary_provider = chosen_route.target_provider
        model_name = chosen_route.model_name
        intent = getattr(chosen_route, "intent", "chat")

        # Cascade order: Primary -> NIM (Backup) -> Groq -> DeepSeek -> Ollama
        candidate_order = list(dict.fromkeys([primary_provider, "nim", "groq", "deepseek", "ollama"]))

        for prov_name in candidate_order:
            if not self.health.is_available(prov_name):
                continue

            provider = self.providers.get(prov_name)
            if not provider:
                continue

            target_model = self._get_target_model(prov_name, primary_provider, model_name, intent)

            start_time = time.time()
            try:
                res = provider.generate_with_tools(messages, target_model, tools, extra_kwargs)
                if res and (res.content or res.tool_calls):
                    self.health.record_success(prov_name, time.time() - start_time)
                    return res
            except Exception as e:
                print(f"⚠️ [Provider '{prov_name}' Tool-Call Failed: {e}. Cascading...]")
                self.health.record_failure(prov_name)

        return ModelResponse(content="Sir, I encountered an issue communicating with neural providers.", tool_calls=None)

    def stream_generate(self, messages: List[ChatMessage], route: Optional[RouteDecision] = None) -> Generator[str, None, None]:

        """Streams tokens from primary provider with seamless fallback down to local Ollama."""
        if not messages:
            return

        last_user_msg = messages[-1].content if messages[-1].role.value == "user" else ""
        chosen_route = route or self.router.classify_and_route(last_user_msg)
        primary_provider = chosen_route.target_provider
        model_name = chosen_route.model_name
        intent = getattr(chosen_route, "intent", "chat")

        # Cascade order: Primary -> NIM (Backup) -> Groq -> Gemini -> Ollama
        candidate_order = list(dict.fromkeys([primary_provider, "nim", "groq", "gemini", "ollama"]))

        for prov_name in candidate_order:
            if not self.health.is_available(prov_name):
                continue

            provider = self.providers.get(prov_name)
            if not provider:
                continue

            target_model = self._get_target_model(prov_name, primary_provider, model_name, intent)

            start_time = time.time()
            try:
                print(f"☁️ [ModelGateway: Routing to {prov_name.upper()} ({target_model})]")
                has_tokens = False
                for token in provider.stream_generate(messages, target_model):
                    has_tokens = True
                    yield token

                if has_tokens:
                    self.health.record_success(prov_name, time.time() - start_time)
                    return
            except Exception as e:
                print(f"⚠️ [Provider '{prov_name}' Failed: {e}. Falling back to next provider...]")
                self.health.record_failure(prov_name)

        # Ultimate safety fallback if all generators failed
        yield "Sir, all cloud neural providers are currently unreachable and the local offline engine reported an error."

# Global Model Gateway Singleton
model_gateway = ModelGateway()
