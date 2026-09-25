"""
JARVIS V2 - Google Gemini Provider
Multimodal reasoning and fallback intelligence using google-genai.
"""
from typing import List, Dict, Any, Generator, Optional
try:
    from google import genai
except ImportError:
    genai = None

from core.config import config
from core.schemas import ChatMessage, MessageRole
from models.providers.base_provider import BaseProvider

class GeminiProvider(BaseProvider):
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if genai and self.api_key and "your_" not in self.api_key else None

    def generate(self, messages: List[ChatMessage], model: str = "gemini-3.6-flash", extra_kwargs: Optional[Dict[str, Any]] = None) -> str:
        if not self.client:
            raise RuntimeError("Gemini client not initialized.")
        prompt_text = "\n".join([f"{m.role.value}: {m.content}" for m in messages])
        res = self.client.models.generate_content(model=model, contents=prompt_text)
        return res.text or ""

    def stream_generate(self, messages: List[ChatMessage], model: str = "gemini-3.6-flash", extra_kwargs: Optional[Dict[str, Any]] = None) -> Generator[str, None, None]:
        if not self.client:
            raise RuntimeError("Gemini client not initialized.")
        prompt_text = "\n".join([f"{m.role.value}: {m.content}" for m in messages])
        stream = self.client.models.generate_content_stream(model=model, contents=prompt_text)
        for chunk in stream:
            if chunk.text:
                yield chunk.text
