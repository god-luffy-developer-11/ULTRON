"""Unit tests for ULTRON Policy Engine and Emergency Stop."""
import pytest
from services.policy.engine import policy_engine
from services.policy.emergency_stop import emergency_stop
from services.policy.approvals import approval_manager
from services.policy.risk import PolicyDecision, RiskTier
from services.registry.registry import tool_registry

@pytest.fixture(autouse=True)
def ensure_emergency_stop_clear():
    emergency_stop.resume()
    yield
    emergency_stop.resume()

def test_r0_read_only_allowed():
    tool = tool_registry.get_tool("system.get_status")
    assert tool is not None
    res = policy_engine.evaluate(tool, "windows-primary", {"detailed": False})
    assert res.decision == PolicyDecision.ALLOW

def test_r2_requires_approval():
    tool = tool_registry.get_tool("files.edit")
    assert tool is not None
    res = policy_engine.evaluate(tool, "windows-primary", {"file_path": "test.txt", "content": "hi", "mode": "write"})
    assert res.decision == PolicyDecision.REQUIRE_APPROVAL
    assert res.approval_id is not None

def test_approval_flow_and_tamper_prevention():
    tool = tool_registry.get_tool("files.edit")
    params = {"file_path": "notes.txt", "content": "important notes", "mode": "write"}
    
    # 1. Request approval
    res1 = policy_engine.evaluate(tool, "windows-primary", params)
    assert res1.decision == PolicyDecision.REQUIRE_APPROVAL
    appr_id = res1.approval_id

    # 2. Grant approval
    grant = approval_manager.grant_approval(appr_id, approved_by="Luffy")
    assert grant["status"] == "approved"

    # 3. Alter parameters (tampering attempt)
    tampered_params = {"file_path": "malicious.bat", "content": "rm -rf", "mode": "write"}
    res2 = policy_engine.evaluate(tool, "windows-primary", tampered_params, approval_id=appr_id)
    assert res2.decision == PolicyDecision.DENY

    # 4. Correct parameters should succeed
    appr2 = approval_manager.create_request("files.edit", "windows-primary", params, "R2")
    approval_manager.grant_approval(appr2["approval_id"], approved_by="Luffy")
    res3 = policy_engine.evaluate(tool, "windows-primary", params, approval_id=appr2["approval_id"])
    assert res3.decision == PolicyDecision.ALLOW

def test_unknown_tool_rejected():
    res = policy_engine.evaluate(None, "windows-primary", {})
    assert res.decision == PolicyDecision.DENY
    assert "not registered" in res.reason

def test_emergency_stop_blocks_dispatch():
    # Trigger emergency stop
    emergency_stop.trigger(reason="Test Stop", user="Luffy")
    assert emergency_stop.is_active() is True

    tool = tool_registry.get_tool("system.get_status")
    res = policy_engine.evaluate(tool, "windows-primary", {})
    assert res.decision == PolicyDecision.EMERGENCY_STOPPED
    assert "Emergency stop is active" in res.reason
