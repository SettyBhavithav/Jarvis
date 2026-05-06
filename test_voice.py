import edge_tts
import asyncio
import pygame
import io
import os

async def test():
    print("Testing Edge TTS...")
    text = "Hello sir, this is a test of the new neural voice system. Can you hear me?"
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    print(f"Audio generated: {len(audio_data)} bytes")
    pygame.mixer.init()
    sound_file = io.BytesIO(audio_data)
    pygame.mixer.music.load(sound_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    print("Test complete.")

if __name__ == "__main__":
    asyncio.run(test())
