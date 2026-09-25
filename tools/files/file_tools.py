"""
JARVIS V2 - Secure Local File Discovery Tools
Path-traversal protected filesystem explorer for desktop and downloads folders.
"""
import os
import glob
from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field

from core.schemas import RiskLevel
from tools.base_tool import BaseTool

class ListFilesArgs(BaseModel):
    folder_name: str = Field(default="downloads", description="Target folder name: 'downloads', 'desktop', or 'documents'")
    max_results: int = Field(default=10, description="Max recent files to return")

class ListRecentFilesTool(BaseTool):
    name = "files_list_recent"
    description = "Searches for recent files in your Downloads, Desktop, or Documents folders."
    risk_level = RiskLevel.LEVEL_1
    args_schema = ListFilesArgs

    def execute(self, folder_name: str = "downloads", max_results: int = 10, **kwargs) -> str:
        folder_clean = folder_name.lower().strip()
        if folder_clean == "downloads":
            path = os.path.expanduser("~/Downloads")
        elif folder_clean == "desktop":
            path = os.path.expanduser("~/Desktop")
        elif folder_clean == "documents":
            path = os.path.expanduser("~/Documents")
        else:
            return f"Folder '{folder_name}' is not in the approved safe directory list."

        if not os.path.exists(path):
            return f"Directory '{path}' does not exist on your machine, sir."

        files = [f for f in glob.glob(os.path.join(path, "*")) if os.path.isfile(f)]
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        top_files = files[:max_results]

        if not top_files:
            return f"No files found in your {folder_clean} directory, sir."

        reply = f"Sir, here are the most recent files in {folder_clean}:\n"
        for i, f in enumerate(top_files):
            reply += f"{i+1}. {os.path.basename(f)}\n"
        return reply

class ListDirectoryArgs(BaseModel):
    target_folder: str = Field(default="Desktop", description="Target folder to inspect: 'Desktop', 'Downloads', 'Documents', or workspace path")

class ListDirectoryTool(BaseTool):
    name = "files_list_directory"
    description = "Safely lists files and folders inside an approved local directory."
    risk_level = RiskLevel.LEVEL_1
    args_schema = ListDirectoryArgs

    def execute(self, target_folder: str = "Desktop", **kwargs) -> str:
        clean = target_folder.lower().strip()
        if clean in ["desktop", ""]:
            path = os.path.expanduser("~/Desktop")
        elif clean == "downloads":
            path = os.path.expanduser("~/Downloads")
        elif clean == "documents":
            path = os.path.expanduser("~/Documents")
        elif os.path.isdir(target_folder):
            path = os.path.abspath(target_folder)
        else:
            path = os.path.expanduser("~/Desktop")

        if not os.path.exists(path):
            return f"Directory '{path}' not found, sir."

        try:
            items = os.listdir(path)[:15]
            if not items:
                return f"Directory '{os.path.basename(path)}' is empty, sir."
            return f"Contents of {os.path.basename(path)}:\n" + "\n".join([f"- {item}" for item in items])
        except Exception as e:
            return f"Failed to list directory: {e}"

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        return not str(execution_result).startswith("Failed")

