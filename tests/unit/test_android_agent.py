"""Unit tests for Android companion device agent."""
import pytest
from services.devices.android_agent import android_agent

def test_android_connection_status():
    status = android_agent.get_connection_status()
    assert "device_id" in status
    assert status["device_id"] == "android-companion"
    assert "connected" in status
    assert "battery" in status

def test_android_list_granted_permissions():
    perms = android_agent.list_granted_permissions()
    assert isinstance(perms, list)
    assert len(perms) > 0
    assert "android.permission.CALL_PHONE" in perms

def test_android_read_notifications():
    notifs = android_agent.read_notifications(limit=5)
    assert isinstance(notifs, list)
