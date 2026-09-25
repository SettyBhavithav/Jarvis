"""
JARVIS V2 - Cross-Channel Notification Engine
Dispatches priority alerts across Voice, Desktop Windows toast notifications, and Discord webhooks.
"""
import os
import subprocess
from typing import Optional
from voice.tts import tts_engine
from core.config import config

class NotificationManager:
    def notify(self, title: str, message: str, channel: str = "voice") -> bool:
        formatted_alert = f"Alert: {title}. {message}"
        print(f"🔔 [Notification ({channel.upper()})]: {formatted_alert}")

        chan = channel.lower().strip()
        if chan == "voice":
            try:
                tts_engine.speak_chunk(formatted_alert)
            except Exception as e:
                print(f"[Voice Alert Warning]: {e}")

        elif chan == "desktop":
            self._send_desktop_notification(title, message)

        elif chan == "discord":
            self._send_discord_notification(title, message)

        return True

    def _send_desktop_notification(self, title: str, message: str):
        """Sends a native Windows Toast notification via PowerShell."""
        try:
            ps_cmd = (
                f"[void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                f"$notify = New-Object System.Windows.Forms.NotifyIcon; "
                f"$notify.Icon = [System.Drawing.SystemIcons]::Information; "
                f"$notify.Visible = $true; "
                f"$notify.ShowBalloonTip(5000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)"
            )
            subprocess.Popen(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Desktop Toast Warning]: {e}")

    def _send_discord_notification(self, title: str, message: str):
        """Dispatches notification to Discord channel or webhook."""
        webhook_url = getattr(config, "DISCORD_WEBHOOK_URL", None)
        if webhook_url and webhook_url.startswith("http"):
            try:
                import httpx
                payload = {"content": f"**[JARVIS Alert] {title}**\n{message}"}
                httpx.post(webhook_url, json=payload, timeout=4.0)
            except Exception as e:
                print(f"[Discord Notification Warning]: {e}")
        else:
            print(f"[Discord Notification Queued]: {title}: {message}")

# Global Notification Singleton
notification_manager = NotificationManager()

