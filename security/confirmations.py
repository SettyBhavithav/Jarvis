"""
JARVIS V2 - Session-Bound Explicit User Confirmation Engine
Binds confirmation requests to specific user, session, channel, and action identifiers.
"""
import uuid
import time
from typing import Optional, Dict, Any, Callable, Tuple
from core.state import runtime_state

class ConfirmationManager:
    def __init__(self):
        self._pending: Dict[str, Dict[str, Any]] = {}

    def create_confirmation_request(
        self,
        action_name: str,
        summary: str,
        callback: Callable[[], Any],
        user_id: str = "user_default",
        session_id: str = "default_session",
        channel: str = "voice",
        timeout_seconds: float = 30.0
    ) -> str:
        token = str(uuid.uuid4())[:8]
        req = {
            "token": token,
            "action": action_name,
            "summary": summary,
            "callback": callback,
            "user_id": user_id,
            "session_id": session_id,
            "channel": channel,
            "created_at": time.time(),
            "timeout": timeout_seconds
        }
        self._pending[token] = req
        runtime_state.set_pending_confirmation(req)
        return token

    def confirm(
        self,
        token: str,
        user_id: str,
        session_id: str,
        channel: str
    ) -> Tuple[bool, Any]:
        """
        Confirms and executes a pending action.
        Strictly requires and validates all four parameters:
        token, user_id, session_id, and channel.
        Global 'latest pending action' confirmation is strictly forbidden.
        """
        if not token:
            return False, "Security Violation: Confirmation token is required. Global confirmation is forbidden."

        req = self._pending.get(token)
        if not req:
            return False, "Invalid or expired confirmation token, sir."

        # Validate caller identity across all bound parameters
        if req.get("user_id") != user_id:
            return False, f"Security Violation: Confirmation denied due to user identity mismatch."

        if req.get("session_id") != session_id:
            return False, f"Security Violation: Confirmation denied due to session mismatch."

        if req.get("channel") != channel:
            return False, f"Security Violation: Confirmation denied due to channel mismatch."

        # Check expiry
        if time.time() - req["created_at"] > req["timeout"]:
            self._pending.pop(token, None)
            runtime_state.clear_pending_confirmation()
            return False, "Confirmation request timed out for your safety, sir."

        # Pop from pending after all 4 validations succeed
        self._pending.pop(token, None)
        runtime_state.clear_pending_confirmation()

        # Execute verified callback
        try:
            result = req["callback"]()
            return True, result
        except Exception as e:
            return False, f"Action execution failed: {e}"

    def get_pending_token_for_session(self, user_id: str, session_id: str, channel: str) -> Optional[str]:
        """Returns the pending token strictly matching user_id, session_id, and channel."""
        for token, req in reversed(list(self._pending.items())):
            if req.get("user_id") == user_id and req.get("session_id") == session_id and req.get("channel") == channel:
                return token
        return None

    def cancel(
        self,
        token: Optional[str] = None,
        user_id: str = "user_default",
        session_id: str = "default_session",
        channel: str = "voice"
    ) -> str:
        """Cancels a pending action scoped strictly to the caller's session."""
        if token:
            req = self._pending.get(token)
            if req and req.get("user_id") == user_id and req.get("session_id") == session_id and req.get("channel") == channel:
                self._pending.pop(token, None)
                runtime_state.clear_pending_confirmation()
                return "Action cancelled, sir."
            return "No matching confirmation found to cancel."

        # Scoped cancel: cancel pending actions belonging strictly to this user, session & channel
        to_cancel = [
            t for t, r in self._pending.items()
            if r.get("user_id") == user_id and r.get("session_id") == session_id and r.get("channel") == channel
        ]
        for t in to_cancel:
            self._pending.pop(t, None)
        runtime_state.clear_pending_confirmation()
        return "Action cancelled, sir."

confirmation_manager = ConfirmationManager()
