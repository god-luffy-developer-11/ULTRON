"""Memory management for ULTRON."""
import json
import os
import threading
from typing import Any, Dict, Optional
from core.config import Config

class MemoryManager:
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or Config.MEMORY_FILE
        self._lock = threading.Lock()
        self.data: Dict[str, Any] = {
            "owner": "Luffy",
            "preferences": {},
            "routines": {},
            "contacts": {},
            "notes": {}
        }
        self.load()

    def load(self):
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                except Exception:
                    pass

    def save(self):
        with self._lock:
            try:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[Memory] Failed to save memory: {e}")

    def get(self, category: str, key: Optional[str] = None) -> Any:
        with self._lock:
            if category not in self.data:
                return None
            if key is None:
                return self.data.get(category)
            return self.data.get(category, {}).get(key)

    def set(self, category: str, key: str, value: Any) -> str:
        with self._lock:
            if category not in self.data:
                self.data[category] = {}
            if isinstance(self.data[category], dict):
                self.data[category][key] = value
                self.save()
                return f"Stored {key} in {category}."
            return f"Invalid category {category}."

    def delete(self, category: str, key: str) -> str:
        with self._lock:
            if category in self.data and isinstance(self.data[category], dict) and key in self.data[category]:
                del self.data[category][key]
                self.save()
                return f"Removed {key} from {category}."
            return f"Key {key} not found."

    def summary(self) -> str:
        with self._lock:
            return json.dumps(self.data, indent=2)

memory = MemoryManager()
