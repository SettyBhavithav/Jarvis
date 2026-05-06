import speech_recognition as sr
import numpy as np

def find_working_mic():
    print("Scanning all microphone indices for input...")
    mics = sr.Microphone.list_microphone_names()
    
    best_index = -1
    max_vol = 0
    
    for i in range(len(mics)):
        print(f"Testing Index [{i}]: {mics[i]}...")
        try:
            with sr.Microphone(device_index=i) as source:
                r = sr.Recognizer()
                # Record 1 second
                audio = r.record(source, duration=1)
                data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                vol = np.max(np.abs(data))
                print(f"  -> Volume: {vol}")
                if vol > max_vol:
                    max_vol = vol
                    best_index = i
        except Exception as e:
            print(f"  -> Failed: {e}")
            
    print("-" * 30)
    if best_index != -1:
        print(f"RECOMMENDATION: Use Device Index [{best_index}] with Volume {max_vol}")
    else:
        print("No working microphone found.")

if __name__ == "__main__":
    find_working_mic()
