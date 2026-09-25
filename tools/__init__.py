"""
JARVIS V2 Tools Package & Auto-Registration
Registers all system, media, communication, productivity, vision, youtube, and browser tools.
"""
from tools.registry import tool_registry
from tools.system.system_tools import SystemStatsTool, LockWorkstationTool, ShutdownTool, MinimizeWindowsTool
from tools.media.media_tools import (
    ToggleMediaTool, NextTrackTool, PreviousTrackTool, MuteVolumeTool,
    VolumeUpTool, VolumeDownTool, MediaVolumeControlTool
)
from tools.productivity.task_tools import (
    AddTaskTool, ListTasksTool, ClearTasksTool, CompleteTaskTool, DeleteTaskTool
)
from tools.productivity.calendar_tools import ListCalendarEventsTool, CreateCalendarEventTool
from tools.communication.email_tools import ListEmailsTool, SendEmailTool
from tools.communication.whatsapp_tools import WhatsAppSendFileTool
from tools.browser.browser_tools import BrowserSearchTool, BrowserNavigateTool, BrowserScrapeTool
from tools.vision.vision_tools import DesktopVisionTool, AudioVisionTool
from tools.youtube.youtube_tools import PlayYouTubeTool, SummarizeYouTubeTranscriptTool
from tools.files.file_tools import ListRecentFilesTool, ListDirectoryTool

# Auto-register all tools
def register_all_tools():
    tools = [
        SystemStatsTool(),
        LockWorkstationTool(),
        ShutdownTool(),
        MinimizeWindowsTool(),
        ToggleMediaTool(),
        NextTrackTool(),
        PreviousTrackTool(),
        MuteVolumeTool(),
        VolumeUpTool(),
        VolumeDownTool(),
        MediaVolumeControlTool(),
        AddTaskTool(),
        ListTasksTool(),
        ClearTasksTool(),
        CompleteTaskTool(),
        DeleteTaskTool(),
        ListCalendarEventsTool(),
        CreateCalendarEventTool(),
        ListEmailsTool(),
        SendEmailTool(),
        WhatsAppSendFileTool(),
        BrowserSearchTool(),
        BrowserNavigateTool(),
        BrowserScrapeTool(),
        DesktopVisionTool(),
        AudioVisionTool(),
        PlayYouTubeTool(),
        SummarizeYouTubeTranscriptTool(),
        ListRecentFilesTool(),
        ListDirectoryTool()
    ]
    for t in tools:
        tool_registry.register(t)

register_all_tools()

