"""
JARVIS V2 - Desktop Vision & Multimodal Tools
Screen awareness using Gemini 2.0 Flash / NVIDIA NIM Llama 3.2 Vision and Phi-4 Multimodal.
"""
import os
import base64
import time
from pydantic import BaseModel, Field
from core.config import config
from core.schemas import RiskLevel
from tools.base_tool import BaseTool

class ScreenVisionArgs(BaseModel):
    question: str = Field(default="Describe what you see on my screen in detail.", description="The question or error to analyze")

class DesktopVisionTool(BaseTool):
    name = "vision_analyze_screen"
    description = "Captures the user's desktop screen and performs visual reasoning or error diagnosis."
    risk_level = RiskLevel.LEVEL_1
    args_schema = ScreenVisionArgs

    def execute(self, question: str = "Describe what you see on my screen in detail.", **kwargs) -> str:
        print("👁️ [Vision: Capturing Screen...]")
        tmp_path = "_vision_tmp.jpg"
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            screenshot = screenshot.resize((1280, 720))
            screenshot.save(tmp_path, "JPEG", quality=75)

            with open(tmp_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            # Try Gemini first if available
            from models.gateway import model_gateway
            gemini = model_gateway.providers.get("gemini")
            if gemini and gemini.client:
                from google.genai import types
                res = gemini.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        types.Part.from_bytes(data=base64.b64decode(img_b64), mime_type="image/jpeg"),
                        question
                    ]
                )
                return res.text or "I observed the screen, sir, but obtained no description."

            # Fallback to NIM Vision
            nim = model_gateway.providers.get("nim")
            if nim and nim.client:
                res = nim.client.chat.completions.create(
                    model=config.VISION_MODEL,
                    messages=[{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "text", "text": question}
                    ]}],
                    max_tokens=1024
                )
                return res.choices[0].message.content

            return "Sir, no vision model is currently configured with a valid API key."
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return f"Vision analysis failed: {e}"

class AudioVisionTool(BaseTool):
    name = "multimodal_audio_vision"
    description = "Captures a screenshot and 5 seconds of ambient audio, sending both to Phi-4 Multimodal."
    risk_level = RiskLevel.LEVEL_1
    args_schema = ScreenVisionArgs

    def execute(self, question: str = "Analyze what you hear and see.", **kwargs) -> str:
        tmp_img = "_phi_tmp.jpg"
        try:
            from PIL import ImageGrab
            import speech_recognition as sr
            # 1. Capture Screen
            screenshot = ImageGrab.grab()
            screenshot = screenshot.resize((1280, 720))
            screenshot.save(tmp_img, "JPEG", quality=75)
            with open(tmp_img, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            os.remove(tmp_img)

            # 2. Record 5s Ambient Audio
            print("🎤 [Recording 5s Ambient Audio for Phi-4...]")
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.2)
                audio = r.record(source, duration=5)
            audio_b64 = base64.b64encode(audio.get_wav_data()).decode("utf-8")

            from models.gateway import model_gateway
            nim = model_gateway.providers.get("nim")
            if nim and nim.client:
                res = nim.client.chat.completions.create(
                    model=config.AUDIO_VISION_MODEL,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
                    ]}],
                    max_tokens=1024
                )
                return res.choices[0].message.content

            return "Sir, Phi-4 Multimodal requires a valid NVIDIA NIM API key."
        except Exception as e:
            return f"Multimodal analysis failed: {e}"
