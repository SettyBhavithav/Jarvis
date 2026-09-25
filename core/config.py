"""
JARVIS V2 - Core Configuration System
Centralized, validated configuration with environment variable overrides.
"""
from typing import List, Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class JarvisConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- Project Metadata ---
    PROJECT_NAME: str = "JARVIS"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # --- Cloud API Keys ---
    GROQ_API_KEY: Optional[str] = None
    NIM_API_KEY: Optional[str] = None
    NIM_QWEN_API_KEY: Optional[str] = None
    NIM_GEMMA_API_KEY: Optional[str] = None
    NIM_VISION_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # --- Models ---
    FAST_CHAT_MODEL: str = "qwen/qwen3.8-27b"
    MAIN_BRAIN_MODEL: str = "qwen/qwen3.8-27b"
    CODING_MODEL: str = "deepseek-ai/deepseek-chat"
    REASONING_MODEL: str = "deepseek-ai/deepseek-reasoner"
    VISION_MODEL: str = "meta/llama-3.2-11b-vision-instruct"
    AUDIO_VISION_MODEL: str = "microsoft/phi-4-multimodal-instruct"
    OFFLINE_MODEL: str = "llama3.1:8b"
    SAFETY_MODEL: str = "meta/llama-guard-4-12b"

    # --- NVIDIA NIM Backup / Fallback Models (First-Party NVIDIA Models) ---
    NIM_BACKUP_CHAT_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    NIM_BACKUP_CODE_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b"
    NIM_BACKUP_REASONING_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b"
    NIM_BACKUP_VISION_MODEL: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

    # --- Voice Settings ---
    STT_PROVIDER: str = "groq"
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"
    VOICE_INPUT_MODEL: str = "small.en"
    WAKE_WORD_MODEL: str = "hey_jarvis"
    WAKE_WORD_THRESHOLD: float = 0.15
    TTS_VOICE: str = "en-US-GuyNeural"
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_NORMALIZATION: bool = True
    VAD_MIN_SILENCE_DURATION_MS: int = 500
    REVERB_DECAY_DELAY: float = 0.8  # Seconds to wait for physical speaker echo decay

    # --- Supabase & Storage ---
    SUPABASE_URL: Optional[str] = Field(default=None, validation_alias=AliasChoices("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL"))
    SUPABASE_KEY: Optional[str] = Field(default=None, validation_alias=AliasChoices("SUPABASE_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY"))
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    LOCAL_DB_PATH: str = "jarvis_local_cache.db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # --- Discord OpenClaw ---
    DISCORD_BOT_TOKEN: Optional[str] = None
    DISCORD_ALLOWED_USER_IDS: List[int] = Field(default_factory=list)

    # --- Policy & Safety ---
    REQUIRE_CONFIRMATION_FOR_LEVEL_3: bool = True
    REQUIRE_CONFIRMATION_FOR_LEVEL_4: bool = True
    ENABLE_LLAMA_GUARD: bool = True
    MAX_TOOL_TIMEOUT_SECONDS: int = 30
    DEFAULT_USER_NAME: str = "Setty Bhavithav"

# Global Config Instance
config = JarvisConfig()
