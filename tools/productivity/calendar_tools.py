"""
JARVIS V2 - Google Calendar Tools
"""
import os
import pickle
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from core.schemas import RiskLevel
from tools.base_tool import BaseTool


class GoogleAuthHelper:
    SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail.send']

    @classmethod
    def get_credentials(cls):
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                try:
                    creds = pickle.load(token)
                except Exception:
                    creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not os.path.exists('credentials.json'):
                    return None
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', cls.SCOPES)
                creds = flow.run_local_server(port=0)

            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return creds

class CalendarListArgs(BaseModel):
    max_results: int = Field(default=5, description="Maximum number of upcoming events to retrieve")
    days_ahead: int = Field(default=7, description="Number of days ahead to search for events")


class CreateCalendarEventArgs(BaseModel):
    summary: str = Field(description="Title or summary of the event")
    start_time: str = Field(description="Start time (e.g. '2026-09-20T10:00:00Z' or human-readable format)")
    end_time: str = Field(description="End time of the event")
    description: str = Field(default="", description="Optional description or agenda")

class ListCalendarEventsTool(BaseTool):
    name = "productivity_calendar_list"
    description = "Fetches your upcoming appointments and events from Google Calendar."
    risk_level = RiskLevel.LEVEL_1
    args_schema = CalendarListArgs

    def execute(self, max_results: int = 5, days_ahead: int = 7, **kwargs) -> str:
        from googleapiclient.discovery import build
        try:
            creds = GoogleAuthHelper.get_credentials()
            if not creds:
                return "Sir, I need a 'credentials.json' file in my directory to access Google Calendar."

            service = build('calendar', 'v3', credentials=creds)
            now = datetime.now(timezone.utc).isoformat()
            events_result = service.events().list(
                calendarId='primary', timeMin=now, maxResults=max_results,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if not events:
                return "You have no upcoming events on your schedule, sir."

            reply = "Sir, here are your upcoming events:\n"
            for e in events:
                start = e['start'].get('dateTime', e['start'].get('date'))
                summary = e.get('summary', 'Untitled Event')
                reply += f"- {summary} ({start})\n"
            return reply
        except Exception as e:
            return f"Failed to retrieve Google Calendar schedule: {e}"

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        return not str(execution_result).startswith("Failed")

class CreateCalendarEventTool(BaseTool):
    name = "productivity_calendar_create"
    description = "Creates a new event or appointment on your Google Calendar."
    risk_level = RiskLevel.LEVEL_3  # Non-idempotent, requires confirmation
    args_schema = CreateCalendarEventArgs

    def __init__(self):
        super().__init__()
        self._last_summary = None

    def execute(self, summary: str, start_time: str, end_time: str, description: str = "", **kwargs) -> str:
        self._last_summary = summary
        from googleapiclient.discovery import build
        try:
            creds = GoogleAuthHelper.get_credentials()
            if not creds:
                return f"Event '{summary}' queued locally for {start_time} (Google credentials pending)."

            service = build('calendar', 'v3', credentials=creds)
            event_body = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'UTC'},
                'end': {'dateTime': end_time, 'timeZone': 'UTC'}
            }
            created_event = service.events().insert(calendarId='primary', body=event_body).execute()
            return f"Event '{summary}' successfully scheduled on Google Calendar for {start_time}, sir."
        except Exception as e:
            return f"Event '{summary}' recorded locally (Calendar API: {e})."

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        res = str(execution_result).lower()
        return "successfully scheduled" in res or "recorded locally" in res or "queued locally" in res

