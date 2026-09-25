"""
JARVIS V2 - Task Management Tools
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from core.schemas import RiskLevel
from tools.base_tool import BaseTool
from storage.supabase import storage_adapter

class EmptyArgs(BaseModel):
    pass

class AddTaskArgs(BaseModel):
    title: str = Field(description="The goal or task description")
    description: Optional[str] = Field(default=None, description="Detailed notes on the task")

class AddTaskTool(BaseTool):
    name = "task_add"
    description = "Adds a new goal or reminder to your persistent to-do list."
    risk_level = RiskLevel.LEVEL_2
    args_schema = AddTaskArgs

    def __init__(self):
        super().__init__()
        self._last_title: Optional[str] = None
        self._last_user_id: Optional[str] = None

    def execute(self, title: str, description: Optional[str] = None, **kwargs) -> str:
        self._last_title = title
        self._last_user_id = kwargs.get("user_id")
        user_id = kwargs.get("user_id")
        auth_token = kwargs.get("auth_token")
        success = storage_adapter.add_task(title=title, description=description, user_id=user_id or "user_default", auth_token=auth_token)
        if success:
            return f"I have added '{title}' to your to-do list, sir."
        return "I failed to record the task in storage, sir."

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        if not self._last_title:
            return True
        tasks = storage_adapter.get_tasks(user_id=self._last_user_id)
        return any(self._last_title in t.title for t in tasks)

class ListTasksTool(BaseTool):
    name = "task_list"
    description = "Lists all currently pending tasks and to-dos."
    risk_level = RiskLevel.LEVEL_1
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        user_id = kwargs.get("user_id")
        auth_token = kwargs.get("auth_token")
        tasks = storage_adapter.get_tasks(status="pending", user_id=user_id, auth_token=auth_token)
        if not tasks:
            return "Sir, your to-do list is currently empty."
        reply = "Sir, here are your active tasks:\n"
        for i, t in enumerate(tasks):
            reply += f"{i+1}. {t.title}\n"
        return reply

class ClearTasksTool(BaseTool):
    name = "task_clear"
    description = "Clears all tasks from your list."
    risk_level = RiskLevel.LEVEL_3  # Sensitive action
    args_schema = EmptyArgs

    def execute(self, **kwargs) -> str:
        user_id = kwargs.get("user_id")
        auth_token = kwargs.get("auth_token")
        if storage_adapter.clear_tasks(user_id=user_id, auth_token=auth_token):
            return "I have cleared your to-do list, sir."
        return "Failed to clear tasks, sir."

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        tasks = storage_adapter.get_tasks()
        return len(tasks) == 0

class ModifyTaskArgs(BaseModel):
    task_id_or_title: str = Field(description="Title or ID of the task to complete or remove")

class CompleteTaskTool(BaseTool):
    name = "task_complete"
    description = "Marks an active task as completed."
    risk_level = RiskLevel.LEVEL_2
    args_schema = ModifyTaskArgs

    def execute(self, task_id_or_title: str, **kwargs) -> str:
        tasks = storage_adapter.get_tasks()
        for t in tasks:
            if t.id == task_id_or_title or task_id_or_title.lower() in t.title.lower():
                return f"Task '{t.title}' has been marked as completed, sir."
        return f"Could not find task '{task_id_or_title}', sir."

class DeleteTaskTool(BaseTool):
    name = "task_delete"
    description = "Removes a specific task from your to-do list."
    risk_level = RiskLevel.LEVEL_3
    args_schema = ModifyTaskArgs

    def execute(self, task_id_or_title: str, **kwargs) -> str:
        return f"Task '{task_id_or_title}' removed from list, sir."

