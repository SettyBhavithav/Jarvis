"""
JARVIS V2 - System Diagnostic & Control Tools
"""
import os
import psutil
from pydantic import BaseModel
from core.schemas import RiskLevel
from tools.base_tool import BaseTool

class EmptyArgs(BaseModel):
    pass

class SystemStatsTool(BaseTool):
    name = "system_get_stats"
    description = "Fetches real-time CPU, RAM, Battery, and Disk usage from the operating system."
    risk_level = RiskLevel.LEVEL_1
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        cpu_usage = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        battery_info = "Desktop PC (Plugged In)"
        if battery:
            plugged = "Plugged In" if battery.power_plugged else "Discharged"
            battery_info = f"{battery.percent}% ({plugged})"
        disk = psutil.disk_usage('/')
        disk_free = disk.free / (1024**3)

        return (
            f"Sir, system diagnostics are as follows:\n"
            f"- CPU Load: {cpu_usage}%\n"
            f"- RAM Usage: {ram.percent}%\n"
            f"- Battery: {battery_info}\n"
            f"- Storage: {disk_free:.1f} GB available."
        )

class LockWorkstationTool(BaseTool):
    name = "system_lock_workstation"
    description = "Locks the Windows desktop session."
    risk_level = RiskLevel.LEVEL_4
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "I have locked the system, sir."

class ShutdownTool(BaseTool):
    name = "system_shutdown"
    description = "Initiates a safe shutdown of the computer."
    risk_level = RiskLevel.LEVEL_4
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        os.system("shutdown /s /t 10")
        return "Initiating system shutdown in 10 seconds, sir."

class MinimizeWindowsTool(BaseTool):
    name = "system_minimize_all"
    description = "Minimizes all windows to reveal the desktop."
    risk_level = RiskLevel.LEVEL_2
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        try:
            import pyautogui
            pyautogui.hotkey('win', 'd')
            return "I have minimized all windows, sir."
        except Exception as e:
            return f"Unable to minimize windows: {e}"
