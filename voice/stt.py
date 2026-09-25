"""
JARVIS V2 - Hybrid Speech-to-Text Engine
Primary: Groq Cloud LPU (whisper-large-v3-turbo, ~80ms latency, zero RAM footprint).
Fallback: Local faster-whisper on CPU/GPU with VAD filter.
"""
import io
import os
import sys
import torch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import speech_recognition as sr
from typing import Optional
from openai import OpenAI
from core.config import config
from voice.vad import audio_preprocessor

class SpeechToTextEngine:
    def __init__(self):
        self._local_model = None
        self._groq_client: Optional[OpenAI] = None
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 500
        self.recognizer.dynamic_energy_threshold = True

        groq_key = config.GROQ_API_KEY
        if groq_key and "your_" not in groq_key and config.STT_PROVIDER == "groq":
            try:
                self._groq_client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            except Exception as e:
                print(f"[STT: Groq client init error]: {e}")

    def prewarm(self):
        """Initializes cloud STT client or pre-loads local Whisper model."""
        if self._groq_client:
            print(f"🎙️ [STT Engine: Groq '{config.GROQ_STT_MODEL}' Ready (Ultra-low latency Cloud LPU)]")
        else:
            self._ensure_local_model()

    def _ensure_local_model(self):
        """Lazy-loads local faster-whisper only when required to conserve RAM."""
        if self._local_model is None:
            from faster_whisper import WhisperModel
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
            print(f"🎙️ [Loading faster-whisper ({config.VOICE_INPUT_MODEL}) on {device.upper()} ({compute})...]")
            try:
                self._local_model = WhisperModel(config.VOICE_INPUT_MODEL, device=device, compute_type=compute)
            except Exception as e:
                print(f"[STT Warning: Fallback to CPU]: {e}")
                self._local_model = WhisperModel(config.VOICE_INPUT_MODEL, device="cpu", compute_type="int8")
            print("🎙️ [Local STT Engine Ready]")

    def _transcribe_groq(self, audio: sr.AudioData) -> str:
        """Sends captured audio to Groq's whisper-large-v3-turbo in memory."""
        wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
        wav_io = io.BytesIO(wav_bytes)
        wav_io.name = "audio.wav"

        res = self._groq_client.audio.transcriptions.create(
            file=wav_io,
            model=config.GROQ_STT_MODEL,
            response_format="json",
            language="en",
            temperature=0.0
        )
        return getattr(res, "text", "").strip()

    def _transcribe_local(self, audio: sr.AudioData) -> str:
        """Local fallback using faster-whisper and VAD filtering."""
        self._ensure_local_model()
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw, np.int16).flatten().astype(np.float32) / 32768.0

        if config.AUDIO_NORMALIZATION:
            audio_np = audio_preprocessor.normalize_audio(audio_np)

        segments, _ = self._local_model.transcribe(
            audio_np,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=config.VAD_MIN_SILENCE_DURATION_MS)
        )
        return "".join([s.text for s in segments]).strip()

    def listen_and_transcribe(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        self.prewarm()
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
            print("🎙️ [Listening... Speak now!]")
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

                # 1. Primary: Ultra-fast Groq Cloud LPU
                if self._groq_client:
                    try:
                        text = self._transcribe_groq(audio)
                        if text:
                            return text
                    except Exception as e:
                        print(f"⚠️ [Groq STT Failed: {e}. Falling back to local Whisper...]")

                # 2. Fallback: Local faster-whisper
                return self._transcribe_local(audio)

            except sr.WaitTimeoutError:
                return ""
            except Exception as e:
                print(f"[STT Error]: {e}")
                return ""

# Global STT Singleton
stt_engine = SpeechToTextEngine()
