# JARVIS: Autonomous AI Assistant & System Architect
**Project Overview & Technical Documentation**

## 1. Core Architecture & Multi-Modal Routing
JARVIS is not a standard chatbot. He operates using a **Dynamic Heuristic Router** that analyzes the user's intent in real-time and routes the query to the most efficient LLM for the task:
* **Groq (LPU) - `llama-3.1-70b-versatile`:** Used for blazing-fast, sub-second conversational responses and general queries.
* **DeepSeek - `deepseek-chat` / `deepseek-reasoner`:** Triggered implicitly for high-level coding, debugging, and complex logical reasoning tasks.
* **NVIDIA NIM - `meta/llama-3.2-11b-vision-instruct`:** Dedicated purely to Desktop Computer Vision, allowing Jarvis to physically "see" the screen.
* **Ollama (Local Fallback):** If the internet disconnects, Jarvis seamlessly falls back to a locally hosted LLM to ensure core systems remain online.

## 2. Long-Term Memory System (RAG)
Jarvis possesses true long-term memory. He does not rely on massive context windows that clear out when the script restarts.
* **Vector Database:** Utilizes **MongoDB Atlas**.
* **Embedding Model:** Uses local `sentence-transformers` (`all-MiniLM-L6-v2`) to encode user preferences, daily routines, and specific project details into mathematical vectors.
* **Recall Mechanism:** During a conversation, Jarvis performs a cosine similarity search against the vector database to inject relevant past memories into his prompt natively, creating a persistent, evolving relationship with the user.

## 3. Advanced Voice Architecture
The voice system was engineered from scratch to mimic true human interaction, prioritizing speed, accuracy, and interruptibility.
* **Wake Word Engine (`openwakeword`):** Runs on a dedicated background thread. The threshold has been aggressively fine-tuned (`0.15` confidence) to recognize natural slangs and accents (e.g., "Hey Zarvis") without requiring robotic enunciation.
* **Speech-to-Text (`faster-whisper`):** Features active Voice Activity Detection (VAD) and 16kHz real-time audio normalization. This physically prevents the engine from hallucinating words out of background static.
* **Text-to-Speech (`edge-tts`):** Streams Microsoft's `en-US-GuyNeural` voice. Includes a custom text-sanitization pipeline to strip markdown and emojis before playback.
* **True Voice Interruption:** Jarvis's microphone unlocks *while* he is speaking. If the Wake Word Engine hears the user interrupt, it instantly flushes the TTS queue, halts the physical speaker, and employs an 0.8s acoustic reverb delay to prevent echo loops, allowing for flawless conversational overlap.

## 4. Heuristic Action Controller (Physical OS Automation)
Unlike standard LLMs restricted to text, Jarvis is hardcoded with Python modules to interact with the physical operating system autonomously.
* **Implicit Screen Awareness:** By listening for pronouns like *"What is this error?"* or *"Look at this"*, Jarvis autonomously takes a screenshot of the user's desktop, routes it to the NIM Vision model, and verbally explains the UI or code error.
* **Headless Web Scraping:** Using `playwright`, Jarvis can spin up an invisible Chromium browser, navigate to a URL, bypass strict DOM locators to extract raw text, and summarize entire websites.
* **YouTube Chaining:** Jarvis can autonomously grab the active URL from the browser, fetch the subtitle transcript via `youtube_transcript_api`, and summarize hour-long videos in seconds.
* **Autonomous Background Emailing:** Authenticated via OAuth2 and the Gmail API, Jarvis can write formal corporate emails and send them silently in the background without launching a browser or requiring UI interaction.
* **WhatsApp Automation:** He can parse the user's filesystem, locate specific documents, open WhatsApp Desktop, and autonomously send files to contacts.
* **Media Orchestration:** Injects OS-level `pyautogui` hooks to control Spotify and system media playback with zero latency.
* **System Diagnostics & Calendar:** Interfaces with `psutil` to track real-time hardware health (CPU/RAM/Storage) and the Google Calendar API to read daily schedules.

## 5. Remote Access via Discord (OpenClaw)
Jarvis is not bound to the local PC terminal. He is tethered to a private Discord Bot.
* The user can send text messages from their phone to Jarvis via Discord.
* The Discord integration is tied directly into the Heuristic Action Controller, meaning the user can remotely trigger web scrapes, system diagnostics, or LLM queries from anywhere in the world.

---
**Developed for Setty Bhavithav**
*Status: Production Ready | Version: 2.0*
