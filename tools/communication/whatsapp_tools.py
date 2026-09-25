"""
JARVIS V2 - WhatsApp Automation Tools
Automates file discovery and WhatsApp Desktop dispatch using PowerShell clipboard and GUI hooks.
"""
import os
import time
from pydantic import BaseModel, Field
from core.schemas import RiskLevel
from tools.base_tool import BaseTool

class WhatsAppSendFileArgs(BaseModel):
    file_path: str = Field(description="Full path to the file on local disk")
    contact: str = Field(description="Name of the contact as saved in WhatsApp Desktop")

class WhatsAppSendFileTool(BaseTool):
    name = "whatsapp_send_file"
    description = "Dispatches a local file to a contact via WhatsApp Desktop."
    risk_level = RiskLevel.LEVEL_3  # Requires Confirmation
    args_schema = WhatsAppSendFileArgs

    def execute(self, file_path: str, contact: str, **kwargs) -> str:
        if not os.path.exists(file_path):
            return f"Error: File not found at '{file_path}'."

        try:
            import pyautogui
            print(f"⚡ [WhatsApp: Copying {os.path.basename(file_path)} to clipboard...]")
            # Copy file to clipboard via PowerShell
            os.system(f'powershell.exe -command "Set-Clipboard -Path \'{file_path}\'"')

            # Launch WhatsApp
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.write("whatsapp", interval=0.05)
            time.sleep(0.5)
            pyautogui.press('enter')

            print("⏳ [Waiting for WhatsApp Desktop to focus...]")
            time.sleep(4.0)

            # Search contact
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.8)
            pyautogui.write(contact, interval=0.05)
            time.sleep(2.0)
            pyautogui.press('down')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(1.0)

            # Paste and send
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.5)
            pyautogui.press('enter')

            return f"File '{os.path.basename(file_path)}' has been sent to {contact} via WhatsApp, sir."
        except Exception as e:
            return f"WhatsApp automation failed: {e}"
