"""
JARVIS V2 - YouTube Automation & Summarization Tools
"""
import re
import time
import webbrowser
try:
    import pywhatkit
except ImportError:
    pywhatkit = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

from pydantic import BaseModel, Field
from core.schemas import RiskLevel
from security.prompt_injection import prompt_defense
from tools.base_tool import BaseTool

class PlayYouTubeArgs(BaseModel):
    query: str = Field(description="Search term or video title to play on YouTube")

class SummarizeYouTubeArgs(BaseModel):
    video_url_or_id: str = Field(description="YouTube full URL or 11-character video ID")

class PlayYouTubeTool(BaseTool):
    name = "youtube_play_video"
    description = "Searches and plays a video on YouTube in your default browser."
    risk_level = RiskLevel.LEVEL_2
    args_schema = PlayYouTubeArgs

    def execute(self, query: str, **kwargs) -> str:
        if pywhatkit:
            try:
                pywhatkit.playonyt(query)
                return f"Playing '{query}' on YouTube, sir."
            except Exception:
                pass
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        return f"Opened YouTube search for '{query}', sir."

class SummarizeYouTubeTranscriptTool(BaseTool):
    name = "youtube_summarize_transcript"
    description = "Downloads English subtitle transcripts for a YouTube video and creates a bullet-point summary."
    risk_level = RiskLevel.LEVEL_1
    args_schema = SummarizeYouTubeArgs

    def execute(self, video_url_or_id: str, **kwargs) -> str:
        if not YouTubeTranscriptApi:
            return "Transcript summarization is currently unavailable: youtube_transcript_api is not installed in this environment."

        # Extract 11-character ID
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", video_url_or_id)
        video_id = match.group(1) if match else video_url_or_id.strip()

        print(f"🎬 [YouTube: Downloading Transcript for {video_id}...]")
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB']).fetch()
            except Exception:
                transcript = next(iter(transcript_list)).fetch()

            raw_text = " ".join([t['text'] for t in transcript])
            if len(raw_text) > 20000:
                raw_text = raw_text[:20000] + "... [TRUNCATED]"

            safe_text = prompt_defense.sanitize_untrusted_content(raw_text, source_type=f"YouTube: {video_id}")

            # Summarize via model gateway
            from models.gateway import model_gateway
            from core.schemas import ChatMessage, MessageRole

            prompt = [
                ChatMessage(role=MessageRole.SYSTEM, content="You are Jarvis. Summarize this YouTube video transcript in 3-5 structured, detailed bullet points."),
                ChatMessage(role=MessageRole.USER, content=f"Summarize the video:\n\n{safe_text}")
            ]

            summary_tokens = []
            for token in model_gateway.stream_generate(prompt):
                summary_tokens.append(token)
            return "".join(summary_tokens)

        except Exception as e:
            return f"Could not retrieve transcripts for this YouTube video, sir: {e}"
