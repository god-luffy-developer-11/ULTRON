"""Risk tiers as specified in ULTRON Specification."""
from enum import Enum

class RiskTier(str, Enum):
    R0 = "R0"  # Read-only (Status metrics, file list, public search)
    R1 = "R1"  # Routine (Allowlisted app launch, saved read-only workflow, speak)
    R2 = "R2"  # Significant (Edit files, package install, screen capture)
    R3 = "R3"  # High impact (Send messages, delete data, security changes)
    R4 = "R4"  # Prohibited (Bypass security controls, credential theft)

class PolicyDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"
    EMERGENCY_STOPPED = "emergency_stopped"
