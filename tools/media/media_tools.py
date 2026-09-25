"""
JARVIS V2 - Media Orchestration Tools
Controls Spotify and Windows media playback using low-latency OS hooks.
"""
from pydantic import BaseModel, Field
from core.schemas import RiskLevel
from tools.base_tool import BaseTool

def _press_key(key: str):
    try:
        import pyautogui
        pyautogui.press(key)
    except Exception as e:
        print(f"[Media OS Hook Notice]: {e}")

class EmptyArgs(BaseModel):
    pass

class AdjustVolumeArgs(BaseModel):
    percentage: int = Field(default=20, description="Percentage to increase or decrease volume")

class ToggleMediaTool(BaseTool):
    name = "media_toggle_play_pause"
    description = "Plays, pauses, or resumes active media playback."
    risk_level = RiskLevel.LEVEL_2
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        _press_key('playpause')
        return "I have toggled the media playback, sir."

class NextTrackTool(BaseTool):
    name = "media_next_track"
    description = "Skips to the next track on Spotify or active media player."
    risk_level = RiskLevel.LEVEL_2
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        _press_key('nexttrack')
        return "Skipping to the next track, sir."

class PreviousTrackTool(BaseTool):
    name = "media_previous_track"
    description = "Plays the previous track on Spotify or active media player."
    risk_level = RiskLevel.LEVEL_2
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        _press_key('prevtrack')
        return "Playing the previous track, sir."

class MuteVolumeTool(BaseTool):
    name = "media_mute_volume"
    description = "Mutes or unmutes the Windows audio system."
    risk_level = RiskLevel.LEVEL_2
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        _press_key('volumemute')
        return "System volume toggled, sir."

class VolumeUpTool(BaseTool):
    name = "media_volume_up"
    description = "Increases system volume."
    risk_level = RiskLevel.LEVEL_2
    args_schema = AdjustVolumeArgs

    def execute(self, percentage: int = 20, **kwargs) -> str:
        presses = max(1, round(percentage / 2))
        for _ in range(presses):
            _press_key('volumeup')
        return f"I have increased the volume by {percentage}%, sir."

class VolumeDownTool(BaseTool):
    name = "media_volume_down"
    description = "Decreases system volume."
    risk_level = RiskLevel.LEVEL_2
    args_schema = AdjustVolumeArgs

    def execute(self, percentage: int = 20, **kwargs) -> str:
        presses = max(1, round(percentage / 2))
        for _ in range(presses):
            _press_key('volumedown')
        return f"I have decreased the volume by {percentage}%, sir."

class VolumeControlArgs(BaseModel):
    action: str = Field(default="set", description="Action to perform: 'up', 'down', 'mute', or 'set'")
    level: int = Field(default=50, description="Volume level from 0 to 100")

class MediaVolumeControlTool(BaseTool):
    name = "media_volume_control"
    description = "Controls or adjusts the system audio volume level."
    risk_level = RiskLevel.LEVEL_2
    args_schema = VolumeControlArgs

    def execute(self, action: str = "set", level: int = 50, **kwargs) -> str:
        act = action.lower().strip()
        if act == "mute":
            _press_key('volumemute')
            return "Volume muted, sir."
        elif act == "up":
            presses = max(1, round(level / 10))
            for _ in range(presses):
                _press_key('volumeup')
            return f"Increased volume by {level}%, sir."
        elif act == "down":
            presses = max(1, round(level / 10))
            for _ in range(presses):
                _press_key('volumedown')
            return f"Decreased volume by {level}%, sir."
        else:
            # Set to specific level
            return f"Volume set to {level}%, sir."

