"""
JARVIS V2 - Groq LPU Provider
Hyper-fast (300+ tok/s) conversational inference engine.
"""
import json
from typing import List, Dict, Any, Generator, Optional
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
from core.config import config
from core.schemas import ChatMessage, ModelResponse, ToolCall
from models.providers.base_provider import BaseProvider

class GroqProvider(BaseProvider):
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.groq.com/openai/v1", timeout=6.0) if OpenAI and self.api_key and "your_" not in self.api_key else None

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role.value, "content": m.content if m.content is not None else ""}
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.name:
                msg_dict["name"] = m.name
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments)
                        }
                    }
                    for tc in m.tool_calls
                ]
            formatted.append(msg_dict)
        return formatted

    def generate(self, messages: List[ChatMessage], model: str, extra_kwargs: Optional[Dict[str, Any]] = None) -> str:
        if not self.client:
            raise RuntimeError("Groq client not initialized (missing API key).")
        kwargs = {"model": model, "messages": self._format_messages(messages)}
        if extra_kwargs:
            kwargs.update(extra_kwargs)
        res = self.client.chat.completions.create(**kwargs)
        return res.choices[0].message.content or ""

    def generate_with_tools(self, messages: List[ChatMessage], model: str, tools: List[Dict[str, Any]], extra_kwargs: Optional[Dict[str, Any]] = None) -> ModelResponse:
        if not self.client:
            raise RuntimeError("Groq client not initialized (missing API key).")
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": self._format_messages(messages),
            "tools": tools,
            "tool_choice": "auto"
        }
        if extra_kwargs:
            kwargs.update(extra_kwargs)
        res = self.client.chat.completions.create(**kwargs)
        choice = res.choices[0]
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = []
            for tc in choice.message.tool_calls:
                args = {}
                if tc.function.arguments:
                    try:
                        args = json.loads(tc.function.arguments)
                    except Exception:
                        args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args
                ))
        return ModelResponse(
            content=choice.message.content,
            tool_calls=tool_calls
        )

    def stream_generate(self, messages: List[ChatMessage], model: str, extra_kwargs: Optional[Dict[str, Any]] = None) -> Generator[str, None, None]:
        if not self.client:
            raise RuntimeError("Groq client not initialized (missing API key).")
        kwargs = {"model": model, "messages": self._format_messages(messages), "stream": True}
        if extra_kwargs:
            kwargs.update(extra_kwargs)
        stream = self.client.chat.completions.create(**kwargs)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

