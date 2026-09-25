"""
JARVIS V2 - Voice Interruption & Acoustic Barge-In Controller
Handles immediate voice cutoff, queue drainage, and calibrated acoustic reverb decay.
"""
import time
from core.config import config
from core.state import runtime_state, AudioState
from voice.tts import tts_engine

class VoiceInterruptionController:
    def handle_barge_in(self):
        """Halts active speech immediately, drains the queue, and prevents acoustic echo loops."""
        print("\n🛑 [Interruption: Halting Voice Output & Draining Queue...]")
        tts_engine.stop()
        runtime_state.request_interrupt()

        # Acoustic Echo Prevention: wait for room reverberation to settle before re-opening mic
        time.sleep(config.REVERB_DECAY_DELAY)
        runtime_state.clear_interrupt()
        runtime_state.audio_state = AudioState.IDLE
        print("🟢 [Acoustic Reverb Settled - Mic Armed]")

interruption_controller = VoiceInterruptionController()
