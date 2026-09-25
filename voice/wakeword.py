"""
JARVIS V2 - Wake Word Detection Engine (openwakeword)
Dedicated background thread monitoring for 'hey_jarvis' at 0.15 threshold.
"""
import time
import threading
import numpy as np
from core.config import config
from core.state import runtime_state

class WakeWordDetector:
    def __init__(self):
        self.threshold = config.WAKE_WORD_THRESHOLD
        self.wake_event = threading.Event()
        self._thread = None
        self._is_running = False

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        def _worker():
            try:
                from openwakeword.model import Model
                import pyaudio
            except ImportError:
                print("[WakeWord Warning: openwakeword or pyaudio not installed.]")
                return

            oww_model = Model(wakeword_models=[config.WAKE_WORD_MODEL])
            audio = pyaudio.PyAudio()
            stream = None
            self._is_running = True

            while self._is_running:
                if runtime_state.is_mic_busy:
                    if stream is not None:
                        stream.stop_stream()
                        stream.close()
                        stream = None
                    time.sleep(0.3)
                    continue

                if stream is None:
                    try:
                        stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
                    except Exception:
                        time.sleep(1.0)
                        continue

                try:
                    raw_data = stream.read(1024, exception_on_overflow=False)
                    audio_data = np.frombuffer(raw_data, dtype=np.int16)
                    prediction = oww_model.predict(audio_data)
                    max_score = max(prediction.values()) if prediction else 0

                    if max_score > self.threshold:
                        print(f"\n🟢 [Wake Word Triggered! Score: {max_score:.2f}]")
                        runtime_state.is_mic_busy = True
                        if stream is not None:
                            stream.stop_stream()
                            stream.close()
                            stream = None
                        self.wake_event.set()
                        time.sleep(0.5)

                        while runtime_state.is_mic_busy:
                            time.sleep(0.3)

                except Exception:
                    time.sleep(0.2)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

# Global Wake Word Singleton
wake_word_detector = WakeWordDetector()
