"""Global keyboard hotkey trigger for instant wake."""
import threading
from typing import Callable, Optional

class HotkeyTrigger:
    def __init__(self, hotkey: str = "ctrl+alt+u", on_trigger: Optional[Callable[[], None]] = None):
        self.hotkey = hotkey
        self.on_trigger = on_trigger
        self.active = False

    def start(self):
        try:
            import keyboard
            keyboard.add_hotkey(self.hotkey, self._callback)
            self.active = True
            print(f"[Hotkey] Activated global trigger: {self.hotkey}")
        except Exception as e:
            print(f"[Hotkey] Failed to register {self.hotkey}: {e}")

    def _callback(self):
        print(f"\n[Trigger] Hotkey {self.hotkey} pressed!")
        if self.on_trigger:
            self.on_trigger()

    def stop(self):
        if self.active:
            try:
                import keyboard
                keyboard.remove_hotkey(self.hotkey)
            except Exception:
                pass
            self.active = False
