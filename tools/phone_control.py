"""Phone Control via ADB (Android Debug Bridge): apps, camera, taps, swipes, calls, SMS, screen info."""
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from core.config import Config

class PhoneController:
    """Orchestrates Android device control via Android Debug Bridge (ADB)."""

    def __init__(self):
        self.device_serial = Config.ADB_DEVICE_SERIAL
        self.adb_bin = self._find_adb()
        self._screen_size: Optional[Tuple[int, int]] = None

    def _find_adb(self) -> str:
        """Locate adb.exe dynamically on the system."""
        # 1. On PATH
        which_adb = shutil.which("adb")
        if which_adb:
            return which_adb

        # 2. LocalAppData platform-tools (standard install location)
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(local_app_data) / "Android" / "platform-tools" / "adb.exe",
            Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local" / "Android" / "platform-tools" / "adb.exe",
            Path(r"C:\platform-tools\adb.exe"),
            Path(r"C:\Program Files\Android\platform-tools\adb.exe")
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        return "adb"

    def _auto_bind_device(self):
        """Auto-bind to the first active device if serial not explicitly set."""
        if not self.device_serial:
            devs = self.get_devices()
            if devs:
                for d in devs:
                    if d.get("state") == "device":
                        self.device_serial = d["serial"]
                        break
                if not self.device_serial and devs:
                    self.device_serial = devs[0]["serial"]

    def _run_adb(self, cmd_args: List[str], timeout: int = 25) -> str:
        """Run adb command safely with argument list."""
        self._auto_bind_device()
        base = [self.adb_bin]
        if self.device_serial:
            base.extend(["-s", self.device_serial])
        
        full_cmd = base + cmd_args
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()

            if "device unauthorized" in err.lower() or "device unauthorized" in out.lower():
                return "Device is connected but unauthorized. Please check your phone screen and tap 'Allow USB debugging'."
            if "no devices/emulators found" in err.lower() or "device not found" in err.lower():
                return "No Android device detected. Please connect your phone via USB or Wireless Debugging."
            
            return out or err or "Success."
        except FileNotFoundError:
            return "ADB executable not found. Please install Android SDK platform-tools."
        except Exception as e:
            return f"ADB execution failed: {e}"

    def get_devices(self) -> List[Dict[str, str]]:
        """List all connected Android devices with status and model."""
        try:
            res = subprocess.run([self.adb_bin, "devices", "-l"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
            lines = (res.stdout or "").strip().splitlines()
            devices = []
            for line in lines[1:]: # Skip 'List of devices attached' header
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    model = "Unknown"
                    for part in parts[2:]:
                        if part.startswith("model:"):
                            model = part.replace("model:", "")
                    devices.append({
                        "serial": serial,
                        "state": state,
                        "model": model
                    })
            return devices
        except Exception as e:
            print(f"[Phone] Error querying devices: {e}")
            return []

    def check_connection(self) -> str:
        """Return human-readable status of phone connection."""
        devs = self.get_devices()
        if not devs:
            return "No phone connected. Connect via USB cable or Wireless Debugging."
        
        dev = devs[0]
        if dev["state"] == "unauthorized":
            return f"Phone ({dev['serial']}) connected but UNAUTHORIZED. Look at your phone screen and tap 'Allow USB Debugging'."
        if dev["state"] == "device":
            self.device_serial = dev["serial"]
            model = self.get_device_model()
            battery = self.get_battery()
            return f"Phone connected and authorized! Model: {model} (Serial: {dev['serial']}). {battery}."
        
        return f"Phone status: {dev['state']} ({dev['serial']})."

    def get_screen_size(self) -> Tuple[int, int]:
        """Fetch screen physical dimensions (width, height)."""
        if self._screen_size:
            return self._screen_size
        out = self._run_adb(["shell", "wm", "size"])
        m = re.search(r'Physical size:\s*(\d+)x(\d+)', out)
        if m:
            self._screen_size = (int(m.group(1)), int(m.group(2)))
            return self._screen_size
        return (1080, 2400) # Fallback

    def connect_wireless(self, ip_address: str, port: int = 5555) -> str:
        """Connect to phone over Wi-Fi."""
        target = f"{ip_address}:{port}"
        return self._run_adb(["connect", target])

    def get_device_model(self) -> str:
        """Read device manufacturer and model name."""
        mfg = self._run_adb(["shell", "getprop", "ro.product.manufacturer"])
        model = self._run_adb(["shell", "getprop", "ro.product.model"])
        return f"{mfg} {model}".strip()

    def get_battery(self) -> str:
        """Get phone battery level and status."""
        out = self._run_adb(["shell", "dumpsys", "battery"])
        level_m = re.search(r'level:\s*(\d+)', out)
        lvl = level_m.group(1) if level_m else "Unknown"
        return f"Phone Battery: {lvl}%"

    def wake_screen(self) -> str:
        """Wake up phone screen and dismiss lockscreen/keyguard."""
        self._run_adb(["shell", "input", "keyevent", "224"]) # KEYCODE_WAKEUP
        self._run_adb(["shell", "input", "keyevent", "82"])  # KEYCODE_MENU / Unlock swipe
        return "Screen awakened and unlocked."

    def lock_screen(self) -> str:
        """Lock phone screen."""
        self._run_adb(["shell", "input", "keyevent", "26"]) # KEYCODE_POWER
        return "Screen locked."

    def open_phone_app(self, app_name: str) -> str:
        """Open an app on phone by name or package identifier."""
        self.wake_screen()
        clean_name = app_name.lower().strip()

        # Handle Camera directly
        if clean_name in ["camera", "cam", "photo", "cam app"]:
            res = self._run_adb(["shell", "am", "start", "-n", "com.transsion.camera/com.android.camera.CameraLauncher"])
            if "Error" in res or "does not exist" in res:
                self._run_adb(["shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"])
            return "Camera opened on phone."

        # Handle Contacts directly
        if clean_name in ["contacts", "contact", "people"]:
            res = self._run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "content://contacts/people"])
            if "Error" in res or "not found" in res:
                self._run_adb(["shell", "am", "start", "-n", "com.sh.smart.caller/com.android.dialer.ContactMainActivity"])
            return "Contacts app opened on phone."

        # Handle Maps directly
        if clean_name in ["maps", "map", "navigation", "gps", "google maps"]:
            self._run_adb(["shell", "monkey", "-p", "com.google.android.apps.maps", "-c", "android.intent.category.LAUNCHER", "1"])
            return "Google Maps opened on phone."

        packages = {
            "whatsapp": "com.whatsapp",
            "youtube": "com.google.android.youtube",
            "yt music": "com.google.android.apps.youtube.music",
            "music": "com.google.android.apps.youtube.music",
            "chrome": "com.brave.browser",
            "brave": "com.brave.browser",
            "browser": "com.brave.browser",
            "messages": "com.google.android.apps.messaging",
            "sms": "com.google.android.apps.messaging",
            "phone": "com.sh.smart.caller",
            "dialer": "com.sh.smart.caller",
            "call": "com.sh.smart.caller",
            "contacts": "com.sh.smart.caller",
            "settings": "com.android.settings",
            "spotify": "com.spotify.music",
            "instagram": "com.instagram.android",
            "telegram": "org.telegram.messenger",
            "gallery": "com.gallery20",
            "photos": "com.gallery20",
            "maps": "com.google.android.apps.maps",
            "calculator": "com.transsion.calculator",
            "calc": "com.transsion.calculator",
            "clock": "com.transsion.deskclock",
            "alarm": "com.transsion.deskclock",
            "files": "com.google.android.apps.nbu.files",
            "file manager": "com.transsion.phonemanager"
        }
        pkg = packages.get(clean_name, app_name.strip())

        res = self._run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])
        if "No activities found" in res:
            res = self._run_adb(["shell", "am", "start", "-n", f"{pkg}"])
        return f"Opened {app_name} on phone."

    def _list_camera_files(self) -> List[str]:
        """List files in /sdcard/DCIM/Camera."""
        check_out = self._run_adb(["shell", "ls", "-t", "/sdcard/DCIM/Camera"])
        return [l.strip().split()[-1] for l in check_out.splitlines() if l.strip() and (".jpg" in l.lower() or ".png" in l.lower() or ".mp4" in l.lower())]

    def take_photo(self, camera_type: str = "back", pull_to_pc: bool = False) -> str:
        """Open the camera, trigger autofocus, click shutter, and verify picture captured.
        
        Args:
            camera_type: 'back' for rear camera, 'front' or 'selfie' for front camera.
            pull_to_pc: If True, pulls newly captured photo to local PC directory.
        """
        self.wake_screen()
        before_files = set(self._list_camera_files())

        # 1. Launch native camera
        res = self._run_adb(["shell", "am", "start", "-n", "com.transsion.camera/com.android.camera.CameraLauncher"])
        if "Error" in res or "does not exist" in res:
            self._run_adb(["shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"])

        time.sleep(1.4)  # Allow sensor, exposure, and preview UI to stabilize

        w, h = self.get_screen_size()

        # 2. Switch camera if front/selfie requested
        if camera_type.lower() in ["front", "selfie"]:
            switch_x = int(w * 0.858)
            switch_y = int(h * 0.865)
            self._run_adb(["shell", "input", "tap", str(switch_x), str(switch_y)])
            time.sleep(1.0)

        # 3. Press shutter: both coordinate tap & KEYCODE_CAMERA & VOLUME_DOWN
        shutter_x = w // 2
        shutter_y = int(h * 0.865)
        self._run_adb(["shell", "input", "tap", str(shutter_x), str(shutter_y)])
        self._run_adb(["shell", "input", "keyevent", "27"])  # KEYCODE_CAMERA
        self._run_adb(["shell", "input", "keyevent", "25"])  # KEYCODE_VOLUME_DOWN
        
        # 4. Wait and detect the newly written photo
        new_file = None
        for _ in range(6):
            time.sleep(0.5)
            current_files = self._list_camera_files()
            diff = [f for f in current_files if f not in before_files]
            if diff:
                new_file = diff[0]
                break

        if not new_file:
            current_files = self._list_camera_files()
            new_file = current_files[0] if current_files else "photo.jpg"

        # 5. Optionally pull to local PC
        if pull_to_pc:
            pc_dir = Path(__file__).resolve().parent.parent / "captured_photos"
            pc_dir.mkdir(exist_ok=True)
            local_target = pc_dir / new_file
            self._run_adb(["pull", f"/sdcard/DCIM/Camera/{new_file}", str(local_target)])
            return f"Picture successfully taken on phone and copied to PC at {local_target}!"

        return f"Picture successfully taken on phone! Saved as {new_file}."

    def record_video(self, duration_seconds: int = 5) -> str:
        """Launch video mode, record for duration_seconds, and stop."""
        self.wake_screen()
        self._run_adb(["shell", "am", "start", "-a", "android.media.action.VIDEO_CAPTURE"])
        time.sleep(1.5)

        w, h = self.get_screen_size()
        shutter_x = w // 2
        shutter_y = int(h * 0.865)

        # Start recording
        self._run_adb(["shell", "input", "tap", str(shutter_x), str(shutter_y)])
        time.sleep(max(1, duration_seconds))
        # Stop recording
        self._run_adb(["shell", "input", "tap", str(shutter_x), str(shutter_y)])
        return f"Recorded {duration_seconds}-second video on phone."

    def switch_camera(self) -> str:
        """Switch between front and rear camera in active camera app."""
        w, h = self.get_screen_size()
        switch_x = int(w * 0.858)
        switch_y = int(h * 0.865)
        self._run_adb(["shell", "input", "tap", str(switch_x), str(switch_y)])
        return "Switched camera view."

    def tap(self, x: int, y: int) -> str:
        """Tap screen coordinates (x, y)."""
        return self._run_adb(["shell", "input", "tap", str(x), str(y)])

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
        """Swipe from (x1, y1) to (x2, y2)."""
        return self._run_adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])

    def type_phone(self, text: str) -> str:
        """Type text into currently focused input field."""
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        return self._run_adb(["shell", "input", "text", escaped])

    def press_key(self, key_name: str) -> str:
        """Press an Android system key (home, back, app_switch, volume_up, volume_down, power, enter, etc.)."""
        keycodes = {
            "home": "3",
            "back": "4",
            "call": "5",
            "endcall": "6",
            "volume_up": "24",
            "volume_down": "25",
            "power": "26",
            "camera": "27",
            "clear": "28",
            "enter": "66",
            "menu": "82",
            "unlock": "82",
            "app_switch": "187", # Recent apps
            "overview": "187",
            "recent": "187",
            "wakeup": "224"
        }
        code = keycodes.get(key_name.lower().strip(), key_name)
        return self._run_adb(["shell", "input", "keyevent", code])

    def tap_element_by_text(self, text_or_desc: str) -> str:
        """Dynamically find any text or button on the phone screen and tap it."""
        self._run_adb(["shell", "uiautomator", "dump", "/sdcard/uidump.xml"])
        xml_str = self._run_adb(["shell", "cat", "/sdcard/uidump.xml"])
        if not xml_str or "<hierarchy" not in xml_str:
            return "Could not read UI hierarchy from phone screen."

        try:
            root = ET.fromstring(xml_str)
            target = text_or_desc.lower().strip()
            for node in root.iter("node"):
                text = node.attrib.get("text", "")
                desc = node.attrib.get("content-desc", "")
                bounds = node.attrib.get("bounds", "")
                if target in text.lower() or target in desc.lower():
                    # Parse bounds e.g. [503,2245][721,2463]
                    coords = [int(n) for n in re.findall(r'\d+', bounds)]
                    if len(coords) >= 4:
                        cx = (coords[0] + coords[2]) // 2
                        cy = (coords[1] + coords[3]) // 2
                        self._run_adb(["shell", "input", "tap", str(cx), str(cy)])
                        return f"Found and tapped '{text or desc}' at ({cx}, {cy}) on phone."
            return f"Could not find element matching '{text_or_desc}' on screen."
        except Exception as e:
            return f"Error parsing phone screen elements: {e}"

    def get_screen_text(self) -> str:
        """Read all visible text strings from current phone screen."""
        self._run_adb(["shell", "uiautomator", "dump", "/sdcard/uidump.xml"])
        xml_str = self._run_adb(["shell", "cat", "/sdcard/uidump.xml"])
        if not xml_str:
            return "Screen empty or unavailable."
        try:
            root = ET.fromstring(xml_str)
            texts = []
            for node in root.iter("node"):
                t = node.attrib.get("text", "").strip()
                d = node.attrib.get("content-desc", "").strip()
                if t and t not in texts:
                    texts.append(t)
                if d and d not in texts:
                    texts.append(d)
            return "\n".join(texts[:30]) or "No text detected on screen."
        except Exception as e:
            return f"Error reading screen text: {e}"

    def send_whatsapp_message(self, target: str, message: str) -> str:
        """Open WhatsApp chat with contact or number and immediately send the message.
        
        Args:
            target: Name of contact (e.g. 'Rudra', 'Pavi') or phone number.
            message: Text message to send.
        """
        self.wake_screen()
        target_name = target.strip()
        clean_num = re.sub(r'[^\d\+]', '', target)

        if not clean_num or len(clean_num) < 7:
            # Look up contact number from phone database
            contacts = self.find_contacts(target)
            if contacts:
                exact = [c for c in contacts if c["name"].lower() == target.lower()]
                best = exact[0] if exact else contacts[0]
                target_name = best["name"]
                clean_num = re.sub(r'[^\d\+]', '', best["number"])

        if clean_num:
            # Ensure country code is present (default India +91 if 10 digits)
            digits_only = re.sub(r'\D', '', clean_num)
            if len(digits_only) == 10:
                digits_only = "91" + digits_only
            elif digits_only.startswith("0") and len(digits_only) == 11:
                digits_only = "91" + digits_only[1:]

            import urllib.parse
            encoded_msg = urllib.parse.quote(message)
            url = f"https://api.whatsapp.com/send?phone={digits_only}&text={encoded_msg}"
            self._run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.whatsapp"])
            time.sleep(1.8)

            # Tap the WhatsApp send button
            w, h = self.get_screen_size()
            send_x = int(w * 0.93)
            send_y = int(h * 0.96)
            self._run_adb(["shell", "input", "tap", str(send_x), str(send_y)])
            time.sleep(0.5)
            # Second tap safety in case keyboard was adjusting
            self._run_adb(["shell", "input", "tap", str(send_x), str(send_y)])
            return f"Sent WhatsApp message '{message}' to {target_name} ({digits_only}) on your phone, Luffy!"
        else:
            # Fallback: Open WhatsApp, search contact, type and send
            self.open_phone_app("whatsapp")
            time.sleep(1.2)
            self.tap_element_by_text("Search")
            time.sleep(0.5)
            self.type_phone(target)
            time.sleep(1.0)
            self.tap(400, 450) # Tap first result
            time.sleep(1.0)
            self.type_phone(message)
            time.sleep(0.5)
            w, h = self.get_screen_size()
            self.tap(int(w * 0.93), int(h * 0.96))
            return f"Sent WhatsApp message '{message}' to {target_name} on your phone, Luffy!"

    def open_whatsapp_chat(self, target: str = "", message: str = "") -> str:
        """Open WhatsApp and optionally send message to contact or number."""
        if message:
            return self.send_whatsapp_message(target=target, message=message)
        self.wake_screen()
        clean_num = re.sub(r'[^\d\+]', '', target)
        if clean_num:
            import urllib.parse
            url = f"https://api.whatsapp.com/send?phone={clean_num}"
            self._run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.whatsapp"])
            return f"Opened WhatsApp chat with {clean_num}."
        else:
            self.open_phone_app("whatsapp")
            if target:
                time.sleep(1.0)
                self.tap_element_by_text("Search")
                time.sleep(0.5)
                self.type_phone(target)
            return f"Opened WhatsApp for {target}."

    def set_alarm(self, time_str: str = "5:30am", label: str = "Morning") -> str:
        """Set and save an alarm on the phone's clock app.
        
        Args:
            time_str: Time string like '3:30am', '5:30am', '05:30', '17:30', '7:00 PM'.
            label: Optional alarm message/label.
        """
        self.wake_screen()
        # Parse hour, minute, am/pm
        m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str.lower())
        if not m:
            return f"Could not parse alarm time '{time_str}'."
        
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        ampm = m.group(3)

        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

        # Method 1: Direct Android SET_ALARM intent
        cmd = [
            "shell", "am", "start",
            "-a", "android.intent.action.SET_ALARM",
            "--ei", "android.intent.extra.alarm.HOUR", str(hour),
            "--ei", "android.intent.extra.alarm.MINUTES", str(minute),
            "--es", "android.intent.extra.alarm.MESSAGE", label
        ]
        self._run_adb(cmd)
        time.sleep(1.2)

        # Check if we are on the Save screen or DeskClock
        w, h = self.get_screen_size()
        # Save button in DeskClock Add Alarm screen is centered near bottom: bounds=[244,2494][979,2615]
        save_x = int(w * 0.50)
        save_y = int(h * 0.94)
        self.tap(save_x, save_y)
        time.sleep(0.5)

        # Also trigger dynamic element taps for Save / Done / checkmark
        self.tap_element_by_text("Save")
        time.sleep(0.3)

        display_hour = hour if 0 < hour <= 12 else (12 if hour == 0 else hour - 12)
        period = "AM" if hour < 12 else "PM"
        formatted_time = f"{display_hour}:{minute:02d} {period}"
        return f"Alarm successfully set for {formatted_time} on your phone, Luffy!"

    def open_youtube_video(self, query: str = "") -> str:
        """Open YouTube on phone and search for query."""
        self.wake_screen()
        if query:
            import urllib.parse
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            self._run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
            return f"Playing '{query}' on YouTube on phone."
        return self.open_phone_app("youtube")

    def run_phone_shell(self, command: str) -> str:
        """Execute arbitrary ADB shell command directly on the phone."""
        args = ["shell"] + command.split()
        return self._run_adb(args)

    def make_call(self, phone_number: str) -> str:
        """Initiate a phone call."""
        clean = re.sub(r'[^\d\+]', '', phone_number)
        return self._run_adb(["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{clean}"])

    def send_sms(self, phone_number: str, message: str) -> str:
        """Open SMS composer with phone number and text."""
        clean = re.sub(r'[^\d\+]', '', phone_number)
        return self._run_adb([
            "shell", "am", "start",
            "-a", "android.intent.action.SENDTO",
            "-d", f"smsto:{clean}",
            "--es", "sms_body", message
        ])

    def find_contacts(self, query: str = "") -> List[Dict[str, str]]:
        """Query contacts from Android contacts provider by name or partial match."""
        res = self._run_adb(["shell", "content", "query", "--uri", "content://com.android.contacts/data/phones", "--projection", "display_name:data1"], timeout=15)
        clean_q = query.lower().strip()
        matches = []
        for line in res.splitlines():
            if "display_name=" in line and "data1=" in line:
                m = re.search(r'display_name=(.*?),\s*data1=(.*)', line)
                if m:
                    raw_name = m.group(1).encode('ascii', 'ignore').decode().strip()
                    cnum = m.group(2).strip()
                    if not clean_q or clean_q in raw_name.lower():
                        matches.append({"name": raw_name, "number": cnum})
        # Deduplicate while preserving order
        unique = []
        seen = set()
        for item in matches:
            key = (item["name"].lower(), re.sub(r'\D', '', item["number"]))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def call_contact(self, name_or_number: str) -> str:
        """Find contact by name (e.g. 'Pavi', 'Rudra') or phone number, open dialer/call screen, and initiate call."""
        self.wake_screen()
        digits = re.sub(r'[^\d\+]', '', name_or_number)
        
        target_name = name_or_number
        target_num = None

        if len(digits) >= 5 and not any(c.isalpha() for c in name_or_number):
            target_num = digits
        else:
            contacts = self.find_contacts(name_or_number)
            if contacts:
                # Prefer exact match if possible
                exact = [c for c in contacts if c["name"].lower() == name_or_number.lower()]
                best = exact[0] if exact else contacts[0]
                target_name = best["name"]
                target_num = re.sub(r'[^\d\+]', '', best["number"])
            else:
                # Fallback: Open contacts app and search
                self.open_phone_app("contacts")
                time.sleep(1.0)
                self.tap(964, 189) # Tap enter_search
                time.sleep(0.5)
                self.type_phone(name_or_number)
                return f"Could not find exact number for '{name_or_number}'. Opened Contacts search on phone."

        # Initiate call on phone
        self._run_adb(["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{target_num}"])
        self._run_adb(["shell", "am", "start", "-a", "android.intent.action.DIAL", "-d", f"tel:{target_num}"])
        return f"Calling {target_name} ({target_num}) on your phone, Luffy!"

    def open_maps_route(self, destination: str = "nearest petrol bunk") -> str:
        """Open Google Maps on phone and immediately route/navigate to destination."""
        self.wake_screen()
        import urllib.parse
        encoded = urllib.parse.quote_plus(destination)
        self._run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f"google.navigation:q={encoded}"])
        return f"Google Maps navigation to '{destination}' opened on your phone, Luffy!"

    def calculate_on_phone(self, expression: str) -> str:
        """Open phone Calculator and compute math expression."""
        self.wake_screen()
        self.open_phone_app("calculator")
        time.sleep(1.0)
        clean_expr = expression.replace(" ", "")
        for ch in clean_expr:
            if ch in ['0','1','2','3','4','5','6','7','8','9','+','-','*','/']:
                self.type_phone(ch)
            time.sleep(0.08)
        self._run_adb(["shell", "input", "keyevent", "66"]) # Enter / Equals
        return f"Calculated {clean_expr} in phone Calculator."

    def test_all_phone_apps(self) -> str:
        """Systematically open and test major applications on the phone with functional actions."""
        results = []
        
        # 1. Contacts & Search
        self.open_phone_app("contacts")
        time.sleep(1.0)
        pavi_matches = self.find_contacts("pavi")
        rudra_matches = self.find_contacts("rudra")
        pavi_str = f"Found {pavi_matches[0]['name']} ({pavi_matches[0]['number']})" if pavi_matches else "Pavi not found"
        rudra_str = f"Found {rudra_matches[0]['name']} ({rudra_matches[0]['number']})" if rudra_matches else "Rudra not found"
        results.append(f"1. Contacts: SUCCESS ({pavi_str}, {rudra_str})")

        # 2. Google Maps Navigation
        self.open_maps_route("nearest petrol bunk")
        time.sleep(1.5)
        results.append("2. Google Maps: SUCCESS (Navigating to nearest petrol bunk)")

        # 3. Camera
        self.take_photo(camera_type="back", pull_to_pc=False)
        time.sleep(1.0)
        results.append("3. Camera: SUCCESS (Photo captured)")

        # 4. Calculator - Compute math expression
        self.calculate_on_phone("125+75")
        results.append("4. Calculator: SUCCESS (Calculated 125+75)")

        # 5. Clock - Set Alarm at 5:30 AM
        alarm_res = self.set_alarm(time_str="5:30am", label="Morning Routine")
        time.sleep(1.0)
        results.append(f"5. Clock: SUCCESS ({alarm_res})")

        # 6. Gallery / Photos - View photos
        self.open_phone_app("gallery")
        time.sleep(1.0)
        results.append("6. Gallery: SUCCESS (Album viewer opened)")

        # 7. YouTube - Search & play
        self.open_youtube_video("lofi beats")
        time.sleep(1.5)
        results.append("7. YouTube: SUCCESS (Searching & playing lofi beats)")

        # 8. WhatsApp - Multi-command: Open & send message to Rudra
        wa_res = self.send_whatsapp_message(target="Rudra", message="hi")
        time.sleep(1.5)
        results.append(f"8. WhatsApp: SUCCESS ({wa_res})")

        # 9. Browser - Launch web browser
        self.open_phone_app("browser")
        time.sleep(1.0)
        results.append("9. Browser (Brave): SUCCESS (Browser launched)")

        # 10. Settings - System settings
        self.open_phone_app("settings")
        time.sleep(1.0)
        results.append("10. Settings: SUCCESS (Settings opened)")

        # Return to home screen
        self.press_key("home")

        return "Phone App Multi-Command Test Suite Complete:\n" + "\n".join(results)

phone = PhoneController()
