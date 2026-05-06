import speech_recognition as sr
import numpy as np

def test_microphone():
    print("Available Microphones:")
    mics = sr.Microphone.list_microphone_names()
    for i, mic in enumerate(mics):
        print(f"[{i}] {mic}")
        
    print("\nAttempting to record from default microphone for 3 seconds...")
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("\nSPEAK LOUDLY NOW...")
        # Record exactly 3 seconds
        audio = recognizer.record(source, duration=3)
        
    # Check if we captured silence
    audio_data = np.frombuffer(audio.get_raw_data(), np.int16)
    max_volume = np.max(np.abs(audio_data))
    
    print("\n--- RESULTS ---")
    print(f"Max Volume captured: {max_volume}")
    
    if max_volume == 0:
        print("❌ CRITICAL ERROR: Python captured PURE SILENCE (Volume = 0).")
        print("This means either:")
        print("1. Windows 11 Privacy Settings are blocking your Terminal/VS Code from using the mic.")
        print("   (Go to Windows Settings -> Privacy & Security -> Microphone -> 'Let desktop apps access your microphone')")
        print("2. The default microphone is set to 'Stereo Mix' or a disconnected device.")
    elif max_volume < 500:
        print("⚠️ WARNING: Audio was captured, but it is EXTREMELY quiet.")
        print("You might need to increase your microphone volume in Windows settings.")
    else:
        print("✅ SUCCESS: Microphone is working and capturing your voice beautifully!")

if __name__ == "__main__":
    test_microphone()
