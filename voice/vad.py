"""
JARVIS V2 - Audio Normalization & VAD Utilities
"""
import numpy as np

class AudioPreprocessor:
    @staticmethod
    def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
        """
        Boosts low-volume microphone audio to maximum amplitude without distortion,
        ensuring Whisper VAD does not drop quiet speech.
        """
        max_amp = np.max(np.abs(audio_data))
        if max_amp > 0:
            return audio_data / max_amp
        return audio_data

audio_preprocessor = AudioPreprocessor()
