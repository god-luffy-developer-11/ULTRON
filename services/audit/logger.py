"""SQLite-backed append-only audit logger with secret redaction."""
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

REDACT_KEYS = {"api_key", "password", "token", "secret", "authorization", "auth", "key"}

def redact_dict(data: Any) -> Any:
    """Recursively redact sensitive keys from dictionaries."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if any(rk in k.lower() for rk in REDACT_KEYS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_dict(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_dict(i) for i in data]
    return data

class AuditLogger:
    def __init__(self, db_path: Path = Path("data/ultron_audit.db")):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        request_id TEXT NOT NULL,
                        job_id TEXT,
                        device_id TEXT NOT NULL,
                        tool_id TEXT NOT NULL,
                        policy_version TEXT NOT NULL,
                        risk TEXT NOT NULL,
                        decision TEXT NOT NULL,
                        approval_ref TEXT,
                        outcome TEXT NOT NULL,
                        duration_ms INTEGER,
                        error_code TEXT,
                        details_json TEXT
                    )
                """)
                conn.commit()

    def log_event(
        self,
        request_id: str,
        device_id: str,
        tool_id: str,
        risk: str,
        decision: str,
        outcome: str,
        duration_ms: int = 0,
        policy_version: str = "1.0",
        job_id: Optional[str] = None,
        approval_ref: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """Write an append-only audit event."""
        safe_details = redact_dict(details or {})
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_events (
                        timestamp, request_id, job_id, device_id, tool_id,
                        policy_version, risk, decision, approval_ref, outcome,
                        duration_ms, error_code, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ts, request_id, job_id, device_id, tool_id,
                    policy_version, risk, decision, approval_ref, outcome,
                    duration_ms, error_code, json.dumps(safe_details)
                ))
                conn.commit()
                return cursor.lastrowid

    def query_events(self, limit: int = 50, tool_id: Optional[str] = None, decision: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query audit log events."""
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        if tool_id:
            query += " AND tool_id = ?"
            params.append(tool_id)
        if decision:
            query += " AND decision = ?"
            params.append(decision)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    if item.get("details_json"):
                        try:
                            item["details"] = json.loads(item["details_json"])
                        except Exception:
                            item["details"] = {}
                    results.append(item)
                return results

audit_logger = AuditLogger()
