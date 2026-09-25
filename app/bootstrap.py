"""
JARVIS V2 - Bootstrap & Lifecycle Management
Initializes all subsystems, pre-warms local neural models, and launches background threads.
"""
import threading
from core.config import config
from storage.supabase import storage_adapter
from voice.stt import stt_engine
from voice.tts import tts_engine
from voice.wakeword import wake_word_detector
from agents.discord_agent import discord_agent
from tools import register_all_tools

class SystemBootstrapper:
    @staticmethod
    def initialize_system():
        print("=" * 60)
        print("🤖 [BOOTING JARVIS V2: AUTONOMOUS MULTIMODAL AI AGENT OS]")
        print(f"   Environment: {config.ENVIRONMENT.upper()} | Version: {config.VERSION}")
        print("=" * 60)

        # 1. Register all tools
        register_all_tools()
        print("🛠️  [Tool Registry: All Level 0-4 tools registered and verified]")

        # 2. Pre-warm local STT Whisper
        stt_engine.prewarm()

        # 3. Boot TTS Worker Thread
        tts_engine.start_worker()
        print("🔊 [TTS Engine: Edge-TTS worker thread started]")

        # 4. Start Wake Word Detector
        wake_word_detector.start()
        print(f"👂 [Wake Word Engine: openwakeword started ({config.WAKE_WORD_MODEL} @ {config.WAKE_WORD_THRESHOLD})]")

        # 5. Start Discord OpenClaw Daemon Thread
        if config.DISCORD_BOT_TOKEN and "your_" not in config.DISCORD_BOT_TOKEN:
            t_disc = threading.Thread(target=discord_agent.start, daemon=True)
            t_disc.start()
            print("📱 [Discord OpenClaw: Remote access thread launched]")
        else:
            print("📱 [Discord OpenClaw: Disabled (No token provided)]")

        print("⚡ [All Systems Initialized & Operational]")
        print("-" * 60)

bootstrapper = SystemBootstrapper()
