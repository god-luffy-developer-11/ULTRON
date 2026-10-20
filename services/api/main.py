"""FastAPI backend service for ULTRON."""
import sys
import time
import uuid
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from services.policy.emergency_stop import emergency_stop
from services.policy.engine import policy_engine
from services.policy.approvals import approval_manager
from services.policy.risk import PolicyDecision
from services.registry.registry import tool_registry
from services.audit.logger import audit_logger

app = FastAPI(
    title="ULTRON Orchestration Service",
    description="Backend API with Policy Gateway, Tool Registry, Audit Logging, and Emergency Stop",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request / Response Models
class ToolExecuteRequest(BaseModel):
    tool_id: str
    device_id: str = "windows-primary"
    params: Dict[str, Any] = Field(default_factory=dict)
    approval_id: Optional[str] = None
    request_id: Optional[str] = None

class EmergencyStopRequest(BaseModel):
    reason: str = "User initiated emergency stop"
    user: str = "Luffy"

class EmergencyResumeRequest(BaseModel):
    user: str = "Luffy"

@app.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": "ultron-backend",
        "emergency_stop_active": emergency_stop.is_active(),
        "registered_tools_count": len(tool_registry.list_tools())
    }

@app.get("/tools")
def list_tools():
    return tool_registry.list_tools()

@app.post("/emergency-stop")
def trigger_emergency_stop(req: EmergencyStopRequest):
    state = emergency_stop.trigger(reason=req.reason, user=req.user)
    audit_logger.log_event(
        request_id=f"estop_{int(time.time())}",
        device_id="windows-primary",
        tool_id="system.emergency_stop",
        risk="R3",
        decision="emergency_stop_triggered",
        outcome="stopped",
        details={"reason": req.reason, "user": req.user}
    )
    return {"message": "Emergency stop triggered successfully.", "state": state}

@app.post("/emergency-stop/resume")
def resume_emergency_stop(req: EmergencyResumeRequest):
    state = emergency_stop.resume(user=req.user)
    audit_logger.log_event(
        request_id=f"eresume_{int(time.time())}",
        device_id="windows-primary",
        tool_id="system.emergency_resume",
        risk="R3",
        decision="emergency_stop_resumed",
        outcome="resumed",
        details={"user": req.user}
    )
    return {"message": "Emergency stop cleared.", "state": state}

@app.get("/emergency-stop/status")
def get_emergency_stop_status():
    return emergency_stop.get_state()

@app.post("/tools/execute")
def execute_tool(req: ToolExecuteRequest):
    req_id = req.request_id or f"req_{uuid.uuid4().hex[:10]}"
    start_time = time.time()
    tool_def = tool_registry.get_tool(req.tool_id)

    # 1. Evaluate against policy engine
    eval_res = policy_engine.evaluate(
        tool_def=tool_def,
        device_id=req.device_id,
        params=req.params,
        approval_id=req.approval_id
    )

    risk_str = tool_def.risk.value if tool_def else "R4"

    # 2. Handle Emergency Stop
    if eval_res.decision == PolicyDecision.EMERGENCY_STOPPED:
        audit_logger.log_event(
            request_id=req_id,
            device_id=req.device_id,
            tool_id=req.tool_id,
            risk=risk_str,
            decision="emergency_stopped",
            outcome="blocked",
            error_code="EMERGENCY_STOP_ACTIVE",
            details=req.params
        )
        raise HTTPException(status_code=403, detail=eval_res.reason)

    # 3. Handle Denial
    if eval_res.decision == PolicyDecision.DENY:
        audit_logger.log_event(
            request_id=req_id,
            device_id=req.device_id,
            tool_id=req.tool_id,
            risk=risk_str,
            decision="deny",
            outcome="denied",
            error_code="POLICY_DENIED",
            details=req.params
        )
        raise HTTPException(status_code=403, detail=eval_res.reason)

    # 4. Handle Pending Approval (R2 / R3)
    if eval_res.decision == PolicyDecision.REQUIRE_APPROVAL:
        audit_logger.log_event(
            request_id=req_id,
            device_id=req.device_id,
            tool_id=req.tool_id,
            risk=risk_str,
            decision="require_approval",
            outcome="pending",
            approval_ref=eval_res.approval_id,
            details=req.params
        )
        return {
            "status": "awaiting_approval",
            "approval_id": eval_res.approval_id,
            "tool_id": req.tool_id,
            "risk": risk_str,
            "reason": eval_res.reason,
            "params": req.params
        }

    # 5. Execute Approved Tool
    try:
        # Validate inputs against Pydantic schema
        validated_input = tool_registry.validate_input(req.tool_id, req.params)
        
        if not tool_def.handler:
            raise NotImplementedError(f"Handler for '{req.tool_id}' is not yet configured.")

        result = tool_def.handler(validated_input)
        duration_ms = int((time.time() - start_time) * 1000)

        # Log successful execution
        audit_logger.log_event(
            request_id=req_id,
            device_id=req.device_id,
            tool_id=req.tool_id,
            risk=risk_str,
            decision="allow",
            outcome="success",
            approval_ref=req.approval_id,
            duration_ms=duration_ms,
            details={"params": req.params, "result": result.model_dump() if hasattr(result, "model_dump") else str(result)}
        )

        return {
            "status": "success",
            "request_id": req_id,
            "tool_id": req.tool_id,
            "duration_ms": duration_ms,
            "result": result.model_dump() if hasattr(result, "model_dump") else result
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        audit_logger.log_event(
            request_id=req_id,
            device_id=req.device_id,
            tool_id=req.tool_id,
            risk=risk_str,
            decision="allow",
            outcome="error",
            error_code=type(e).__name__,
            duration_ms=duration_ms,
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approvals/{approval_id}/grant")
def grant_approval_ticket(approval_id: str, user: str = "Luffy"):
    record = approval_manager.grant_approval(approval_id, approved_by=user)
    if not record:
        raise HTTPException(status_code=404, detail="Approval ticket not found or already expired.")
    return {"status": "approved", "ticket": record}

@app.post("/approvals/{approval_id}/reject")
def reject_approval_ticket(approval_id: str, user: str = "Luffy"):
    record = approval_manager.reject_approval(approval_id, rejected_by=user)
    if not record:
        raise HTTPException(status_code=404, detail="Approval ticket not found.")
    return {"status": "rejected", "ticket": record}

@app.get("/audit")
def get_audit_logs(limit: int = 50, tool_id: Optional[str] = None, decision: Optional[str] = None):
    return audit_logger.query_events(limit=limit, tool_id=tool_id, decision=decision)

class CommandRequest(BaseModel):
    command: str
    user: str = "Luffy"

@app.post("/command")
def execute_command(req: CommandRequest):
    if emergency_stop.is_active():
        raise HTTPException(status_code=403, detail="Emergency stop is currently active.")
    from core.brain import brain
    reply = brain.process_command(req.command)
    return {
        "status": "success",
        "command": req.command,
        "reply": reply,
        "timestamp": time.time()
    }

@app.get("/system/status")
def get_system_status():
    import psutil
    from tools.pc_control import get_system_info
    from tools.phone_control import phone

    phone_conn = phone.check_connection()
    phone_online = "connected" in phone_conn.lower() or "device" in phone_conn.lower()

    return {
        "emergency_stop": emergency_stop.is_active(),
        "pc": {
            "cpu_percent": psutil.cpu_percent(),
            "ram_percent": psutil.virtual_memory().percent,
            "info": get_system_info()
        },
        "phone": {
            "connected": phone_online,
            "status_text": phone_conn
        },
        "timestamp": time.time()
    }

