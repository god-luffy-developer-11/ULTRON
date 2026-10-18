"""Policy evaluation gateway for ULTRON."""
from typing import Dict, Any, Optional, Set
from services.policy.risk import RiskTier, PolicyDecision
from services.policy.scopes import DEFAULT_USER_SCOPES
from services.policy.emergency_stop import emergency_stop
from services.policy.approvals import approval_manager

class PolicyEvaluationResult:
    def __init__(self, decision: PolicyDecision, reason: str, approval_id: Optional[str] = None):
        self.decision = decision
        self.reason = reason
        self.approval_id = approval_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "approval_id": self.approval_id
        }

class PolicyEngine:
    def __init__(self, autonomy_mode: str = "balanced"):
        self.autonomy_mode = autonomy_mode

    def evaluate(
        self,
        tool_def: Optional[Any],
        device_id: str,
        params: Dict[str, Any],
        user_scopes: Set[str] = DEFAULT_USER_SCOPES,
        approval_id: Optional[str] = None
    ) -> PolicyEvaluationResult:
        # 1. Emergency stop check
        if emergency_stop.is_active():
            return PolicyEvaluationResult(
                PolicyDecision.EMERGENCY_STOPPED,
                f"Emergency stop is active: {emergency_stop.get_state().get('reason', 'Halted')}"
            )

        # 2. Unknown tool check
        if tool_def is None:
            return PolicyEvaluationResult(
                PolicyDecision.DENY,
                "Tool is not registered in the trusted tool registry."
            )

        tool_id = tool_def.tool_id
        risk: RiskTier = tool_def.risk

        # 3. Prohibited tier check (R4) - Absolute denial
        if risk == RiskTier.R4:
            return PolicyEvaluationResult(
                PolicyDecision.DENY,
                f"Tool '{tool_id}' is classified as R4 (Prohibited). Approval cannot override."
            )

        # 4. Device check
        if device_id not in tool_def.allowed_devices:
            return PolicyEvaluationResult(
                PolicyDecision.DENY,
                f"Tool '{tool_id}' is not permitted to run on device '{device_id}'."
            )

        # 5. Scope check
        for required_scope in tool_def.required_scopes:
            if required_scope not in user_scopes:
                return PolicyEvaluationResult(
                    PolicyDecision.DENY,
                    f"Missing required scope '{required_scope}' for tool '{tool_id}'."
                )

        # 6. Autonomy Tier Rules:
        # R0: Read-only -> Automatic
        if risk == RiskTier.R0:
            return PolicyEvaluationResult(PolicyDecision.ALLOW, "R0 Read-only action permitted.")

        # R1: Routine -> Automatic
        if risk == RiskTier.R1:
            return PolicyEvaluationResult(PolicyDecision.ALLOW, "R1 Routine action permitted.")

        # R2 & R3: Significant / High Impact -> Requires explicit approval
        if risk in [RiskTier.R2, RiskTier.R3]:
            if approval_id:
                if approval_manager.verify_approval(approval_id, tool_id, device_id, params):
                    return PolicyEvaluationResult(PolicyDecision.ALLOW, f"Valid approval ticket verified for {tool_id}.")
                else:
                    return PolicyEvaluationResult(
                        PolicyDecision.DENY,
                        "Approval ticket is invalid, expired, or parameters were modified."
                    )
            else:
                # Generate a pending approval request
                req = approval_manager.create_request(tool_id, device_id, params, risk.value)
                return PolicyEvaluationResult(
                    PolicyDecision.REQUIRE_APPROVAL,
                    f"Action requires confirmation (Risk Tier {risk.value}).",
                    approval_id=req["approval_id"]
                )

        return PolicyEvaluationResult(PolicyDecision.DENY, "Unknown policy state.")

policy_engine = PolicyEngine()
