"""
JARVIS V2 - Tool Registry & Execution Controller
Central catalog for tool execution, timeout enforcement, policy gating, action verification, and audit logging.
"""
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple
import concurrent.futures
from core.schemas import RiskLevel, AuditEntry
from core.exceptions import SecurityPolicyError, ConfirmationDeniedError, ToolExecutionError
from security.policy import policy_engine
from security.confirmations import confirmation_manager
from storage.supabase import storage_adapter
from tools.base_tool import BaseTool

class ToolRegistry:
    NON_IDEMPOTENT_TOOLS = {
        "communication_gmail_send",
        "task_add",
        "productivity_calendar_create",
        "communication_whatsapp_send"
    }

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self._recent_actions: Dict[str, Tuple[float, Any]] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions compatible with OpenAI tool calling and MCP."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.args_schema.model_json_schema()
                }
            })
        return schemas

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str = "user_default",
        channel: str = "voice",
        session_id: str = "default_session",
        auth_token: Optional[str] = None
    ) -> Any:
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")

        # Idempotency Guard
        fingerprint = None
        if tool_name in self.NON_IDEMPOTENT_TOOLS:
            key = f"{user_id}:{tool_name}:{json.dumps(arguments, sort_keys=True)}"
            fingerprint = hashlib.sha256(key.encode()).hexdigest()
            now = time.time()
            if fingerprint in self._recent_actions:
                prev_time, prev_res = self._recent_actions[fingerprint]
                if now - prev_time < 45.0:
                    print(f"🛑 [Idempotency Guard: Duplicate action '{tool_name}' detected within {int(now - prev_time)}s. Preventing duplicate.]")
                    return f"[Duplicate Action Suppressed] Previously completed: {prev_res}"

        # 1. Evaluate Security & Policy Engine
        is_allowed, requires_confirm, policy_msg = policy_engine.evaluate_tool_request(
            tool_name=tool.name,
            risk_level=tool.risk_level,
            user_id=user_id,
            channel=channel
        )

        if not is_allowed:
            storage_adapter.log_audit(AuditEntry(
                user_id=user_id,
                channel=channel,
                action=f"execute_{tool_name}",
                tool_name=tool_name,
                arguments_summary=str(arguments),
                risk_level=tool.risk_level.value,
                confirmed_by_user=False,
                status="denied",
                result_summary="Denied by Policy Engine"
            ), auth_token=auth_token)
            raise SecurityPolicyError(policy_msg)

        # 2. Gatekeeper Confirmation for Sensitive Operations
        if requires_confirm:
            token = confirmation_manager.create_confirmation_request(
                action_name=tool.name,
                summary=f"Execute {tool.name} with arguments: {arguments}",
                callback=lambda: self._execute_with_timeout(tool, arguments, user_id, channel, confirmed=True, auth_token=auth_token),
                user_id=user_id,
                session_id=session_id,
                channel=channel
            )
            return f"Sir, {policy_msg} (Say 'yes' or 'confirm' with token {token} to proceed with {tool.name})"

        # 3. Direct Execution for Level 0-2 Actions
        return self._execute_with_timeout(tool, arguments, user_id, channel, confirmed=False, auth_token=auth_token)

    def _execute_with_timeout(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any],
        user_id: str,
        channel: str,
        confirmed: bool,
        auth_token: Optional[str] = None
    ) -> Any:
        validated_args = tool.args_schema(**arguments)

        def _target():
            call_kwargs = validated_args.model_dump()
            # Pass execution context if tool supports them
            call_kwargs["user_id"] = user_id
            call_kwargs["channel"] = channel
            if auth_token:
                call_kwargs["auth_token"] = auth_token
            try:
                return tool.execute(**call_kwargs)
            except TypeError:
                # If tool does not accept extra context kwargs, fall back to pure validated args
                return tool.execute(**validated_args.model_dump())

        last_error = None
        for attempt in range(tool.max_retries + 1):
            try:
                # Real strict timeout enforcement using ThreadPoolExecutor
                future = self._executor.submit(_target)
                result = future.result(timeout=tool.timeout_seconds)
                verified = tool.verify(result)

                # Persist Audit Log
                storage_adapter.log_audit(AuditEntry(
                    user_id=user_id,
                    channel=channel,
                    action=f"execute_{tool.name}",
                    tool_name=tool.name,
                    arguments_summary=str(arguments),
                    risk_level=tool.risk_level.value,
                    confirmed_by_user=confirmed,
                    status="success" if verified else "failed",
                    result_summary=str(result)[:200]
                ), auth_token=auth_token)

                if verified:
                    if tool.name in self.NON_IDEMPOTENT_TOOLS:
                        key = f"{user_id}:{tool.name}:{json.dumps(arguments, sort_keys=True)}"
                        fp = hashlib.sha256(key.encode()).hexdigest()
                        self._recent_actions[fp] = (time.time(), result)
                    return result
                else:
                    last_error = f"Action verification failed for {tool.name}"
            except concurrent.futures.TimeoutError:
                last_error = f"Tool '{tool.name}' timed out after {tool.timeout_seconds} seconds"
            except Exception as e:
                last_error = str(e)

        return f"Tool execution failed for {tool.name}: {last_error}"

# Global Tool Registry Singleton
tool_registry = ToolRegistry()
