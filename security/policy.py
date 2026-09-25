"""
JARVIS V2 - Security & Policy Engine
Risk classification (Levels 0-4) and authorization gatekeeper.
"""
from typing import Dict, Any, Tuple
from core.schemas import RiskLevel
from core.config import config
from core.exceptions import SecurityPolicyError

class PolicyEngine:
    def __init__(self):
        self.require_level_3_confirmation = config.REQUIRE_CONFIRMATION_FOR_LEVEL_3
        self.require_level_4_confirmation = config.REQUIRE_CONFIRMATION_FOR_LEVEL_4

    def evaluate_tool_request(self, tool_name: str, risk_level: RiskLevel, user_id: str, channel: str) -> Tuple[bool, bool, str]:
        """
        Evaluates whether an action is allowed and if confirmation is needed.
        Returns: (is_allowed, requires_confirmation, message)
        """
        # Critical actions (Shutdown, Lock, Format, Wipe)
        if risk_level == RiskLevel.LEVEL_4:
            if self.require_level_4_confirmation:
                return True, True, f"Critical system action '{tool_name}' requires your explicit verbal or digital confirmation."
            return True, False, "Permitted"

        # Sensitive external actions (Send Email, WhatsApp Transfer, Delete Tasks)
        if risk_level == RiskLevel.LEVEL_3:
            if self.require_level_3_confirmation:
                return True, True, f"Sensitive action '{tool_name}' requires confirmation before proceeding."
            return True, False, "Permitted"

        # Low-risk and read-only actions (Open app, search web, system stats)
        return True, False, "Permitted"

    def evaluate_action(self, tool_name: str, arguments: Dict[str, Any] = None, user_id: str = "default", channel: str = "voice") -> Any:
        """Helper to evaluate action risk and confirmation requirement by tool name."""
        from tools.registry import tool_registry
        tool = tool_registry.get_tool(tool_name)
        risk = tool.risk_level if tool else RiskLevel.LEVEL_1
        # Overwrite level for dangerous commands if not explicitly registered with level 4
        if "shutdown" in tool_name or "lock" in tool_name:
            risk = RiskLevel.LEVEL_4
        elif "send" in tool_name or "email" in tool_name or "whatsapp" in tool_name:
            risk = RiskLevel.LEVEL_3

        allowed, req_confirm, msg = self.evaluate_tool_request(tool_name, risk, user_id, channel)
        
        class ActionEvalResult:
            def __init__(self, allowed: bool, req_confirm: bool, risk: RiskLevel, msg: str):
                self.is_allowed = allowed
                self.requires_confirmation = req_confirm
                self.risk_level = risk
                self.message = msg
                
        return ActionEvalResult(allowed, req_confirm, risk, msg)

# Global Policy Singleton
policy_engine = PolicyEngine()
