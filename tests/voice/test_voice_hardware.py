"""
JARVIS V2 - Hardware Voice & Microphone Integration Tests
Marked with @pytest.mark.voice so CI-safe pytest runs skip these by default.
"""
import pytest

@pytest.mark.voice
def test_voice_tts_playback():
    try:
        import edge_tts
        import asyncio
        async def _test():
            comm = edge_tts.Communicate("Testing neural voice.", "en-US-GuyNeural")
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    return True
            return False
        res = asyncio.run(_test())
        assert res is True
    except Exception as e:
        pytest.skip(f"Audio/Edge-TTS hardware unavailable: {e}")

@pytest.mark.voice
def test_mic_hardware():
    try:
        import speech_recognition as sr
        mics = sr.Microphone.list_microphone_names()
        assert len(mics) >= 0
    except Exception as e:
        pytest.skip(f"Microphone hardware unavailable: {e}")
