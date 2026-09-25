"""
JARVIS V2 - State Management System
Thread-safe runtime state tracking for voice, agents, confirmation, and sessions.
"""
from enum import Enum
import threading
from typing import Optional, Dict, Any

class AudioState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

class RuntimeState:
    def __init__(self):
        self._lock = threading.RLock()
        self._audio_state: AudioState = AudioState.IDLE
        self._is_mic_busy: bool = False
        self._interrupt_requested: bool = False
        self._active_session_id: Optional[str] = None
        self._active_tool_name: Optional[str] = None
        self._pending_confirmation: Optional[Dict[str, Any]] = None

    @property
    def audio_state(self) -> AudioState:
        with self._lock:
            return self._audio_state

    @audio_state.setter
    def audio_state(self, state: AudioState):
        with self._lock:
            self._audio_state = state

    @property
    def is_mic_busy(self) -> bool:
        with self._lock:
            return self._is_mic_busy

    @is_mic_busy.setter
    def is_mic_busy(self, val: bool):
        with self._lock:
            self._is_mic_busy = val

    @property
    def interrupt_requested(self) -> bool:
        with self._lock:
            return self._interrupt_requested

    def request_interrupt(self):
        with self._lock:
            self._interrupt_requested = True
            self._audio_state = AudioState.INTERRUPTED

    def clear_interrupt(self):
        with self._lock:
            self._interrupt_requested = False

    @property
    def pending_confirmation(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._pending_confirmation

    def set_pending_confirmation(self, confirmation: Dict[str, Any]):
        with self._lock:
            self._pending_confirmation = confirmation

    def clear_pending_confirmation(self):
        with self._lock:
            self._pending_confirmation = None

# Global Runtime State Singleton
runtime_state = RuntimeState()
