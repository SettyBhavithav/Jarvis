from typing import List, Dict, Any, Generator, Optional
try:
    import ollama
except ImportError:
    ollama = None

from core.config import config
from core.schemas import ChatMessage, ModelResponse, ToolCall
from models.providers.base_provider import BaseProvider

class OllamaProvider(BaseProvider):
    def __init__(self):
        self.default_model = config.OFFLINE_MODEL

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    def generate(self, messages: List[ChatMessage], model: Optional[str] = None, extra_kwargs: Optional[Dict[str, Any]] = None) -> str:
        if not ollama:
            raise RuntimeError("Ollama library is not installed in this environment.")
        model_name = model or self.default_model
        res = ollama.chat(model=model_name, messages=self._format_messages(messages))
        return res['message']['content']

    def generate_with_tools(self, messages: List[ChatMessage], model: Optional[str] = None, tools: List[Dict[str, Any]] = None, extra_kwargs: Optional[Dict[str, Any]] = None) -> ModelResponse:
        if not ollama:
            raise RuntimeError("Ollama library is not installed in this environment.")
        model_name = model or self.default_model
        formatted = self._format_messages(messages)
        try:
            res = ollama.chat(model=model_name, messages=formatted, tools=tools)
            msg = res.get('message', {})
            tool_calls = None
            if msg.get('tool_calls'):
                tool_calls = []
                for i, tc in enumerate(msg['tool_calls']):
                    fn = tc.get('function', {})
                    tool_calls.append(ToolCall(
                        id=f"ollama_tc_{i}",
                        name=fn.get('name', ''),
                        arguments=fn.get('arguments', {})
                    ))
            return ModelResponse(content=msg.get('content'), tool_calls=tool_calls)
        except Exception:
            content = self.generate(messages, model_name, extra_kwargs)
            return ModelResponse(content=content, tool_calls=None)

    def stream_generate(self, messages: List[ChatMessage], model: Optional[str] = None, extra_kwargs: Optional[Dict[str, Any]] = None) -> Generator[str, None, None]:
        model_name = model or self.default_model
        stream = ollama.chat(model=model_name, messages=self._format_messages(messages), stream=True)
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                yield chunk['message']['content']

