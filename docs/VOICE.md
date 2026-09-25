# JARVIS V2 — Voice Subsystem & Interruption Architecture

## 1. Voice Pipeline Overview

JARVIS V2 features a sub-second, full-duplex voice pipeline with true acoustic barge-in interruption.

```
       Microphone (16kHz PCM)
                 │
                 ▼
        ┌──────────────────┐
        │ openWakeWord VAD │ ("Hey Jarvis" @ 0.15 threshold)
        └────────┬─────────┘
                 │ (Wake word detected)
                 ▼
        ┌──────────────────┐
        │  faster-whisper  │ (small.en on CPU/CUDA + Silero VAD)
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Orchestrator /   │ (ReAct streaming generation)
        │ Model Gateway    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  Edge-TTS Stream │ (Chunked byte streaming)
        └────────┬─────────┘
                 │
                 ▼
         Pygame Audio Out
```

---

## 2. Low-Latency Wake-Word Detection (`voice/wakeword.py`)
- **Engine:** `openwakeword` with custom `hey_jarvis` model.
- **Sensitivity Threshold:** `0.15` default (configured in `config.WAKE_WORD_THRESHOLD`), providing rapid activation while rejecting ambient speech.
- **VAD Pre-Filtering:** Only feeds frames with active voice energy to the neural detector.

---

## 3. Speech-to-Text Pipeline (`voice/stt.py`)
- **Engine:** `faster-whisper` (`small.en` or `tiny.en` on CPU/CUDA with `compute_type="float32"`).
- **VAD Energy Gate:** Dynamic energy threshold calculation (`energy_threshold = 300`) with silence timeouts to prevent cutting off the user mid-sentence.
- **Audio Normalization:** Enforces 16kHz mono PCM normalization before feeding the acoustic model.

---

## 4. True Voice Barge-In / Interruption Engine (`voice/interruption.py`)
Real conversational AI requires the user to interrupt JARVIS at any instant while the assistant is speaking:
1. **TTS Output Tagging:** When Edge-TTS plays audio via Pygame, `RuntimeState.is_speaking` is set to `True`.
2. **Microphone Subtraction & Reverb Window:** An intentional 0.8-second blanking guard prevents echo cancellation feedback from self-triggering an interruption.
3. **Interrupt Event:** If user speech energy exceeds the threshold while JARVIS is speaking:
   - Pygame audio playback is immediately stopped (`pygame.mixer.music.stop()`).
   - The streaming TTS sentence queue is instantly purged.
   - The event bus emits `AudioInterruptedEvent`.
   - The system transitions directly into `LISTENING` state to capture the user's interruption prompt.
