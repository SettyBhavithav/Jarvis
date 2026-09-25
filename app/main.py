"""
JARVIS V2 - Main Orchestration Loop
The central execution runtime tying voice, streaming TTS, barge-in, and agentic orchestration.
"""
import time
import sys
from typing import List
from core.state import runtime_state, AudioState
from core.schemas import ChatMessage, MessageRole
from app.bootstrap import bootstrapper
from voice.stt import stt_engine
from voice.tts import tts_engine
from voice.wakeword import wake_word_detector
from voice.interruption import interruption_controller
from core.orchestrator import orchestrator

def run_jarvis():
    # Bootstrap all engines
    bootstrapper.initialize_system()

    history: List[ChatMessage] = []

    print("\n🟢 JARVIS is online. Say 'Hey Jarvis' to activate. Press Ctrl+C to shut down.\n")

    while True:
        try:
            runtime_state.audio_state = AudioState.IDLE
            wake_word_detector.wake_event.clear()

            print("\n🔵 [Standby] Waiting for 'Hey Jarvis'...")

            # Wait for wake word
            while not wake_word_detector.wake_event.is_set():
                time.sleep(0.1)

            # Wake word caught! Lock mic for speech acquisition
            runtime_state.is_mic_busy = True
            time.sleep(0.2)

            # Listen & Transcribe
            runtime_state.audio_state = AudioState.LISTENING
            user_input = stt_engine.listen_and_transcribe(timeout=5, phrase_time_limit=10)

            if not user_input or len(user_input.strip()) == 0:
                runtime_state.is_mic_busy = False
                continue

            print(f"\nYou (Voice): {user_input}")
            history.append(ChatMessage(role=MessageRole.USER, content=user_input))

            # Execute turn via Orchestrator
            runtime_state.audio_state = AudioState.THINKING
            print("Jarvis: ", end="", flush=True)

            token_generator = orchestrator.execute_turn(user_input, history=history, channel="voice")

            current_sentence = ""
            full_reply = ""

            for token in token_generator:
                print(token, end="", flush=True)
                full_reply += token
                current_sentence += token

                # Chunk sentences for streaming TTS
                if any(punct in token for punct in ['.', '!', '?', '\n']):
                    tts_engine.speak_chunk(current_sentence)
                    current_sentence = ""

            if current_sentence.strip():
                tts_engine.speak_chunk(current_sentence)
            print()

            history.append(ChatMessage(role=MessageRole.ASSISTANT, content=full_reply))

            # --- TRUE VOICE BARGE-IN INTERRUPTION ---
            # Unlock mic so user can interrupt mid-speech
            runtime_state.is_mic_busy = False
            wake_word_detector.wake_event.clear()

            while tts_engine.is_speaking():
                if wake_word_detector.wake_event.is_set():
                    interruption_controller.handle_barge_in()
                    wake_word_detector.wake_event.clear()
                    break
                time.sleep(0.08)

            wake_word_detector.wake_event.clear()

        except KeyboardInterrupt:
            print("\nShutting down JARVIS systems. Goodbye, sir.")
            tts_engine.stop()
            break
        except Exception as e:
            print(f"\n[JARVIS System Exception]: {e}")
            runtime_state.is_mic_busy = False
            time.sleep(1.0)

if __name__ == "__main__":
    run_jarvis()
