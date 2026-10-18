"""Media & system settings control: volume, play/pause, brightness, wifi/bluetooth."""
import pyautogui
from tools.pc_control import run_shell

def play_pause() -> str:
    """Toggle media play/pause."""
    pyautogui.press("playpause")
    return "Toggled play/pause."

def volume_up(steps: int = 5) -> str:
    """Increase master volume."""
    for _ in range(steps):
        pyautogui.press("volumeup")
    return f"Increased volume by {steps} steps."

def volume_down(steps: int = 5) -> str:
    """Decrease master volume."""
    for _ in range(steps):
        pyautogui.press("volumedown")
    return f"Decreased volume by {steps} steps."

def volume_mute() -> str:
    """Mute or unmute volume."""
    pyautogui.press("volumemute")
    return "Muted/unmuted volume."

def next_track() -> str:
    """Skip to next media track."""
    pyautogui.press("nexttrack")
    return "Skipped to next track."

def prev_track() -> str:
    """Skip to previous media track."""
    pyautogui.press("prevtrack")
    return "Skipped to previous track."

def set_brightness(level: int) -> str:
    """Set screen brightness (0-100%)."""
    level = max(0, min(100, level))
    cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
    return run_shell(cmd)

def toggle_wifi(enable: bool) -> str:
    """Enable or disable Wi-Fi adapter."""
    state = "Enable" if enable else "Disable"
    cmd = f"{state}-NetAdapter -Name 'Wi-Fi' -Confirm:$false"
    return run_shell(cmd)
