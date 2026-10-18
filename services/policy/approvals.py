"""Approval tokens bound to exact action and parameters."""
import hashlib
import json
import time
import uuid
from typing import Dict, Any, Optional

class ApprovalManager:
    def __init__(self, default_ttl_seconds: int = 120):
        self.default_ttl = default_ttl_seconds
        self._tokens: Dict[str, Dict[str, Any]] = {}

    def _hash_params(self, params: Dict[str, Any]) -> str:
        serialized = json.dumps(params, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def create_request(self, tool_id: str, device_id: str, params: Dict[str, Any], risk: str) -> Dict[str, Any]:
        """Create a pending approval request."""
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        param_hash = self._hash_params(params)
        record = {
            "approval_id": approval_id,
            "tool_id": tool_id,
            "device_id": device_id,
            "param_hash": param_hash,
            "params": params,
            "risk": risk,
            "status": "pending",
            "created_at": time.time(),
            "expires_at": time.time() + self.default_ttl
        }
        self._tokens[approval_id] = record
        return record

    def grant_approval(self, approval_id: str, approved_by: str = "Luffy") -> Optional[Dict[str, Any]]:
        """Approve a pending request."""
        record = self._tokens.get(approval_id)
        if not record:
            return None
        if time.time() > record["expires_at"]:
            record["status"] = "expired"
            return None
        record["status"] = "approved"
        record["approved_by"] = approved_by
        record["approved_at"] = time.time()
        return record

    def reject_approval(self, approval_id: str, rejected_by: str = "Luffy") -> Optional[Dict[str, Any]]:
        record = self._tokens.get(approval_id)
        if record:
            record["status"] = "rejected"
            record["rejected_by"] = rejected_by
        return record

    def verify_approval(self, approval_id: str, tool_id: str, device_id: str, current_params: Dict[str, Any]) -> bool:
        """Verify that a valid, unexpired approval exists for these exact parameters."""
        record = self._tokens.get(approval_id)
        if not record:
            return False
        if record["status"] != "approved":
            return False
        if time.time() > record["expires_at"]:
            record["status"] = "expired"
            return False
        if record["tool_id"] != tool_id or record["device_id"] != device_id:
            return False
        
        # Verify parameter hash hasn't been altered
        current_hash = self._hash_params(current_params)
        if current_hash != record["param_hash"]:
            print(f"[Approval] Parameter tampering detected for {approval_id}")
            return False

        # One-time use: consume the ticket upon verification
        record["status"] = "consumed"
        return True

approval_manager = ApprovalManager()
