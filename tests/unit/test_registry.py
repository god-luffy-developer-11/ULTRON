"""Unit tests for ULTRON Tool Registry and Schema Validation."""
import pytest
from pydantic import ValidationError
from services.registry.registry import tool_registry, RegisteredTool
from services.policy.risk import RiskTier
import services.registry.schemas as schemas

def test_registry_lists_default_tools():
    tools = tool_registry.list_tools()
    assert len(tools) >= 10
    tool_ids = [t["tool_id"] for t in tools]
    assert "system.get_status" in tool_ids
    assert "apps.open" in tool_ids
    assert "files.list" in tool_ids
    assert "browser.search" in tool_ids

def test_duplicate_registration_rejected():
    with pytest.raises(ValueError) as exc:
        tool_registry.register_tool(RegisteredTool(
            tool_id="system.get_status",
            version="1.0",
            description="Duplicate test",
            risk=RiskTier.R0,
            required_scopes=["system:read"],
            allowed_devices=["windows-primary"],
            input_schema=schemas.SystemGetStatusInput,
            output_schema=schemas.SystemGetStatusOutput
        ))
    assert "Duplicate tool ID" in str(exc.value)

def test_schema_validation():
    # Valid input
    validated = tool_registry.validate_input("apps.open", {"app_name": "notepad"})
    assert validated.app_name == "notepad"

    # Missing required argument
    with pytest.raises(ValidationError):
        tool_registry.validate_input("apps.open", {})
