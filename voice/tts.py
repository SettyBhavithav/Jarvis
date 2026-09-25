"""
JARVIS V2 - Streaming Text-to-Speech Engine (Edge-TTS)
Persistent worker thread streaming high-fidelity audio chunks via Pygame mixer with immediate purge support.
"""
import os
import io
import queue
import asyncio
import threading
import edge_tts
from core.config import config
from core.state import runtime_state, AudioState

class TextToSpeechEngine:
    def __init__(self):
        self.tts_queue = queue.Queue()
        self.is_playing = False
        self.is_generating = False
        self._thread = None

    def start_worker(self):
        if self._thread is not None and self._thread.is_alive():
            return

        def _worker():
            async def _async_loop():
                os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
                import pygame
                pygame.mixer.init()

                while True:
                    text = await asyncio.get_event_loop().run_in_executor(None, self.tts_queue.get)

                    if text == "STOP":
                        pygame.mixer.music.stop()
                        runtime_state.audio_state = AudioState.IDLE
                        continue

                    if text:
                        self.is_generating = True
                        runtime_state.audio_state = AudioState.SPEAKING
                        try:
                            communicate = edge_tts.Communicate(text, config.TTS_VOICE)
                            audio_data = b""
                            async for chunk in communicate.stream():
                                if chunk["type"] == "audio":
                                    audio_data += chunk["data"]

                            if audio_data:
                                sound_file = io.BytesIO(audio_data)
                                self.is_playing = True
                                pygame.mixer.music.load(sound_file)
                                pygame.mixer.music.play()

                                while pygame.mixer.music.get_busy():
                                    if not self.tts_queue.empty() and self.tts_queue.queue[0] == "STOP":
                                        pygame.mixer.music.stop()
                                        self.tts_queue.get()
                                        break
                                    await asyncio.sleep(0.04)

                        except Exception as e:
                            print(f"[TTS Error]: {e}")
                        finally:
                            self.is_playing = False
                            self.is_generating = False
                            if self.tts_queue.empty():
                                runtime_state.audio_state = AudioState.IDLE

            asyncio.run(_async_loop())

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def speak_chunk(self, sentence: str):
        if not sentence:
            return
        # Sanitize markdown formatting and emojis that crash edge-tts
        clean = sentence.replace("*", "").replace("#", "").replace("_", "").strip()
        if any(c.isalnum() for c in clean):
            self.tts_queue.put(clean)

    def stop(self):
        """Purges pending audio chunks and commands hardware stop."""
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except Exception:
                pass
        self.tts_queue.put("STOP")
        self.is_playing = False
        self.is_generating = False
        runtime_state.audio_state = AudioState.IDLE

    def is_speaking(self) -> bool:
        return self.is_playing or self.is_generating or not self.tts_queue.empty()

# Global TTS Singleton
tts_engine = TextToSpeechEngine()
