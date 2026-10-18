"""Persistent Emergency Stop Controller for ULTRON."""
import json
import threading
import time
from pathlib import Path
from typing import Dict, Any

class EmergencyStopController:
    """Thread-safe, local & persistent emergency stop controller."""

    def __init__(self, state_file: Path = Path("data/emergency_stop.json")):
        self.state_file = state_file
        self._lock = threading.RLock()
        self._stopped = False
        self._reason = ""
        self._stopped_at: float = 0.0
        self._stopped_by = ""
        self._load()

    def _load(self):
        with self._lock:
            if self.state_file.exists():
                try:
                    with open(self.state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._stopped = data.get("stopped", False)
                        self._reason = data.get("reason", "")
                        self._stopped_at = data.get("stopped_at", 0.0)
                        self._stopped_by = data.get("stopped_by", "")
                except Exception:
                    self._stopped = False

    def _save(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "stopped": self._stopped,
                    "reason": self._reason,
                    "stopped_at": self._stopped_at,
                    "stopped_by": self._stopped_by
                }, f, indent=2)
        except Exception as e:
            print(f"[EmergencyStop] Error saving state: {e}")

    def is_active(self) -> bool:
        """Returns True if emergency stop is currently active."""
        with self._lock:
            return self._stopped

    def trigger(self, reason: str = "User initiated emergency stop", user: str = "Luffy") -> Dict[str, Any]:
        """Trigger emergency stop immediately."""
        with self._lock:
            self._stopped = True
            self._reason = reason
            self._stopped_at = time.time()
            self._stopped_by = user
            self._save()
            print(f"[EmergencyStop] TRIGGERED by {user}: {reason}")
            return self.get_state()

    def resume(self, user: str = "Luffy") -> Dict[str, Any]:
        """Deliberately resume from emergency stop."""
        with self._lock:
            self._stopped = False
            self._reason = ""
            self._stopped_at = 0.0
            self._stopped_by = ""
            self._save()
            print(f"[EmergencyStop] RESUMED by {user}")
            return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._stopped,
                "reason": self._reason,
                "stopped_at": self._stopped_at,
                "stopped_by": self._stopped_by
            }

emergency_stop = EmergencyStopController()
