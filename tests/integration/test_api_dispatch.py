"""Integration tests for FastAPI endpoints, policy enforcement, and audit trail."""
import pytest
from fastapi.testclient import TestClient
from services.api.main import app
from services.policy.emergency_stop import emergency_stop

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_stop_state():
    emergency_stop.resume()
    yield
    emergency_stop.resume()

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["emergency_stop_active"] is False

def test_api_list_tools():
    res = client.get("/tools")
    assert res.status_code == 200
    tools = res.json()
    assert len(tools) >= 10

def test_api_execute_r0_tool():
    res = client.post("/tools/execute", json={
        "tool_id": "system.get_status",
        "device_id": "windows-primary",
        "params": {"detailed": False}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "cpu_percent" in data["result"]

def test_api_execute_r2_requires_approval_and_grant():
    # 1. Dispatch R2 without approval
    res = client.post("/tools/execute", json={
        "tool_id": "files.edit",
        "device_id": "windows-primary",
        "params": {
            "file_path": r"c:\Users\surya\Downloads\ULTRON\data\test_edit.txt",
            "content": "Hello Luffy",
            "mode": "write"
        }
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "awaiting_approval"
    approval_id = data["approval_id"]

    # 2. Grant approval
    res_grant = client.post(f"/approvals/{approval_id}/grant")
    assert res_grant.status_code == 200
    assert res_grant.json()["status"] == "approved"

    # 3. Re-dispatch with approval_id
    res_exec = client.post("/tools/execute", json={
        "tool_id": "files.edit",
        "device_id": "windows-primary",
        "params": {
            "file_path": r"c:\Users\surya\Downloads\ULTRON\data\test_edit.txt",
            "content": "Hello Luffy",
            "mode": "write"
        },
        "approval_id": approval_id
    })
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "success"

def test_api_emergency_stop_lifecycle():
    # 1. Trigger Stop
    res_stop = client.post("/emergency-stop", json={"reason": "Safety Test", "user": "Luffy"})
    assert res_stop.status_code == 200
    assert res_stop.json()["state"]["active"] is True

    # 2. Dispatch during stop must be rejected with 403
    res_exec = client.post("/tools/execute", json={
        "tool_id": "system.get_status",
        "device_id": "windows-primary",
        "params": {}
    })
    assert res_exec.status_code == 403
    assert "Emergency stop is active" in res_exec.json()["detail"]

    # 3. Resume
    res_resume = client.post("/emergency-stop/resume", json={"user": "Luffy"})
    assert res_resume.status_code == 200
    assert res_resume.json()["state"]["active"] is False

    # 4. Dispatch now succeeds
    res_after = client.post("/tools/execute", json={
        "tool_id": "system.get_status",
        "device_id": "windows-primary",
        "params": {}
    })
    assert res_after.status_code == 200

def test_api_audit_log_query():
    res = client.get("/audit?limit=10")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    assert len(events) >= 1
