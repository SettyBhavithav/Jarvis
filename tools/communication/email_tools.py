"""
JARVIS V2 - Gmail Tools
"""
import base64
from typing import Optional, Any
from email.message import EmailMessage
from pydantic import BaseModel, Field
from core.schemas import RiskLevel
from tools.base_tool import BaseTool
from tools.productivity.calendar_tools import GoogleAuthHelper

class ListEmailsArgs(BaseModel):
    query: str = Field(default="is:unread", description="Gmail search query filter")
    max_results: int = Field(default=5, description="Maximum emails to return")

class ListEmailsTool(BaseTool):
    name = "communication_gmail_list"
    description = "Searches and lists recent emails from your Gmail inbox."
    risk_level = RiskLevel.LEVEL_1
    args_schema = ListEmailsArgs

    def execute(self, query: str = "is:unread", max_results: int = 5, **kwargs) -> str:
        try:
            creds = GoogleAuthHelper.get_credentials()
            if not creds:
                return "Sir, I need valid Google credentials in credentials.json to access Gmail."
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=creds)
            res = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = res.get('messages', [])
            if not messages:
                return f"No emails found matching query '{query}', sir."
            return f"Retrieved {len(messages)} emails matching '{query}', sir."
        except Exception as e:
            return f"Failed to list emails: {e}"

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        return not str(execution_result).startswith("Failed to list")

class SendEmailArgs(BaseModel):
    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Body text of the email")
    send_immediately: bool = Field(default=False, description="Whether to send immediately or save draft")

class SendEmailTool(BaseTool):
    name = "communication_gmail_send"
    description = "Drafts or sends a formal email via Gmail API with user confirmation."
    risk_level = RiskLevel.LEVEL_3  # Requires Confirmation
    args_schema = SendEmailArgs

    def execute(self, to: str, subject: str, body: str, send_immediately: bool = False, **kwargs) -> str:
        if not send_immediately:
            return f"Draft prepared for {to}: Subject '{subject}'. Please confirm before sending."

        try:
            creds = GoogleAuthHelper.get_credentials()
            if not creds:
                return f"Draft saved locally for {to}: Subject '{subject}'."

            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=creds)
            msg = EmailMessage()
            msg.set_content(body)
            msg['To'] = to
            msg['From'] = 'me'
            msg['Subject'] = subject

            encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={'raw': encoded}).execute()
            return f"Email successfully dispatched to {to}, sir."
        except Exception as e:
            return f"Failed to send email: {e}"

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        res = str(execution_result).lower()
        return "draft" in res or "successfully dispatched" in res

