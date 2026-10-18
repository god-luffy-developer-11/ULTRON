"""Android Companion Device Connector and Bridge."""
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from tools.phone_control import phone

class AndroidDeviceAgent:
    def __init__(self):
        self.device_id = "android-companion"

    def get_connection_status(self) -> Dict[str, Any]:
        """Check ADB connectivity, model, battery, and authorization."""
        res = phone.check_connection()
        battery = phone.get_battery()
        devices = phone.get_devices()
        connected = len(devices) > 0
        serial = devices[0]["serial"] if connected else "none"
        model = devices[0]["model"] if connected else "unknown"
        return {
            "device_id": self.device_id,
            "connected": connected,
            "serial": serial,
            "model": model,
            "battery": battery,
            "summary": res
        }

    def list_granted_permissions(self) -> List[str]:
        """Query granted permissions for shell and system on companion phone."""
        perms = ["android.permission.CALL_PHONE", "android.permission.READ_CONTACTS"]
        try:
            res = phone.run_phone_shell("dumpsys package com.sh.smart.caller | grep -i permission")
            for line in res.splitlines():
                if "granted=true" in line and ":" in line:
                    perm_name = line.split(":")[0].strip()
                    if perm_name not in perms:
                        perms.append(perm_name)
        except Exception:
            pass
        return perms[:15]

    def read_notifications(self, limit: int = 10) -> List[Dict[str, str]]:
        """Read active Android notifications safely via dumpsys notification."""
        notifications = []
        try:
            out = phone.run_phone_shell("dumpsys notification --noredact")
            cur_pkg = ""
            for line in out.splitlines():
                line = line.strip()
                if "pkg=" in line:
                    parts = line.split("pkg=")
                    if len(parts) > 1:
                        cur_pkg = parts[1].split()[0]
                if "android.title=" in line or "android.text=" in line:
                    notifications.append({
                        "package": cur_pkg or "system",
                        "content": line
                    })
                    if len(notifications) >= limit:
                        break
        except Exception as e:
            notifications.append({"error": str(e)})
        return notifications

    def open_app(self, app_name: str) -> str:
        return phone.open_phone_app(app_name)

    def capture_screen(self, pull_to_pc: bool = False) -> Dict[str, Any]:
        phone.wake_screen()
        dev_path = "/sdcard/ultron_companion_screen.png"
        phone.run_phone_shell(f"screencap -p {dev_path}")
        local_path = None
        if pull_to_pc:
            local_path = str(Path(r"c:\Users\surya\Downloads\ULTRON\data\phone_screen.png").resolve())
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["adb", "pull", dev_path, local_path], capture_output=True, timeout=10)
        return {
            "captured": True,
            "device_path": dev_path,
            "local_path": local_path
        }

android_agent = AndroidDeviceAgent()
