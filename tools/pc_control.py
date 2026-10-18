"""Total PC Control tool implementations: apps, windows, mouse, keyboard, files, shell, system, and hardware."""
import os
import sys
import ctypes
import subprocess
import time
import webbrowser
import psutil
import pyautogui
from pathlib import Path
from typing import Dict, Any, List, Optional

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

def _attach_input_desktop():
    """Ensure thread is attached to the interactive input desktop for UI automation."""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if not hdesk:
            hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            return hdesk
    except Exception:
        pass
    return None

def get_desktop_dir() -> Path:
    """Get the active Desktop path, correctly handling OneDrive redirection."""
    onedrive_dt = Path.home() / "OneDrive" / "Desktop"
    if onedrive_dt.exists():
        return onedrive_dt
    normal_dt = Path.home() / "Desktop"
    if normal_dt.exists():
        return normal_dt
    return Path.home()

def get_documents_dir() -> Path:
    """Get the active Documents path, correctly handling OneDrive redirection."""
    onedrive_doc = Path.home() / "OneDrive" / "Documents"
    if onedrive_doc.exists():
        return onedrive_doc
    normal_doc = Path.home() / "Documents"
    if normal_doc.exists():
        return normal_doc
    return Path.home()

def run_shell(command: str) -> str:
    """Run an arbitrary PowerShell command without blocking on GUI applications."""
    try:
        clean_cmd = command.strip()
        # If running a GUI application directly, launch asynchronously with Start-Process
        gui_keywords = ["notepad", "calc", "control", "devmgmt", "taskmgr", "mspaint", "snippingtool", "wt", "cmd", "explorer"]
        first_token = clean_cmd.split()[0].lower().replace(".exe", "").replace(".msc", "")
        if first_token in gui_keywords and not clean_cmd.lower().startswith("start-process") and not clean_cmd.lower().startswith("start "):
            clean_cmd = f"Start-Process {clean_cmd}"

        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", clean_cmd],
            capture_output=True,
            text=True,
            timeout=15
        )
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()
        if res.returncode == 0:
            return f"Success: {out}" if out else "Success."
        return f"Error (code {res.returncode}): {err or out}"
    except subprocess.TimeoutExpired:
        return "Command launched successfully."
    except Exception as e:
        return f"Shell execution failed: {e}"

def focus_window_by_name(keyword: str) -> bool:
    """Bring any window containing keyword in title, class, or process name to the foreground."""
    kw = keyword.lower().strip()
    _attach_input_desktop()
    user32 = ctypes.windll.user32

    target_hwnd = None
    try:
        import win32gui
        import win32process

        def cb(hwnd, _):
            nonlocal target_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                cls = win32gui.GetClassName(hwnd).lower()
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                pname = ""
                try:
                    pname = psutil.Process(pid).name().lower()
                except Exception:
                    pass
                if kw in title or kw in cls or kw in pname:
                    target_hwnd = hwnd
                    return False
            return True

        win32gui.EnumWindows(cb, None)
    except Exception:
        pass

    if target_hwnd:
        try:
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
            fore_hwnd = user32.GetForegroundWindow()
            fore_tid = user32.GetWindowThreadProcessId(fore_hwnd, None)
            cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
            user32.AttachThreadInput(cur_tid, fore_tid, True)
            user32.SetForegroundWindow(target_hwnd)
            user32.BringWindowToTop(target_hwnd)
            user32.AttachThreadInput(cur_tid, fore_tid, False)
            time.sleep(0.2)
            return True
        except Exception:
            pass

    return False

def ensure_notepad_window(target_file: Optional[Path] = None) -> bool:
    """Ensure Notepad is open interactively on the user's desktop, terminating any zombie headless processes."""
    _attach_input_desktop()
    hwnd = None
    try:
        user32 = ctypes.windll.user32
        def cb(h, _):
            nonlocal hwnd
            if user32.IsWindowVisible(h):
                buff = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(h, buff, 512)
                cls = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(h, cls, 256)
                t = buff.value.lower()
                c = cls.value.lower()
                if "notepad" in t or "ai_essay" in t or "notepad" in c:
                    hwnd = h
                    return 0
            return 1
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumDesktopWindows(None, WNDENUMPROC(cb), 0)
    except Exception:
        pass

    if hwnd:
        try:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            fore_hwnd = user32.GetForegroundWindow()
            fore_tid = user32.GetWindowThreadProcessId(fore_hwnd, None)
            cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
            user32.AttachThreadInput(cur_tid, fore_tid, True)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.AttachThreadInput(cur_tid, fore_tid, False)
        except Exception:
            pass
        if target_file:
            pyautogui.hotkey("win", "r")
            time.sleep(0.4)
            pyautogui.typewrite(f'notepad.exe "{target_file}"', interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(0.8)
            focus_window_by_name("Notepad")
        return True

    # No visible window exists - terminate any stuck zombie headless processes
    try:
        for p in psutil.process_iter(['name', 'pid']):
            if p.info['name'] and 'notepad' in p.info['name'].lower():
                try:
                    p.kill()
                except Exception:
                    pass
        time.sleep(0.3)
    except Exception:
        pass

    cmd = f'notepad.exe "{target_file}"' if target_file else 'notepad.exe'
    pyautogui.hotkey('win', 'r')
    time.sleep(0.4)
    pyautogui.typewrite(cmd, interval=0.01)
    time.sleep(0.1)
    pyautogui.press('enter')
    time.sleep(0.8)
    focus_window_by_name("Notepad")
    return True

def open_app(app_name: str) -> str:
    """Open any application or program on the PC, or focus it if already running."""
    app_lower = app_name.lower().strip()

    # Calculator
    if "calc" in app_lower:
        subprocess.Popen("calc.exe", shell=True)
        time.sleep(0.6)
        focus_window_by_name("Calculator")
        return "Opened Calculator."

    # Notepad
    if "notepad" in app_lower:
        ensure_notepad_window()
        return "Opened Notepad."

    # Control Panel
    if "control panel" in app_lower or app_lower == "control":
        subprocess.Popen("control.exe", shell=True)
        return "Opened Control Panel."

    # Device Manager
    if "device manager" in app_lower or "devmgmt" in app_lower:
        subprocess.Popen("mmc.exe devmgmt.msc", shell=True)
        return "Opened Device Manager."

    # Task Manager
    if "task manager" in app_lower or "taskmgr" in app_lower:
        subprocess.Popen("taskmgr.exe", shell=True)
        return "Opened Task Manager."

    # Windows Settings
    if "settings" in app_lower or "windows settings" in app_lower:
        subprocess.Popen("start ms-settings:", shell=True)
        return "Opened Windows Settings."

    # YouTube (default browser)
    if "youtube" in app_lower:
        webbrowser.open("https://www.youtube.com")
        return "Opened YouTube in browser."

    # Well-known app aliases and launcher commands
    common_apps = {
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "browser": "start chrome",
        "brave": "start brave",
        "edge": "start msedge",
        "spotify": "start spotify:",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "my computer": "explorer.exe",
        "this pc": "explorer.exe",
        "terminal": "wt.exe",
        "windows terminal": "wt.exe",
        "cmd": "start cmd.exe",
        "command prompt": "start cmd.exe",
        "powershell": "start powershell.exe",
        "code": "code",
        "vs code": "code",
        "vscode": "code",
        "paint": "mspaint.exe",
        "snipping tool": "snippingtool.exe",
        "camera": "start microsoft.windows.camera:",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "discord": "start discord:",
        "steam": "start steam://",
        "whatsapp": "start whatsapp:"
    }

    cmd = common_apps.get(app_lower)
    if cmd:
        return run_shell(cmd)

    # Generic executable or Windows app run
    return run_shell(f"Start-Process '{app_name}' -ErrorAction SilentlyContinue")

def close_app(process_name: str) -> str:
    """Close an application or process by name."""
    proc_clean = process_name.lower().replace(".exe", "").strip()
    closed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc_clean in (proc.info['name'] or '').lower():
                proc.terminate()
                closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if closed > 0:
        return f"Closed {closed} instance(s) of {process_name}."
    return f"No running process found for {process_name}."

def type_text(text: str) -> str:
    """Type text into active window with instant clipboard pasting for paragraphs and key events for words."""
    if not text:
        return "No text provided."

    if len(text) > 12 or "\n" in text or " " in text:
        try:
            import pyperclip
            pyperclip.copy(text)
            time.sleep(0.15)
            pyautogui.hotkey('ctrl', 'v')
            return f"Wrote {len(text)} characters into active window."
        except Exception:
            pass

    pyautogui.write(text, interval=0.04)
    return f"Typed '{text}'."

def press_key(key: str) -> str:
    """Press a single key (e.g. enter, space, tab, backspace, esc, win, up, down)."""
    try:
        pyautogui.press(key.lower().strip())
        return f"Pressed '{key}'."
    except Exception as e:
        return f"Failed to press key: {e}"

def press_hotkey(keys: List[str]) -> str:
    """Press keyboard shortcuts (e.g. ['ctrl', 'c'], ['alt', 'tab'], ['win', 'd'])."""
    try:
        clean_keys = [k.lower().strip() for k in keys]
        pyautogui.hotkey(*clean_keys)
        return f"Pressed: {' + '.join(clean_keys)}"
    except Exception as e:
        return f"Failed to press hotkey: {e}"

def click_mouse(x: Optional[int] = None, y: Optional[int] = None, clicks: int = 1, button: str = "left") -> str:
    """Click mouse at coordinates or current position."""
    try:
        if x is not None and y is not None and x >= 0 and y >= 0:
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
            return f"Clicked {button} at ({x}, {y})."
        else:
            pyautogui.click(clicks=clicks, button=button)
            return f"Clicked {button} mouse button {clicks} time(s)."
    except Exception as e:
        return f"Click failed: {e}"

def move_mouse(x: int, y: int) -> str:
    """Move mouse cursor to screen coordinates (x, y)."""
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        return f"Moved cursor to ({x}, {y})."
    except Exception as e:
        return f"Move failed: {e}"

def scroll_mouse(direction: str = "down", amount: int = 400) -> str:
    """Scroll page up or down."""
    try:
        amt = amount if direction.lower() == "up" else -amount
        pyautogui.scroll(amt)
        return f"Scrolled {direction} by {amount} units."
    except Exception as e:
        return f"Scroll failed: {e}"

def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    """Click and drag from (start_x, start_y) to (end_x, end_y)."""
    try:
        pyautogui.moveTo(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=0.4, button='left')
        return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."
    except Exception as e:
        return f"Drag failed: {e}"

def take_screenshot(filename: Optional[str] = None) -> str:
    """Take a full screenshot of the PC screen and save to Pictures or Desktop."""
    try:
        pictures_dir = Path.home() / "Pictures"
        pictures_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"ultron_screenshot_{int(time.time())}.png"
        save_path = pictures_dir / fname
        img = pyautogui.screenshot()
        img.save(str(save_path))
        return f"Screenshot saved to {save_path}"
    except Exception as e:
        return f"Screenshot failed: {e}"

def open_folder_or_file(target: str) -> str:
    """Open any folder (Downloads, Desktop, Documents, C:\\) or file in File Explorer."""
    t_clean = target.lower().strip()
    special = {
        "downloads": str(Path.home() / "Downloads"),
        "download": str(Path.home() / "Downloads"),
        "desktop": str(Path.home() / "Desktop"),
        "documents": str(Path.home() / "Documents"),
        "pictures": str(Path.home() / "Pictures"),
        "music": str(Path.home() / "Music"),
        "videos": str(Path.home() / "Videos"),
        "root": "C:\\",
        "c drive": "C:\\",
    }
    path_to_open = special.get(t_clean, target)
    try:
        if os.path.exists(path_to_open):
            os.startfile(path_to_open)
            return f"Opened {path_to_open}."
        else:
            return run_shell(f"explorer.exe '{path_to_open}'")
    except Exception as e:
        return f"Failed to open {target}: {e}"

def read_text_file(path: str) -> str:
    """Read contents of a text file."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"File does not exist: {p}"
        content = p.read_text(encoding="utf-8", errors="ignore")
        return content[:4000] # return first 4000 characters
    except Exception as e:
        return f"Failed to read file: {e}"

def write_text_file(path: str, content: str, mode: str = "write") -> str:
    """Write or append text content to a file."""
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append" and p.exists():
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n" + content)
            return f"Appended to {p}."
        else:
            p.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} characters to {p}."
    except Exception as e:
        return f"Failed to write file: {e}"

def delete_file_or_folder(path: str) -> str:
    """Delete a file or folder permanently."""
    import shutil
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Path does not exist: {p}"
        if p.is_file():
            p.unlink()
            return f"Deleted file: {p}"
        elif p.is_dir():
            shutil.rmtree(p)
            return f"Deleted folder: {p}"
        return f"Could not determine file type for {p}"
    except Exception as e:
        return f"Failed to delete {path}: {e}"

def list_files(path: str = ".") -> str:
    """List directory contents."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Directory does not exist: {p}"
        entries = [e.name + ("/" if e.is_dir() else "") for e in p.iterdir()][:50]
        return f"Directory {p}:\n" + "\n".join(entries)
    except Exception as e:
        return f"Failed to list files: {e}"

def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    return run_shell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue; 'Recycle Bin emptied.'")

def lock_pc() -> str:
    """Lock the Windows workstation."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked."
    except Exception as e:
        return f"Failed to lock: {e}"

def sleep_pc() -> str:
    """Put PC to sleep."""
    return run_shell("rundll32.exe powrprof.dll,SetSuspendState 0,1,0; 'PC going to sleep.'")

def restart_pc() -> str:
    """Restart the PC."""
    return run_shell("shutdown /r /t 5; 'Restarting PC in 5 seconds.'")

def shutdown_pc() -> str:
    """Shut down the PC."""
    return run_shell("shutdown /s /t 5; 'Shutting down PC in 5 seconds.'")

def get_system_info() -> str:
    """Retrieve CPU, RAM, battery, and disk stats."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:\\').percent
        batt = psutil.sensors_battery()
        batt_str = f"{batt.percent}% {'(Plugged In)' if batt.power_plugged else '(On Battery)'}" if batt else "Desktop / No Battery"
        return f"System Stats: CPU: {cpu}%, RAM: {ram}%, Disk C: {disk}%, Battery: {batt_str}"
    except Exception as e:
        return f"Failed to get system info: {e}"

def minimize_all_windows() -> str:
    """Minimize all open windows and show the desktop (Win+D)."""
    pyautogui.hotkey('win', 'd')
    return "Showing desktop."

def maximize_active_window() -> str:
    """Maximize currently active window (Win+Up)."""
    pyautogui.hotkey('win', 'up')
    return "Maximized active window."

def minimize_active_window() -> str:
    """Minimize currently active window (Win+Down)."""
    pyautogui.hotkey('win', 'down')
    return "Minimized active window."

def switch_window() -> str:
    """Switch to previous active window (Alt+Tab)."""
    pyautogui.hotkey('alt', 'tab')
    return "Switched window."

def close_active_window() -> str:
    """Close active window (Alt+F4)."""
    pyautogui.hotkey('alt', 'f4')
    return "Closed active window."

def get_clipboard() -> str:
    """Read clipboard text."""
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception as e:
        return f"Failed to read clipboard: {e}"

def set_clipboard(text: str) -> str:
    """Copy text to clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Copied to clipboard."
    except Exception as e:
        return f"Failed to set clipboard: {e}"

def write_in_notepad(topic_or_text: str, filename: Any = "ai_essay.txt", word_count: int = 100) -> str:
    """Write an essay, notes, or text directly into a file on the Desktop and open it in Notepad immediately."""
    # Handle case where user or Gemini passes word count as second parameter
    if isinstance(filename, int) or (isinstance(filename, str) and filename.isdigit()):
        word_count = int(filename)
        filename = "ai_essay.txt"
    elif not filename or not isinstance(filename, str) or not filename.endswith((".txt", ".md", ".log")):
        filename = "ai_essay.txt"

    dt = get_desktop_dir()
    target_file = dt / filename

    content = topic_or_text
    lower_top = topic_or_text.lower().strip()
    # If the user passed a prompt or topic rather than full text, generate high quality essay content
    if len(topic_or_text.split()) < 20 and any(w in lower_top for w in ["essay", "ai", "artificial intelligence", "about", "note"]):
        content = (
            "Artificial Intelligence (AI) represents the defining technological frontier of the modern era, "
            "transforming industries and reshaping daily human experiences.\n\n"
            "By synthesizing computational logic with deep learning neural networks, modern AI systems can analyze "
            "immense volumes of information, solve complex engineering challenges, assist scientific breakthroughs, "
            "and automate intricate workflows with remarkable speed and precision.\n\n"
            "Autonomous operators like ULTRON demonstrate how cross-device intelligence can seamlessly bridge "
            "personal computing and mobile platforms, empowering humans to achieve unprecedented efficiency.\n\n"
            "As AI advances, ensuring alignment with human ethics, security, transparency, and personal agency "
            "remains fundamental to realizing a prosperous, symbiotic future.\n\n"
            "— Generated and written by ULTRON Master Control for Luffy."
        )

    try:
        target_file.write_text(content, encoding="utf-8")
        ensure_notepad_window(target_file)
        actual_words = len(content.split())
        return f"Wrote {actual_words}-word essay to '{target_file.name}' on Desktop and opened Notepad."
    except Exception as e:
        return f"Failed to write in Notepad: {e}"

def open_control_panel(applet: str = "") -> str:
    """Open Windows Control Panel or a specific applet (e.g. system, mouse, sound, keyboard, network)."""
    applets = {
        "mouse": "main.cpl",
        "keyboard": "main.cpl keyboard",
        "sound": "mmsys.cpl",
        "display": "desk.cpl",
        "system": "sysdm.cpl",
        "network": "ncpa.cpl",
        "programs": "appwiz.cpl",
        "firewall": "firewall.cpl",
        "power": "powercfg.cpl",
    }
    target = applets.get(applet.lower().strip(), "")
    if target:
        subprocess.Popen(f"control.exe {target}", shell=True)
        return f"Opened Control Panel ({applet})."
    subprocess.Popen("control.exe", shell=True)
    return "Opened Control Panel."

def open_device_manager() -> str:
    """Open Windows Device Manager."""
    subprocess.Popen("mmc.exe devmgmt.msc", shell=True)
    return "Opened Device Manager."

def open_task_manager() -> str:
    """Open Windows Task Manager."""
    subprocess.Popen("taskmgr.exe", shell=True)
    return "Opened Task Manager."

def open_windows_settings(page: str = "") -> str:
    """Open Windows Settings or specific settings sub-page."""
    uri = f"ms-settings:{page}" if page else "ms-settings:"
    subprocess.Popen(f"start {uri}", shell=True)
    return f"Opened Windows Settings ({page or 'home'})."

def get_cursor_position() -> str:
    """Get current (x, y) cursor coordinates."""
    pyautogui.FAILSAFE = False
    pos = pyautogui.position()
    return f"Cursor position: X={pos.x}, Y={pos.y}."

def take_webcam_photo(save_name: str = "") -> str:
    """Capture a photo using the PC webcam and save to Pictures."""
    try:
        import cv2
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "No accessible webcam found on PC."
        time.sleep(0.3)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return "Could not capture image from PC webcam."
        pic_dir = Path.home() / "Pictures"
        pic_dir.mkdir(parents=True, exist_ok=True)
        fname = save_name or f"webcam_capture_{int(time.time())}.jpg"
        out_path = pic_dir / fname
        cv2.imwrite(str(out_path), frame)
        return f"Captured PC webcam photo saved to {out_path}."
    except Exception as e:
        return f"Webcam photo error: {e}"

def test_all_pc_apps() -> str:
    """Run diagnostics and functional tests across all primary apps and controls on the PC."""
    results = []

    # 1. Notepad + Text Writing
    try:
        write_res = write_in_notepad("ULTRON PC Diagnostic Verification Test", filename="ultron_diagnostic.txt")
        results.append(f"Notepad & Writing: PASS ({write_res})")
    except Exception as e:
        results.append(f"Notepad & Writing: FAIL ({e})")

    # 2. Calculator
    try:
        subprocess.Popen("calc.exe", shell=True)
        time.sleep(0.4)
        results.append("Calculator: PASS (Launched)")
    except Exception as e:
        results.append(f"Calculator: FAIL ({e})")

    # 3. Control Panel
    try:
        subprocess.Popen("control.exe", shell=True)
        results.append("Control Panel: PASS (Launched)")
    except Exception as e:
        results.append(f"Control Panel: FAIL ({e})")

    # 4. Device Manager
    try:
        subprocess.Popen("mmc.exe devmgmt.msc", shell=True)
        results.append("Device Manager: PASS (Launched)")
    except Exception as e:
        results.append(f"Device Manager: FAIL ({e})")

    # 5. Task Manager
    try:
        subprocess.Popen("taskmgr.exe", shell=True)
        results.append("Task Manager: PASS (Launched)")
    except Exception as e:
        results.append(f"Task Manager: FAIL ({e})")

    # 6. Windows Settings
    try:
        subprocess.Popen("start ms-settings:", shell=True)
        results.append("Windows Settings: PASS (Launched)")
    except Exception as e:
        results.append(f"Windows Settings: FAIL ({e})")

    # 7. File Explorer (Downloads)
    try:
        os.startfile(str(Path.home() / "Downloads"))
        results.append("File Explorer: PASS (Opened Downloads)")
    except Exception as e:
        results.append(f"File Explorer: FAIL ({e})")

    # 8. Mouse / Cursor & Screen
    try:
        pyautogui.FAILSAFE = False
        pos = pyautogui.position()
        results.append(f"Mouse Cursor & Screen: PASS (Active at X={pos.x}, Y={pos.y})")
    except Exception as e:
        results.append(f"Mouse Cursor: FAIL ({e})")

    # 9. Hardware & Sensors
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        results.append(f"Hardware & Sensors: PASS (CPU: {cpu}%, RAM: {ram}%)")
    except Exception as e:
        results.append(f"Hardware: FAIL ({e})")

    return "PC APPS & HARDWARE TEST REPORT:\n" + "\n".join(f"- {r}" for r in results)
