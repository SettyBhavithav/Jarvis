"""
Unit Tests for JARVIS V2 - Policy & Confirmation Engine
"""
import pytest
from core.schemas import RiskLevel
from security.policy import policy_engine
from security.confirmations import confirmation_manager

def test_policy_read_only_allowed_without_confirmation():
    allowed, req_confirm, msg = policy_engine.evaluate_tool_request(
        tool_name="system_get_stats",
        risk_level=RiskLevel.LEVEL_1,
        user_id="test_user",
        channel="voice"
    )
    assert allowed is True
    assert req_confirm is False

def test_policy_sensitive_action_requires_confirmation():
    allowed, req_confirm, msg = policy_engine.evaluate_tool_request(
        tool_name="email_send_background",
        risk_level=RiskLevel.LEVEL_3,
        user_id="test_user",
        channel="voice"
    )
    assert allowed is True
    assert req_confirm is True
    assert "requires confirmation" in msg

def test_confirmation_lifecycle():
    executed = {"val": False}
    def dummy_action():
        executed["val"] = True
        return "SUCCESS"

    token = confirmation_manager.create_confirmation_request(
        action_name="test_action",
        summary="Testing action",
        callback=dummy_action,
        user_id="user_setty",
        session_id="session_xyz",
        channel="voice"
    )
    assert token is not None

    # 1. Calling confirm without token is rejected
    no_tok_success, no_tok_res = confirmation_manager.confirm(token="", user_id="user_setty", session_id="session_xyz", channel="voice")
    assert no_tok_success is False
    assert "required" in no_tok_res.lower()

    # 2. Mismatched user_id is rejected
    bad_user_success, bad_user_res = confirmation_manager.confirm(token=token, user_id="imposter_user", session_id="session_xyz", channel="voice")
    assert bad_user_success is False
    assert "user identity mismatch" in bad_user_res

    # 3. Mismatched session_id is rejected
    bad_sess_success, bad_sess_res = confirmation_manager.confirm(token=token, user_id="user_setty", session_id="foreign_session", channel="voice")
    assert bad_sess_success is False
    assert "session mismatch" in bad_sess_res

    # 4. Mismatched channel is rejected
    bad_chan_success, bad_chan_res = confirmation_manager.confirm(token=token, user_id="user_setty", session_id="session_xyz", channel="discord")
    assert bad_chan_success is False
    assert "channel mismatch" in bad_chan_res

    # 5. Matching all 4 parameters succeeds and executes callback
    success, result = confirmation_manager.confirm(
        token=token,
        user_id="user_setty",
        session_id="session_xyz",
        channel="voice"
    )
    assert success is True
    assert result == "SUCCESS"
    assert executed["val"] is True
