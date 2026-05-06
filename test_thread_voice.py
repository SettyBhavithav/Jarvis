import threading
import pygame
import io
import time
import edge_tts
import asyncio

def tts_worker():
    async def _async_worker():
        pygame.mixer.init()
        communicate = edge_tts.Communicate("Testing threaded voice.", "en-US-GuyNeural")
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        sound_file = io.BytesIO(audio_data)
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        print("Done playing in thread.")

    asyncio.run(_async_worker())

if __name__ == "__main__":
    t = threading.Thread(target=tts_worker, daemon=True)
    t.start()
    time.sleep(5)
