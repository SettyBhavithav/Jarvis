import edge_tts
import pygame
import ollama
import os
import subprocess
import webbrowser
import pyautogui
import time
import speech_recognition as sr
from faster_whisper import WhisperModel
import warnings
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
import threading
import asyncio
import queue
import io
import requests
import sys
import re
import base64
from PIL import ImageGrab
import keyboard
import json

# Load environment variables from .env file
load_dotenv()

# --- API Keys & Clients ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NIM_API_KEY = os.getenv("NIM_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
NIM_QWEN_API_KEY = os.getenv("NIM_QWEN_API_KEY")
NIM_GEMMA_API_KEY = os.getenv("NIM_GEMMA_API_KEY")
NIM_VISION_API_KEY = os.getenv("NIM_VISION_API_KEY")

# Initialize OpenAI-compatible clients if keys exist
groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY and "your_" not in GROQ_API_KEY else None
nim_client = OpenAI(api_key=NIM_API_KEY, base_url="https://integrate.api.nvidia.com/v1") if NIM_API_KEY and "your_" not in NIM_API_KEY else None
nim_qwen_client = OpenAI(api_key=NIM_QWEN_API_KEY or NIM_API_KEY, base_url="https://integrate.api.nvidia.com/v1") if (NIM_QWEN_API_KEY or NIM_API_KEY) and "your_" not in (NIM_QWEN_API_KEY or NIM_API_KEY) else None
nim_gemma_client = OpenAI(api_key=NIM_GEMMA_API_KEY or NIM_API_KEY, base_url="https://integrate.api.nvidia.com/v1") if (NIM_GEMMA_API_KEY or NIM_API_KEY) and "your_" not in (NIM_GEMMA_API_KEY or NIM_API_KEY) else None
nim_vision_client = OpenAI(api_key=NIM_VISION_API_KEY or NIM_API_KEY, base_url="https://integrate.api.nvidia.com/v1") if (NIM_VISION_API_KEY or NIM_API_KEY) and "your_" not in (NIM_VISION_API_KEY or NIM_API_KEY) else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY and "your_" not in GEMINI_API_KEY else None
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://integrate.api.nvidia.com/v1") if DEEPSEEK_API_KEY and "your_" not in DEEPSEEK_API_KEY else None

# Suppress warnings from Whisper
warnings.filterwarnings("ignore", category=UserWarning)

# --- GLOBAL STATES ---
FILE_TRANSFER_STATE = {
    "active": False,
    "files": [],
    "contact": None
}

# Pre-load STT Recognizer
try:
    stt_recognizer = sr.Recognizer()
    stt_recognizer.energy_threshold = 500 # Adjusted for their 2750 max volume
    stt_recognizer.dynamic_energy_threshold = True
    whisper_model = None # We will lazy-load this later!
except Exception as e:
    print(f"[Warning] Failed to initialize audio: {e}")
    whisper_model = None

is_mic_busy = False
active_tts_process = None
wake_word_event = threading.Event()

# --- TTS Engine (Step 9) ---
tts_queue = queue.Queue()

def tts_worker():
    """Persistent thread for high-quality Edge TTS."""
    async def _async_worker():
        # Initialize mixer inside the thread for Windows COM compatibility
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
        import pygame
        pygame.mixer.init()
        global is_tts_playing, is_tts_generating
        
        while True:
            # We use a thread-safe queue. get() blocks until an item is available.
            # But we need to run it in a way that doesn't block the async loop.
            text = await asyncio.get_event_loop().run_in_executor(None, tts_queue.get)
            
            if text == "STOP":
                pygame.mixer.music.stop()
                continue
                
            if text:
                print(f"\n🎙️ [Jarvis Voice: Processing '{text[:50]}...']")
                is_tts_generating = True # Lock mic during generation
                try:
                    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
                    audio_data = b""
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_data += chunk["data"]
                    
                    if audio_data:
                        sound_file = io.BytesIO(audio_data)
                        
                        try:
                            is_tts_playing = True
                            pygame.mixer.music.load(sound_file)
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                # Check for immediate STOP during playback
                                if not tts_queue.empty():
                                    if tts_queue.queue[0] == "STOP":
                                        pygame.mixer.music.stop()
                                        tts_queue.get() # Consume the STOP
                                        break
                                await asyncio.sleep(0.05)
                        finally:
                            is_tts_playing = False
                except Exception as e:
                    print(f"🎙️ [TTS Error]: {e}")
                finally:
                    is_tts_generating = False
    
    asyncio.run(_async_worker())

# Start TTS Thread immediately
threading.Thread(target=tts_worker, daemon=True).start()

def stop_speaking():
    """Signals the persistent TTS thread to stop current audio and clears the backlog."""
    # Empty all pending sentences from the queue
    while not tts_queue.empty():
        try:
            tts_queue.get_nowait()
        except:
            pass
    # Push STOP to halt the currently playing audio chunk
    tts_queue.put("STOP")

# Register keys to instantly stop speech
try:
    # suppress=False allows you to still type spaces in the terminal!
    keyboard.add_hotkey('space', stop_speaking, suppress=False)
    keyboard.add_hotkey('esc', stop_speaking)
except Exception as e:
    print(f"[Warning] Could not register hotkeys: {e}")

def speak_streaming(sentence):
    """Adds a sentence to the TTS queue."""
    if not sentence: return
    clean_text = sentence.replace("*", "").replace("#", "").replace("_", "").strip()
    # Check if there are any actual letters/numbers to speak to prevent edge-tts from crashing
    if any(c.isalnum() for c in clean_text):
        tts_queue.put(clean_text)

is_tts_playing = False
is_tts_generating = False

def is_speaking():
    """Checks if the TTS engine is currently generating or talking."""
    return is_tts_playing or is_tts_generating or not tts_queue.empty()

def speak(text):
    """Speaks full text immediately."""
    stop_speaking()
    speak_streaming(text)

# --- Configuration ---
MIC_DEVICE_INDEX = None # Set to None to use system default
MAIN_BRAIN_MODEL = "meta/llama-4-maverick-17b-128e-instruct"
REASONING_MODEL = "deepseek-ai/deepseek-v3.2"
CODING_MODEL = "qwen/qwen3-coder-480b-a35b-instruct"
FAST_CHAT_MODEL = "google/gemma-3n-e4b-it"
VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"
AUDIO_VISION_MODEL = "microsoft/phi-4-multimodal-instruct"
VOICE_INPUT_MODEL = "small.en" # Fast local STT
SAFETY_MODEL = "meta/llama-guard-4-12b"

def vision_look_at_screen(question):
    """Takes a screenshot and asks Gemini or NIM to analyze it."""
    print("\n👁️ [Vision: Capturing Screen...]")
    try:
        # Capture screen to memory
        screenshot = ImageGrab.grab()
        screenshot = screenshot.resize((1280, 720)) # Resize for faster upload
        
        # Save temporarily
        tmp_path = os.path.join(os.path.dirname(__file__), "_vision_tmp.jpg")
        screenshot.save(tmp_path, "JPEG", quality=75)
        
        with open(tmp_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(tmp_path)
        
        # Try Gemini first (best vision quality, if still using old gemini string)
        if gemini_client and GEMINI_API_KEY:
            print("👁️ [Vision: Analyzing with Gemini...]")
            from google.genai import types
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=base64.b64decode(img_b64), mime_type="image/jpeg"),
                    question
                ]
            )
            return response.text
        
        # Fallback: NIM vision model
        if nim_vision_client:
            print(f"👁️ [Vision: Analyzing with NIM ({VISION_MODEL})...]")
            response = nim_vision_client.chat.completions.create(
                model=VISION_MODEL,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": question}
                ]}],
                max_tokens=1024
            )
            return response.choices[0].message.content
        
        return "No vision API available. Please add a Gemini or NIM API key, sir."
    except Exception as e:
        return f"Vision failed: {e}"

def phi_audio_vision_analysis(prompt):
    """Captures a screenshot and 5 seconds of ambient mic audio, then sends both to Phi-4 Multimodal."""
    print("\n📸🎤 [Multimodal: Capturing Screen and Audio...]")
    try:
        # Capture screen
        screenshot = ImageGrab.grab()
        screenshot = screenshot.resize((1280, 720))
        tmp_img = os.path.join(os.path.dirname(__file__), "_phi_tmp.jpg")
        screenshot.save(tmp_img, "JPEG", quality=75)
        with open(tmp_img, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(tmp_img)
        
        # Capture audio (5 seconds)
        print("🎤 [Recording 5 seconds of ambient audio for Phi-4...]")
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.2)
            audio = r.record(source, duration=5)
            
        audio_data = audio.get_wav_data()
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        
        if not nim_client:
            return "No NIM client configured for Phi-4 Multimodal, sir."
            
        print(f"🧠 [Multimodal: Analyzing with {AUDIO_VISION_MODEL}...]")
        response = nim_client.chat.completions.create(
            model=AUDIO_VISION_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
            ]}],
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Audio+Vision analysis failed: {e}"

def load_soul():
    """Loads the Jarvis personality from SOUL.md and appends dynamic context."""
    soul_content = "You are a helpful AI assistant."
    soul_path = os.path.join(os.path.dirname(__file__), "SOUL.md")
    if os.path.exists(soul_path):
        with open(soul_path, "r", encoding="utf-8") as f:
            soul_content = f.read()
            
    # Inject Dynamic Context (Time, Date, Location)
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")
    
    location_str = "Unknown"
    try:
        # Fast, free IP-based geolocation
        res = requests.get('https://ipapi.co/json/', timeout=2).json()
        city = res.get("city", "Unknown City")
        region = res.get("region", "")
        country = res.get("country_name", "Unknown Country")
        location_str = f"{city}, {region}, {country}"
    except Exception as e:
        location_str = "Hyderabad, Telangana, India (Default)"

    dynamic_context = f"\n\n--- CURRENT SYSTEM CONTEXT ---\nCurrent Time: {time_str}\nCurrent Date: {date_str}\nUser Location: {location_str}\n"
    
    return soul_content + dynamic_context

# --- Memory Management ---
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
MAX_MEMORY_MESSAGES = 20 # Keep last 20 messages to prevent token overflow

def load_memory():
    """Loads previous conversation history from file."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory = json.load(f)
                # Filter out old system prompts so we can inject fresh ones
                return [m for m in memory if m.get("role") != "system"]
        except Exception as e:
            print(f"[Warning] Could not load memory: {e}")
    return []

def save_memory(messages):
    """Saves conversation history to file."""
    try:
        # Keep only the most recent messages (excluding the system prompt)
        memory_to_save = [m for m in messages if m.get("role") != "system"][-MAX_MEMORY_MESSAGES:]
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_to_save, f, indent=2)
    except Exception as e:
        print(f"[Warning] Could not save memory: {e}")
def get_system_stats():
    """Fetches real-time hardware performance data."""
    import psutil
    
    cpu_usage = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    
    battery = psutil.sensors_battery()
    battery_info = "Desktop PC (No Battery)"
    if battery:
        percent = battery.percent
        plugged = "Plugged In" if battery.power_plugged else "Discharged"
        battery_info = f"{percent}% ({plugged})"
        
    disk = psutil.disk_usage('/')
    disk_free = disk.free / (1024**3) # GB
    
    return f"Sir, your system status is as follows:\n- CPU Usage: {cpu_usage}%\n- RAM Usage: {ram_usage}%\n- Battery: {battery_info}\n- Storage: {disk_free:.1f} GB free."

# --- Google Calendar & Gmail Integration ---
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail.send']

def authenticate_google():
    """Handles Google OAuth authentication."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import pickle
    
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def get_calendar_events(max_results=5):
    """Fetches upcoming events from Google Calendar."""
    from googleapiclient.discovery import build
    try:
        creds = authenticate_google()
        if not creds:
            return "Sir, I need a 'credentials.json' file in my directory to access your calendar. Please download it from Google Cloud Console and place it here."
            
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                            maxResults=max_results, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        if not events:
            return "You have no upcoming events, sir."
        
        reply = "Sir, here are your upcoming events:\n"
        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            # Format time if it's a dateTime
            if "T" in start_str:
                dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                start_str = dt.strftime("%b %d at %I:%M %p")
                
            reply += f"- {event['summary']} ({start_str})\n"
        return reply
    except Exception as e:
        return f"I failed to fetch your calendar, sir. Error: {e}"

def send_email_background(to_email, subject, body):
    """Silently sends an email using the Gmail API."""
    from googleapiclient.discovery import build
    from email.message import EmailMessage
    import base64
    try:
        creds = authenticate_google()
        if not creds: return "Sir, I need a 'credentials.json' file to access your Gmail."
            
        service = build('gmail', 'v1', credentials=creds)
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['From'] = 'me'
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        service.users().messages().send(userId="me", body=create_message).execute()
        return f"Email successfully sent to {to_email}, sir."
    except Exception as e:
        return f"I failed to send the email, sir. Error: {e}"

def determine_route(prompt):
    """Simple heuristic router to decide which brain to use."""
    prompt_lower = prompt.lower()
    
    # Vision commands
    vision_keywords = ["what's on my screen", "what is on my screen", "look at my screen", "what do you see", "read the screen", "describe the screen", "what's open", "what is this error", "look at this", "what am i looking at", "can you see this"]
    if any(w in prompt_lower for w in vision_keywords):
        return "vision"
        
    # Multimodal (Audio+Vision) commands
    if any(w in prompt_lower for w in ["listen to this", "what song is this", "what do you hear", "listen and look", "what's playing", "analyze what you hear"]):
        return "audio_vision"
        
    # Personal Data reading
    if any(w in prompt_lower for w in ["read my notes", "check my file", "what is in my document", "read my file", "search my notes"]):
        return "personal_data"
    
    if not GROQ_API_KEY and not NIM_API_KEY:
        return "local"
    if any(word in prompt_lower for word in ["code", "script", "python", "html", "debug"]):
        return "nim_code" if nim_client else "local"
    if any(word in prompt_lower for word in ["research", "think", "explain why", "complex"]):
        return "nim_reason" if nim_client else "local"
    if any(word in prompt_lower for word in ["deepseek", "deep seek"]):
        return "deepseek" if deepseek_client else "local"
    return "groq_chat" if groq_client else "local"

def check_safety(prompt):
    """Passes the user input through Llama-Guard-4 to ensure it's safe."""
    if not nim_client:
        return True
    try:
        print("🛡️ [Safety Guard: Analyzing...]")
        response = nim_client.chat.completions.create(
            model=SAFETY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10
        )
        result = response.choices[0].message.content.strip().lower()
        if "unsafe" in result:
            return False
        return True
    except Exception as e:
        print(f"[Safety Guard Error]: {e}")
        return True

def chat_local(messages, mute=False):
    """Calls local Ollama model (Main Brain fallback)."""
    if not mute: print(f"🧠 [Brain: Local (Fallback)]")
    response = ollama.chat(model="llama3.1:8b", messages=messages, stream=True)
    full_reply = ""
    current_sentence = ""
    stop_speaking()
    for chunk in response:
        word = chunk['message']['content']
        print(word, end="", flush=True)
        full_reply += word
        current_sentence += word
        
        # Stream audio when sentence ends
        if any(punct in word for punct in ['.', '!', '?']):
            if not mute: speak_streaming(current_sentence)
            current_sentence = ""
            
    if current_sentence.strip():
        if not mute: speak_streaming(current_sentence)
    if not mute: print()
    return full_reply

def chat_cloud_openai_compatible(client, model, messages, extra_kwargs=None, mute=False):
    """Calls Groq or NIM APIs using OpenAI client format."""
    if not mute: print(f"☁️ [Brain: Cloud {model}]")
    
    # --- RAG MEMORY INJECTION ---
    try:
        from memory_manager import memory_db
        if memory_db.client and len(messages) > 0 and messages[-1]["role"] == "user":
            user_prompt = messages[-1]["content"]
            user_prompt_lower = user_prompt.lower()
            
            # 1. Store Memory Command
            import re
            save_match = re.search(r"(?:remember|remeber|memorize|save) (?:that )?(.*)", user_prompt, re.IGNORECASE)
            
            if save_match:
                fact = save_match.group(1).strip()
                memory_db.add_memory(fact)
                print(f"💾 [Memory Saved]: {fact}")
                messages.insert(-1, {"role": "system", "content": f"SYSTEM NOTE: You just successfully saved '{fact}' to your long-term database. Please politely acknowledge this to the user."})
            
            # 2. Retrieve Memory Context
            else:
                memories = memory_db.search_memory(user_prompt, top_k=3, threshold=0.3)
                if memories:
                    context = "IMPORTANT RETRIEVED MEMORY: Use these facts from your long term database if they are relevant to answering the user:\n"
                    for m in memories:
                        context += f"- {m['text']}\n"
                    messages.insert(-1, {"role": "system", "content": context})
                    
            # 3. YouTube Summarizer Injection
            yt_match = re.search(r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w\-_]+)", user_prompt)
            if yt_match:
                video_id = yt_match.group(1)
                try:
                    from youtube_transcript_api import YouTubeTranscriptApi
                    print(f"🎬 [YouTube: Downloading Transcript for {video_id}...]")
                    transcript_list = YouTubeTranscriptApi().list(video_id)
                    try:
                        transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB']).fetch()
                    except:
                        transcript = next(iter(transcript_list)).fetch()
                    full_text = " ".join([t.text for t in transcript])
                    # Cap transcript at 20000 chars to avoid token limits
                    if len(full_text) > 20000: full_text = full_text[:20000] + "..."
                    context = f"SYSTEM NOTE: The user has provided a YouTube video link. Here is the exact transcript of the video:\n\n{full_text}\n\nUse this transcript to answer their question or summarize the video. If they ask for a summary, give a highly detailed, formatted response with 3-5 bullet points."
                    messages.insert(-1, {"role": "system", "content": context})
                    print("🟢 [YouTube: Transcript Injected into Brain]")
                except Exception as e:
                    print(f"🔴 [YouTube Error]: {e}")
    except Exception as e:
        print(f"[RAG Error]: {e}")
        
    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        if extra_kwargs:
            kwargs.update(extra_kwargs)
            
        response = client.chat.completions.create(**kwargs)
        
        full_reply = ""
        current_sentence = ""
        is_thinking = False
        stop_speaking()
        
        for chunk in response:
            if not getattr(chunk, "choices", None):
                continue
            
            # Handle DeepSeek reasoning tokens
            reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
            if reasoning:
                if not is_thinking:
                    print("\n[Thinking...] ", end="", flush=True)
                    is_thinking = True
                print(reasoning, end="", flush=True)
            
            # Handle normal content tokens
            if chunk.choices and chunk.choices[0].delta.content is not None:
                if is_thinking:
                    print("\n\nJarvis: ", end="", flush=True)
                    is_thinking = False
                
                word = chunk.choices[0].delta.content
                print(word, end="", flush=True)
                full_reply += word
                current_sentence += word
                
                if any(punct in word for punct in ['.', '!', '?', '\n']):
                    if not mute: speak_streaming(current_sentence)
                    current_sentence = ""
                    
        if current_sentence.strip():
            if not mute: speak_streaming(current_sentence)
            
        if not mute: print()
        return full_reply
    except Exception as e:
        print(f"\n[Cloud API Error: {e}] -> Falling back to Local Brain...")
        return chat_local(messages, mute=mute)

def execute_computer_action(prompt, is_discord=False):
    """Intercepts and executes simple computer commands to ensure <1s latency."""
    prompt_lower = prompt.lower().strip()
    
    # Normalize newlines
    prompt_lower = prompt_lower.replace('\n', ' ')
    
    # Remove polite words
    for word in ["can you ", "please ", "jarvis ", "hey jarvis ", "would you ", "is "]:
        prompt_lower = prompt_lower.replace(word, "")
        
    global FILE_TRANSFER_STATE
    
    # 0.4 System Health Monitor
    if any(word in prompt_lower for word in ["system status", "battery level", "cpu usage", "pc health", "pc status", "performance", "how is my computer", "system info"]):
        print("\n⚡ [Action: Fetching System Diagnostics]")
        return get_system_stats()
        
    # 0.4.0 Media Orchestration (Spotify/Windows)
    if any(word in prompt_lower for word in ["pause the music", "stop the music", "play the music", "resume music", "pause music"]):
        pyautogui.press('playpause')
        return "I have toggled the media playback, sir."
    if any(word in prompt_lower for word in ["next track", "skip this song", "next song", "skip track"]):
        pyautogui.press('nexttrack')
        return "Skipping to the next track, sir."
    if any(word in prompt_lower for word in ["previous track", "last song", "previous song"]):
        pyautogui.press('prevtrack')
        return "Playing the previous track, sir."
    if any(word in prompt_lower for word in ["mute the volume", "mute the system", "mute audio"]):
        pyautogui.press('volumemute')
        return "System muted, sir."
        
    # 0.4.1 Neural To-Do List
    import re
    if any(word in prompt_lower for word in ["show tasks", "to-do list", "what are my tasks", "my goals", "view tasks"]):
        from memory_manager import memory_db
        tasks = memory_db.get_tasks()
        if not tasks:
            return "Sir, your to-do list is currently empty."
        reply = "Sir, here are your current tasks:\n"
        for i, task in enumerate(tasks):
            reply += f"{i+1}. {task}\n"
        return reply

    if any(word in prompt_lower for word in ["clear tasks", "empty to-do list", "delete all tasks"]):
        from memory_manager import memory_db
        if memory_db.clear_tasks():
            return "I have cleared your to-do list, sir."
        return "I failed to clear the list, sir."

    task_match = re.search(r"(?:add task|remember to|todo) (.*)", prompt_lower)
    if task_match:
        task_text = task_match.group(1).strip()
        from memory_manager import memory_db
        if memory_db.add_task(task_text):
            return f"I have added '{task_text}' to your to-do list, sir."
        return "I failed to add the task, sir."
        
    # 0.4.2 Google Calendar
    if any(word in prompt_lower for word in ["calendar", "upcoming events", "my schedule", "what am i doing", "appointments"]):
        print("\n⚡ [Action: Fetching Calendar Events]")
        return get_calendar_events()

    # Check if we are waiting for a file selection from the user
    if FILE_TRANSFER_STATE.get("active"):
        if prompt_lower.isdigit() or prompt_lower.replace("send ", "").strip().isdigit():
            idx_str = prompt_lower.replace("send ", "").strip()
            if idx_str.isdigit():
                idx = int(idx_str) - 1
                if 0 <= idx < len(FILE_TRANSFER_STATE["files"]):
                    file_path = FILE_TRANSFER_STATE["files"][idx]
                    contact = FILE_TRANSFER_STATE["contact"]
                    
                    print(f"⚡ [Action: Sending {os.path.basename(file_path)} to {contact} via WhatsApp]")
                    
                    # Copy file to clipboard silently using PowerShell
                    os.system(f'powershell.exe -command "Set-Clipboard -Path \'{file_path}\'"')
                    
                    # Open WhatsApp Desktop App
                    pyautogui.press('win')
                    time.sleep(0.5)
                    pyautogui.write("whatsapp", interval=0.05)
                    time.sleep(0.5)
                    pyautogui.press('enter')
                    
                    print("⏳ [Waiting for WhatsApp to load...]")
                    time.sleep(5.0)
                    
                    # Search for contact
                    pyautogui.hotkey('ctrl', 'f')
                    time.sleep(1.0)
                    pyautogui.write(contact, interval=0.05)
                    time.sleep(2.0)
                    pyautogui.press('down')
                    time.sleep(0.2)
                    pyautogui.press('enter')
                    time.sleep(1.0)
                    
                    # Paste the file and send
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(2.0) # Wait for attachment preview
                    pyautogui.press('enter')
                    
                    FILE_TRANSFER_STATE["active"] = False
                    return f"I have sent {os.path.basename(file_path)} to {contact} on WhatsApp, sir."
                else:
                    return "Invalid file number, sir. Please select a valid number or say 'cancel'."
                    
        if prompt_lower == "cancel":
            FILE_TRANSFER_STATE["active"] = False
            return "File transfer cancelled, sir."
            
    # Initiate a new File Transfer
    import re
    match = re.search(r"file.*?(?:from|form|in|at)\s+(.*?)\s+.*?(?:send|forward).*?to\s+(.*)", prompt_lower)
    if match:
        path = match.group(1).strip()
        contact = match.group(2).strip().replace(" on whatsapp", "")
        
        # Resolve common paths
        if path.lower() == "downloads":
            path = os.path.expanduser("~\\Downloads")
        elif path.lower() == "documents":
            path = os.path.expanduser("~\\Documents")
        elif path.lower() == "desktop":
            path = os.path.expanduser("~\\Desktop")
            
        import glob
        if os.path.isdir(path):
            files = list(filter(os.path.isfile, glob.glob(os.path.join(path, '*'))))
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            top_files = files[:10]
            
            if not top_files:
                return f"I could not find any files in {path}, sir."
                
            FILE_TRANSFER_STATE["active"] = True
            FILE_TRANSFER_STATE["files"] = top_files
            FILE_TRANSFER_STATE["contact"] = contact
            
            reply = f"I found these recent files in {path}. Which one would you like to send to {contact}?\n\n"
            for i, f in enumerate(top_files):
                reply += f"{i+1}. {os.path.basename(f)}\n"
            return reply
        else:
            return f"I could not find the folder: {path}"
    # 0.5 Desktop Screen Vision
    vision_keywords = ["look", "what is on my screen", "read", "analyze", "see", "describe", "summarize", "fix this error", "what is this", "look at this", "what am i looking at"]
    if ("screen" in prompt_lower and any(w in prompt_lower for w in vision_keywords)) or any(w in prompt_lower for w in ["what is this error", "look at this", "what am i looking at", "can you see this"]):
        q = prompt_lower
        if " and " in prompt_lower:
            q = prompt_lower.split(" and ", 1)[-1]
        elif "on my screen" in prompt_lower:
             q = prompt_lower.replace("on my screen", "").strip()
             
        if len(q) < 10:
            q = "Describe what you see on my screen in detail."
            
        print(f"\n⚡ [Action: Analyzing Screen for '{q}']")
        response = vision_look_at_screen(q)
        return response
        
    # 0.6 Active Browser URL Summarizer (Voice Command)
    if ("summarize" in prompt_lower or "summarise" in prompt_lower) and ("video" in prompt_lower or "screen" in prompt_lower or "youtube" in prompt_lower) and not prompt_lower.startswith("open ") and not prompt_lower.startswith("play "):
        print("\n⚡ [Action: Grabbing URL from Active Browser...]")
        import pyperclip
        import re
        
        # Backup the current clipboard
        old_clipboard = pyperclip.paste()
        
        # Try to copy URL from active browser
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.2)
        
        url = pyperclip.paste()
        
        # Restore clipboard (optional, but polite)
        pyperclip.copy(old_clipboard)
        
        yt_match = re.search(r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w\-_]+)", url)
        if yt_match:
            video_id = yt_match.group(1)
            print(f"🎬 [YouTube: Found URL! Downloading Transcript for {video_id}...]")
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                try:
                    transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB']).fetch()
                except:
                    transcript = next(iter(transcript_list)).fetch()
                full_text = " ".join([t['text'] for t in transcript])
                if len(full_text) > 20000: full_text = full_text[:20000] + "..."
                
                print("🧠 [YouTube: Generating Summary...]")
                ai_prompt = f"Summarize this YouTube video transcript in 3-5 bullet points. Be highly detailed. Transcript:\n{full_text}"
                
                try:
                    # Send to NIM/Groq for fast summary
                    client_to_use = nim_gemma_client if nim_gemma_client else (groq_client if groq_client else nim_client)
                    model_to_use = FAST_CHAT_MODEL if client_to_use in [nim_gemma_client, groq_client] else MAIN_BRAIN_MODEL
                    
                    response = client_to_use.chat.completions.create(
                        model=model_to_use,
                        messages=[{"role": "user", "content": ai_prompt}],
                        max_tokens=500
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    return f"I found the transcript, but I failed to summarize it: {e}"
            except Exception:
                return "I found the YouTube link, but the video doesn't have English subtitles available for me to read, sir."
        else:
            return "I could not find a YouTube video active on your screen, sir. Make sure the video is open and focused in your browser."
        
    # 1. Search the web
    if prompt_lower.startswith("search for ") or prompt_lower.startswith("google "):
        query = prompt_lower[11:] if prompt_lower.startswith("search for ") else prompt_lower[7:]
        print(f"\n⚡ [Action: Searching the web for '{query}']")
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return f"I have opened a web search for '{query}', sir."
        
    # 1.2 Autonomous Web Scraper (Playwright)
    if any(word in prompt_lower for word in ["scrape", "read this website", "summarize the article", "summarize this website", "visit the website"]):
        print("\n⚡ [Action: Routing to Headless Web Scraper]")
        import web_scraper
        
        # If the user didn't explicitly say the URL, pause and ask them to type/paste it
        if "http" not in prompt_lower:
            if is_discord:
                return "Sir, please include the 'http' link in your Discord message so I can scrape it."
            
            stop_speaking()
            print("\n" + "="*50)
            url_input = input("🔗 Please paste the URL you want me to scrape here: ")
            print("="*50 + "\n")
            prompt += f" {url_input}"
            
        # Pass the global groq/nim clients to the scraper so it can think
        return web_scraper.scrape_and_analyze(prompt, nim_client=nim_client, groq_client=groq_client)

        
    # 1.5 Advanced AI Email Generation
    if "send an email to " in prompt_lower or "draft an email to " in prompt_lower or "email " in prompt_lower:
        if "send an email to " in prompt_lower:
            text = prompt_lower.split("send an email to ", 1)[1]
        elif "draft an email to " in prompt_lower:
            text = prompt_lower.split("draft an email to ", 1)[1]
        else:
            text = prompt_lower.split("email ", 1)[1]
            
        text = text.strip()
        
        address = ""
        topic = ""
        
        if " about " in text:
            address, topic = text.split(" about ", 1)
        elif " for " in text:
            address, topic = text.split(" for ", 1)
        elif " saying " in text:
            address, topic = text.split(" saying ", 1)
        else:
            # Try to extract just the email if no separator is found
            parts = text.split(" ", 1)
            address = parts[0]
            topic = parts[1] if len(parts) > 1 else "just saying hello"
            
        address = address.replace(" at ", "@").replace(" ", "").strip()
        
        print(f"\n⚡ [Action: Brainstorming Email to '{address}'...]")
        
        # Pre-calculate dates because small LLMs are bad at math
        from datetime import datetime, timedelta
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        date_context = f"Today is {today.strftime('%A, %B %d, %Y')}. Tomorrow is {tomorrow.strftime('%A, %B %d, %Y')}. Next week is {next_week.strftime('%A, %B %d, %Y')}."
        
        # Ask the AI to write a perfect subject and body
        ai_prompt = f"{date_context}\nWrite an EXTREMELY FORMAL and PROFESSIONAL business email based exactly on this instruction: '{topic}'.\n\nCRITICAL RULES:\n1. Use highly formal, polite, and sophisticated corporate language.\n2. Use the EXACT DATES provided above if the user mentions 'tomorrow', 'next week', etc.\n3. NEVER use brackets or placeholders like [Name] or [Date]. If a name is missing, just omit it naturally.\n4. Output ONLY in this exact format:\nSUBJECT: <your subject>\nBODY: <your body>"
        
        try:
            # We use Groq or NIM for instant generation
            client_to_use = nim_gemma_client if nim_gemma_client else (groq_client if groq_client else nim_client)
            model_to_use = FAST_CHAT_MODEL if client_to_use in [nim_gemma_client, groq_client] else MAIN_BRAIN_MODEL
            
            response = client_to_use.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": ai_prompt}],
                max_tokens=300
            )
            ai_text = response.choices[0].message.content.strip()
            
            # Parse the AI's response
            subject = "Jarvis Message"
            body = ai_text
            
            if "SUBJECT:" in ai_text and "BODY:" in ai_text:
                subject_part, body_part = ai_text.split("BODY:", 1)
                subject = subject_part.replace("SUBJECT:", "").strip()
                body = body_part.strip()
                
        except Exception as e:
            print(f"[Email Brain Error]: {e}")
            subject = "Message from Jarvis"
            body = topic
            
        print(f"⚡ [Action: Sending Email...]")
        status = send_email_background(address, subject, body)
        return status
            
    # 1.8 YouTube Auto-Play
    if prompt_lower.startswith("play ") and " music" not in prompt_lower and " media" not in prompt_lower:
        query = prompt_lower.replace("play ", "", 1).replace(" on youtube", "").strip()
        print(f"\n⚡ [Action: Auto-Playing '{query}' on YouTube]")
        try:
            import pywhatkit
            pywhatkit.playonyt(query)
            return f"I have started playing '{query}' on YouTube, sir."
        except Exception as e:
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return f"I searched YouTube for '{query}', sir."
            
    if prompt_lower.startswith("open "):
        target = prompt_lower[5:].strip()
        
        # Clean up common phrases
        target = target.replace(" in chrome", "").replace(" in edge", "").replace(" in browser", "")
        
        # Extract message if present
        message = None
        if " and send message " in target:
            target, message = target.split(" and send message ", 1)
        elif " and send " in target:
            target, message = target.split(" and send ", 1)
        if message: message = message.strip()
            
        # Extract search query if present
        query = None
        if " and search for " in target:
            target, query = target.split(" and search for ", 1)
        elif " and search " in target:
            target, query = target.split(" and search ", 1)
            
        if query:
            target = target.strip()
            query = query.strip()
            
        # Isolate the first main word/target
        first_word = target.split()[0]
        
        # Handle special case: "open youtube and search for X"
        if first_word == "youtube" and query:
            should_summarize = "summarize" in query or "summarise" in query
            if should_summarize:
                query = query.replace("and summarize that", "").replace("and summarise that", "").replace("and summarize", "").replace("and summarise", "")
                
            query = query.replace("and play latest video", "latest video").replace("and play", "").strip()
                
            print(f"\n⚡ [Action: Searching YouTube for '{query}']")
            try:
                import pywhatkit
                pywhatkit.playonyt(query)
            except Exception as e:
                webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
                return f"I am searching YouTube for '{query}', sir."
                
            if should_summarize:
                try:
                    print("⏳ [Waiting for YouTube to load video...]")
                    time.sleep(10.0) # wait for video to play
                    
                    # Grab URL from active browser
                    import pyperclip
                    old_clipboard = pyperclip.paste() or ""
                    pyautogui.hotkey('ctrl', 'l')
                    time.sleep(0.2)
                    pyautogui.hotkey('ctrl', 'c')
                    time.sleep(0.2)
                    url = pyperclip.paste()
                    pyperclip.copy(old_clipboard)
                    
                    import re
                    yt_match = re.search(r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w\-_]+)", url)
                    if yt_match:
                        try:
                            video_id = yt_match.group(1)
                            from youtube_transcript_api import YouTubeTranscriptApi
                            transcript_list = YouTubeTranscriptApi().list(video_id)
                            try:
                                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB']).fetch()
                            except:
                                transcript = next(iter(transcript_list)).fetch()
                            full_text = " ".join([t.text for t in transcript])
                            if len(full_text) > 20000: full_text = full_text[:20000] + "..."
                            
                            ai_prompt = f"Summarize this YouTube video transcript in 3-5 bullet points. Be highly detailed. Transcript:\n{full_text}"
                            client_to_use = nim_gemma_client if nim_gemma_client else (groq_client if groq_client else nim_client)
                            model_to_use = FAST_CHAT_MODEL if client_to_use in [nim_gemma_client, groq_client] else MAIN_BRAIN_MODEL
                            
                            response = client_to_use.chat.completions.create(
                                model=model_to_use,
                                messages=[{"role": "user", "content": ai_prompt}],
                                max_tokens=500
                            )
                            return f"I have started the video! Here is the summary:\n\n{response.choices[0].message.content.strip()}"
                        except Exception as inner_e:
                            return f"I started the video, but I failed to summarize it. Error: {inner_e}"
                    else:
                        return f"I started playing '{query}', but I failed to extract the URL from your browser to summarize it. Please make sure the browser window was active!"
                except Exception as sum_e:
                    return f"I started playing '{query}', but an internal error crashed the summarizer: {sum_e}"
            
            return f"Playing '{query}' on YouTube, sir."
            
        print(f"\n⚡ [Action: Opening '{first_word}']")
        
        # Check if it's a website or common app
        if "." in first_word or first_word in ["youtube", "google", "facebook", "github", "reddit", "twitter"]:
            url = f"https://{first_word}.com" if "." not in first_word else (f"https://{first_word}" if not first_word.startswith("http") else first_word)
            webbrowser.open(url)
            return f"Opening website {first_word}, sir."
        else:
            # Open app via Windows Start Menu (foolproof for Store apps like WhatsApp)
            try:
                pyautogui.press("win")
                time.sleep(0.5)
                pyautogui.write(first_word, interval=0.05)
                time.sleep(0.5)
                pyautogui.press("enter")
                
                if query:
                    print(f"⏳ [Waiting for {first_word} to load before searching...]")
                    time.sleep(3.0) # Wait 3 seconds for app to fully open
                    pyautogui.hotkey('ctrl', 'f') # Universal Windows search shortcut
                    time.sleep(0.5)
                    pyautogui.write(query, interval=0.05)
                    
                    if message:
                        print(f"⏳ [Opening chat and typing message...]")
                        time.sleep(1.5) # Wait for search results to appear
                        pyautogui.press('down') # Move to the first search result
                        time.sleep(0.2)
                        pyautogui.press('enter') # Open the chat
                        time.sleep(1.0) # Wait for chat interface to load
                        pyautogui.write(message, interval=0.05) # Type the message
                        time.sleep(0.5)
                        pyautogui.press('enter') # Send the message!
                        return f"I have launched {first_word}, found {query}, and sent your message, sir."
                        
                    return f"I have launched {first_word} and searched for '{query}', sir."
                    
                return f"I have launched {first_word} for you, sir."
            except Exception as e:
                return f"I encountered an error trying to open {first_word}: {e}"
                
    # 3. Look at screen (vision)
    if any(p in prompt_lower for p in ["what's on my screen", "what is on my screen", "look at my screen", "what do you see", "read the screen", "describe the screen", "what's open"]):
        reply = vision_look_at_screen(prompt)
        return reply
        
    # 4. Take a screenshot
    if "screenshot" in prompt_lower or "capture screen" in prompt_lower:
        print(f"\n⚡ [Action: Taking Screenshot]")
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        return f"Screenshot saved successfully as {filename} in your Jarvis folder, sir."
        
    # 4. Type text
    if prompt_lower.startswith("type "):
        text_to_type = prompt[len(prompt) - len(prompt_lower) + 5:] # preserve original case
        print(f"\n⚡ [Action: Typing Text]")
        pyautogui.write(text_to_type, interval=0.05)
        return f"I have typed the text for you, sir."
        
    # 5. Volume Controls
    if "mute" in prompt_lower or "unmute" in prompt_lower:
        print(f"\n⚡ [Action: Toggling Mute]")
        pyautogui.press("volumemute")
        return "I have toggled the system volume, sir."
    if any(p in prompt_lower for p in ["volume up", "increase volume", "increase the volume", "turn up the volume", "turn volume up", "louder"]):
        # Extract percentage from command (e.g. "by 40 percent" or "by 40%")
        match = re.search(r'by\s+(\d+)\s*(?:percent|%)?', prompt_lower)
        pct = int(match.group(1)) if match else 20 # Default to 20% if no number given
        presses = max(1, round(pct / 2)) # Each key press = ~2% on Windows
        print(f"\n⚡ [Action: Increasing Volume by {pct}% ({presses} presses)]")
        for _ in range(presses): pyautogui.press("volumeup")
        return f"I have increased the volume by {pct}%, sir."
    if any(p in prompt_lower for p in ["volume down", "decrease volume", "decrease the volume", "turn down the volume", "turn volume down", "quieter", "lower the volume"]):
        match = re.search(r'by\s+(\d+)\s*(?:percent|%)?', prompt_lower)
        pct = int(match.group(1)) if match else 20
        presses = max(1, round(pct / 2))
        print(f"\n⚡ [Action: Decreasing Volume by {pct}% ({presses} presses)]")
        for _ in range(presses): pyautogui.press("volumedown")
        return f"I have decreased the volume by {pct}%, sir."
        
    # 6. Media Controls
    if prompt_lower in ["pause", "play", "stop", "resume"] or "play music" in prompt_lower or "pause music" in prompt_lower or "play media" in prompt_lower or "pause media" in prompt_lower:
        print(f"\n⚡ [Action: Play/Pause Media]")
        pyautogui.press("playpause")
        return "I have toggled the media playback, sir."
    if prompt_lower in ["skip", "next"] or "next song" in prompt_lower or "next track" in prompt_lower or "skip song" in prompt_lower:
        print(f"\n⚡ [Action: Next Track]")
        pyautogui.press("nexttrack")
        return "Skipping to the next track, sir."
    if prompt_lower in ["previous", "back"] or "previous song" in prompt_lower or "previous track" in prompt_lower or "go back" in prompt_lower:
        print(f"\n⚡ [Action: Previous Track]")
        pyautogui.press("prevtrack")
        return "Playing the previous track, sir."
        
    # 7. Window Management
    if "minimize everything" in prompt_lower or "show desktop" in prompt_lower:
        print(f"\n⚡ [Action: Minimizing All Windows]")
        pyautogui.hotkey("win", "d")
        return "I have minimized all windows, sir."
    if "close this window" in prompt_lower or "close current window" in prompt_lower:
        print(f"\n⚡ [Action: Closing Window]")
        pyautogui.hotkey("alt", "f4")
        return "I have closed the active window, sir."
        
    # 8. System Power Controls
    if "shutdown computer" in prompt_lower or "turn off computer" in prompt_lower or "shut down" in prompt_lower:
        print(f"\n⚡ [Action: Shutting Down Computer]")
        os.system("shutdown /s /t 5")
        return "Initiating system shutdown in 5 seconds, sir."
    if "restart computer" in prompt_lower or "reboot computer" in prompt_lower or "restart" in prompt_lower:
        print(f"\n⚡ [Action: Restarting Computer]")
        os.system("shutdown /r /t 5")
        return "Initiating system restart in 5 seconds, sir."
    if "sleep computer" in prompt_lower or "go to sleep" in prompt_lower or "lock computer" in prompt_lower:
        print(f"\n⚡ [Action: Locking/Sleeping Computer]")
        # Safe sleep/lock command
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "I have locked the system, sir."
        
    return None # Not a computer action

def wake_word_worker():
    """Background thread that listens for 'Hey Jarvis' and triggers the main loop."""
    global is_mic_busy
    try:
        from openwakeword.model import Model
        import pyaudio
    except ImportError:
        return # Missing dependencies
        
    oww_model = Model(wakeword_models=['hey_jarvis'])
    audio = pyaudio.PyAudio()
    mic_stream = None
    
    while True:
        if is_mic_busy:
            if mic_stream is not None:
                mic_stream.stop_stream()
                mic_stream.close()
                mic_stream = None
            time.sleep(0.5)
            continue
            
        if mic_stream is None:
            try:
                mic_stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
            except Exception as e:
                print(f"\n[Wake Word Error]: Microphone unavailable - {e}")
                time.sleep(2)
                continue
                
        try:
            audio_data = np.frombuffer(mic_stream.read(1024, exception_on_overflow=False), dtype=np.int16)
            prediction = oww_model.predict(audio_data)
            
            # Check all models (though we only loaded one)
            max_score = max(prediction.values()) if prediction else 0
            
            # Print scores occasionally if they are close, to help debug
            if max_score > 0.05:
                print(f"👂 [Wake Word Engine: Heard something similar... Confidence: {max_score:.2f}]")
                
            # Lowered from 0.5 to 0.15 to allow for accents and "Hey Zarvis"
            if max_score > 0.15:
                is_mic_busy = True # Lock mic
                if mic_stream is not None:
                    mic_stream.stop_stream()
                    mic_stream.close()
                    mic_stream = None
                
                # Stop any ongoing speech
                stop_speaking()
                
                # Acknowledge
                print("\n🟢 [Wake Word Detected]")
                # Signal main thread to start listening
                wake_word_event.set()
                time.sleep(1) # Cooldown to prevent instant re-trigger
                
                # Wait for main thread to finish its listening cycle before resetting
                while is_mic_busy:
                    time.sleep(0.5)
        except Exception as e:
            time.sleep(0.5)

def discord_worker():
    """Step 12: Discord Phone Access. Allows Setty to chat with Jarvis from anywhere."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token or "your_" in token:
        print("📱 [Discord] No valid token found in .env. Phone access disabled.")
        return
        
    try:
        import discord
    except ImportError:
        print("📱 [Discord Error] discord.py is not installed.")
        return

    class JarvisClient(discord.Client):
        async def on_ready(self):
            print(f"📱 [Discord: System Online - Logged in as {self.user}]")

        async def on_message(self, message):
            # Don't respond to ourselves
            if message.author == self.user: return
            
            # Check if it's a DM, a mention, or starts with 'jarvis'
            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mention = self.user in message.mentions
            is_named = message.content.lower().startswith('jarvis')
            
            if not (is_dm or is_mention or is_named):
                return

            # Clean up the text
            text = message.content.replace(f'<@{self.user.id}>', '').strip()
            if text.lower().startswith('jarvis'):
                text = text[6:].strip()
                
            print(f"\n📱 [Discord from {message.author}]: {text}")
            
            async with message.channel.typing():
                messages = [{"role": "system", "content": load_soul()}]
                messages.append({"role": "user", "content": text})
                
                # Fast-path for simple computer commands (Bypass safety check for hardcoded actions)
                loop = asyncio.get_event_loop()
                action_response = await loop.run_in_executor(None, lambda: execute_computer_action(text, is_discord=True))
                
                if action_response:
                    print(action_response)
                    reply = action_response
                else:
                    if not check_safety(text):
                        reply = "I'm sorry, sir, but my safety protocols prevent me from executing that request."
                    else:
                        route = determine_route(text)
                        loop = asyncio.get_event_loop()
                        
                        if route == "nim_code":
                            reply = await loop.run_in_executor(None, lambda: chat_cloud_openai_compatible(nim_qwen_client, CODING_MODEL, messages, mute=True))
                        elif route == "nim_reason":
                            extra = {"extra_body": {"chat_template_kwargs": {"thinking": True}}}
                            reply = await loop.run_in_executor(None, lambda: chat_cloud_openai_compatible(nim_client, REASONING_MODEL, messages, extra_kwargs=extra, mute=True))
                        elif route == "deepseek":
                            reply = await loop.run_in_executor(None, lambda: chat_cloud_openai_compatible(deepseek_client, REASONING_MODEL, messages, mute=True))
                        elif route == "groq_chat":
                            if nim_gemma_client:
                                reply = await loop.run_in_executor(None, lambda: chat_cloud_openai_compatible(nim_gemma_client, FAST_CHAT_MODEL, messages, mute=True))
                            else:
                                reply = await loop.run_in_executor(None, lambda: chat_cloud_openai_compatible(groq_client, FAST_CHAT_MODEL, messages, mute=True))
                        else:
                            if nim_client:
                                reply = await loop.run_in_executor(None, lambda: chat_cloud_openai_compatible(nim_client, MAIN_BRAIN_MODEL, messages, mute=True))
                            else:
                                reply = "Brain offline."
                            
            # Discord has a 2000 char limit
            if len(reply) > 1900:
                for i in range(0, len(reply), 1900):
                    await message.channel.send(reply[i:i+1900])
            else:
                await message.channel.send(reply)
            print(f"📱 [Discord: Reply sent to {message.author}.]")

    intents = discord.Intents.default()
    intents.message_content = True
    client = JarvisClient(intents=intents)
    
    # Run discord bot in its own event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.start(token))
    except Exception as e:
        print(f"📱 [Discord Error]: {e}")

def main():
    global whisper_model
    print("Initializing Jarvis Systems...")
    
    # Mixer initialization removed from here (now inside tts_worker thread)
    print(f"API Keys Loaded: Groq [{'YES' if GROQ_API_KEY else 'NO'}], NIM [{'YES' if NIM_API_KEY else 'NO'}], Gemini [{'YES' if GEMINI_API_KEY else 'NO'}]")
    
    # Pre-load the Whisper STT Model during boot to prevent first-time latency
    print("\n⏳ [Pre-loading Voice Module into Memory...]")
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        print(f"🎙️ [Loading Whisper {VOICE_INPUT_MODEL} on {device.upper()}...]")
        whisper_model = WhisperModel("small.en", device=device, compute_type=compute)
    except Exception as e:
        print(f"[Voice Warning] Fast load failed, falling back to basic CPU: {e}")
        whisper_model = WhisperModel("small.en", device="cpu", compute_type="int8")
        
    system_prompt = load_soul()
    messages = [{"role": "system", "content": system_prompt}]
    
    # Load past memory
    past_memory = load_memory()
    if past_memory:
        messages.extend(past_memory)
        print(f"🧠 [Memory Restored: {len(past_memory)} previous messages loaded]")
        
    print("\n⏳ [Initializing Wake Word System...]")
    t = threading.Thread(target=wake_word_worker, daemon=True)
    t.start()
    
    # Start Discord Worker (Step 12)
    t_disc = threading.Thread(target=discord_worker, daemon=True)
    t_disc.start()
    
    print("\nJarvis is online. Say 'Hey Jarvis' to wake me up. Press Ctrl+C to stop.")
    print("-" * 50)
    
    global is_mic_busy
    while True:
        try:
            # is_mic_busy is now handled at the end of the loop to ensure speech finishes
            wake_word_event.clear()
            
            print("\n🔵 [Standby] Waiting for 'Hey Jarvis'...")
            
            # Block until wake word is detected
            while not wake_word_event.is_set():
                time.sleep(0.1)
                
            is_mic_busy = True # Lock the mic so wake word thread drops it
            time.sleep(0.2) # Give wake word thread time to release PyAudio
            
            # --- VOICE INPUT MODE ---
            print("\n🎙️ [Calibrating Mic...]")
            with sr.Microphone() as source:
                stt_recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("🎙️ [Listening... Speak now!]")
                try:
                    audio = stt_recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    print("⏳ [Transcribing...]")
                    
                    # Process audio directly in memory
                    # CRITICAL FIX: Whisper ONLY understands 16000 Hz audio! 
                    # If your laptop records at 48000 Hz, Whisper hears fast-forwarded chipmunk garbage.
                    # convert_rate=16000 forces speech_recognition to resample it correctly.
                    raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                    audio_data = np.frombuffer(raw_data, np.int16).flatten().astype(np.float32) / 32768.0
                    
                    # --- THE FIX: AUDIO NORMALIZATION ---
                    # If the microphone is quiet (like max volume 2750), Whisper and VAD will filter it out.
                    # This boosts the volume to the maximum level without distorting it!
                    max_amp = np.max(np.abs(audio_data))
                    if max_amp > 0:
                        audio_data = audio_data / max_amp
                    
                    # Transcribe using faster-whisper with Voice Activity Detection (VAD)
                    # VAD completely prevents hallucinations caused by silence/static
                    segments, info = whisper_model.transcribe(
                        audio_data, 
                        beam_size=5, 
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=500)
                    )
                    user_input = "".join([segment.text for segment in segments]).strip()
                    
                    if not user_input:
                        continue
                        
                    print(f"You (Voice): {user_input}")
                    
                except sr.WaitTimeoutError:
                    print("[No speech detected.]")
                    continue
                except Exception as e:
                    print(f"[Speech Error: {e}]")
                    continue
            
            # Add to history
            messages.append({"role": "user", "content": user_input})
            
            # Check if this is a computer command first
            action_response = execute_computer_action(user_input)
            
            print("Jarvis: ", end="", flush=True)
            
            if action_response:
                print(action_response)
                reply = action_response
                speak(reply) # Speak action since it didn't stream
            else:
                # Run Safety Check
                if not check_safety(user_input):
                    reply = "I'm sorry, sir, but my safety protocols prevent me from executing that request."
                    print(f"\nJarvis: {reply}")
                    speak(reply)
                    messages.append({"role": "assistant", "content": reply})
                    continue
                
                # Smart Routing for conversational/complex requests
                route = determine_route(user_input)
                
                if route == "vision":
                    reply = vision_look_at_screen(user_input)
                    print(f"Jarvis: {reply}")
                    speak(reply) # Speak vision since it didn't stream
                elif route == "personal_data":
                    topic = user_input.lower().split(" on ")[-1] if " on " in user_input.lower() else user_input.lower()
                    folder = os.path.join(os.path.dirname(__file__), "personal_data")
                    file_found = False
                    if os.path.exists(folder):
                        for filename in os.listdir(folder):
                            if topic.replace("read my notes", "").replace("read my file", "").strip() in filename.lower() and filename.endswith(('.txt', '.md')):
                                with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
                                    content = f.read()
                                print(f"\n⚡ [Action: Reading Personal File '{filename}']")
                                messages[-1]["content"] = f"User said: {user_input}\n\n[System injected file {filename}]:\n{content}"
                                file_found = True
                                break
                    if not file_found:
                        messages[-1]["content"] = f"User said: {user_input}\n\n[System note: No matching file found in personal_data folder.]"
                    
                    # Route to main brain to summarize or answer based on the injected document
                    reply = chat_cloud_openai_compatible(nim_client, MAIN_BRAIN_MODEL, messages) if nim_client else chat_local(messages)
                elif route == "audio_vision":
                    reply = phi_audio_vision_analysis(user_input)
                    print(f"Jarvis: {reply}")
                    speak(reply) # Speak multimodal response
                elif route == "nim_code":
                    reply = chat_cloud_openai_compatible(nim_qwen_client, CODING_MODEL, messages)
                elif route == "nim_reason":
                    extra = {"extra_body": {"chat_template_kwargs": {"thinking": True}}}
                    # Assuming you want NIM logic here (Gemma didn't need a specific client since we didn't assign it as REASONING_MODEL)
                    # We will use nim_client which defaults to Maverick key, or deepseek directly.
                    reply = chat_cloud_openai_compatible(nim_client, REASONING_MODEL, messages, extra_kwargs=extra)
                elif route == "deepseek":
                    reply = chat_cloud_openai_compatible(deepseek_client, REASONING_MODEL, messages)
                elif route == "groq_chat":
                    reply = chat_cloud_openai_compatible(nim_gemma_client, FAST_CHAT_MODEL, messages) if nim_gemma_client else chat_cloud_openai_compatible(groq_client, FAST_CHAT_MODEL, messages)
                else:
                    reply = chat_cloud_openai_compatible(nim_client, MAIN_BRAIN_MODEL, messages) if nim_client else chat_local(messages)
            
            messages.append({"role": "assistant", "content": reply})
            
            # Save memory after every interaction
            save_memory(messages)
            
            # --- TRUE VOICE INTERRUPTION ---
            # Unlock the microphone while he is speaking so he can be interrupted!
            is_mic_busy = False 
            
            print("\n⏳ [Jarvis is speaking... You can say 'Hey Jarvis' to interrupt]")
            while is_speaking():
                if wake_word_event.is_set():
                    print("\n🛑 [Interrupted by User]")
                    stop_speaking()
                    break
                time.sleep(0.1)
                
            # If we were NOT interrupted, we explicitly clear the event to prevent instant re-triggering from echoes
            wake_word_event.clear()
            
            # --- ACOUSTIC ECHO PREVENTION ---
            # Wait 0.8s for the physical speakers to completely finish reverberating in the room
            # before we open the microphone again, so he doesn't hear his own last word!
            time.sleep(0.8)
            
            
        except KeyboardInterrupt:
            print("\nJarvis: Shutting down systems. Goodbye, sir.")
            break
        except Exception as e:
            print(f"\nJarvis [CRITICAL ERROR]: {e}")

if __name__ == "__main__":
    main()
