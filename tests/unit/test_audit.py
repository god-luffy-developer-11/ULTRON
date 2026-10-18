"""Unit tests for ULTRON Audit Logging and Secret Redaction."""
import time
from pathlib import Path
from services.audit.logger import AuditLogger, redact_dict

def test_secret_redaction():
    payload = {
        "user": "Luffy",
        "api_key": "secret_abc123",
        "nested": {
            "password": "mypassword",
            "normal_data": "public_value"
        }
    }
    cleaned = redact_dict(payload)
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert cleaned["nested"]["normal_data"] == "public_value"

def test_audit_log_and_query(tmp_path: Path):
    test_db = tmp_path / "test_audit.db"
    logger = AuditLogger(db_path=test_db)

    req_id = f"test_{int(time.time())}"
    logger.log_event(
        request_id=req_id,
        device_id="windows-primary",
        tool_id="system.get_status",
        risk="R0",
        decision="allow",
        outcome="success",
        details={"api_key": "leaked_key_test"}
    )

    events = logger.query_events(limit=5, tool_id="system.get_status")
    assert len(events) >= 1
    found = events[0]
    assert found["request_id"] == req_id
    assert found["tool_id"] == "system.get_status"
    assert found["details"]["api_key"] == "[REDACTED]"
