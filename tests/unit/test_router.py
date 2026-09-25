"""
Unit Tests for JARVIS V2 - Model Router
"""
import pytest
from models.router import model_router

def test_router_vision_classification():
    decision = model_router.classify_and_route("what is on my screen right now?")
    assert decision.intent == "vision"
    assert decision.requires_vision is True

def test_router_coding_classification():
    decision = model_router.classify_and_route("write a python script to parse logs")
    assert decision.intent == "coding"
    assert decision.requires_tools is True

def test_router_multimodal_classification():
    decision = model_router.classify_and_route("listen to this and look at the chart")
    assert decision.intent == "audio_vision"
    assert decision.requires_audio_vision is True

def test_model_gateway_fallback(monkeypatch):
    """Validates that ModelGateway cascades to fallback provider when primary provider fails."""
    from models.gateway import ModelGateway
    from models.providers.base_provider import BaseProvider
    from core.schemas import ChatMessage, MessageRole

    gateway = ModelGateway()

    class FailingProvider(BaseProvider):
        def generate(self, messages, model, extra_kwargs=None):
            raise ConnectionError("Primary provider connection timeout")
        def stream_generate(self, messages, model, extra_kwargs=None):
            raise ConnectionError("Primary provider stream error")

    class WorkingFallbackProvider(BaseProvider):
        def generate(self, messages, model, extra_kwargs=None):
            return "Fallback model response succeeded"
        def stream_generate(self, messages, model, extra_kwargs=None):
            yield "Fallback response"

    gateway.providers["groq"] = FailingProvider()
    gateway.providers["nim"] = FailingProvider()
    gateway.providers["deepseek"] = FailingProvider()
    gateway.providers["gemini"] = WorkingFallbackProvider()

    res = gateway.generate([ChatMessage(role=MessageRole.USER, content="Hello")])
    assert res == "Fallback model response succeeded"
