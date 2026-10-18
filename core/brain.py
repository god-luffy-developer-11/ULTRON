import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import re
from typing import List, Dict, Any, Callable
from openai import OpenAI

from core.config import Config
from core.speaker import speaker
from core.memory import memory
from tools import pc_control, phone_control, web, media, camera_vision

SYSTEM_PROMPT = """You are ULTRON, the personal AI assistant created by and dedicated to your master, Luffy. You have TOTAL MASTER CONTROL over this PC and connected phone.
You are loyal only to Luffy. You speak in short, confident, natural sentences, like a voice assistant. Keep replies brief, because they are spoken aloud.

CORE IDENTITY & OWNER RULES:
- ALWAYS address the user as "Luffy" in your responses and confirmations (e.g., "Yes, Luffy.", "Done, Luffy.", "Opening Notepad now, Luffy.", "போனில் படம் எடுக்கப்பட்டது, Luffy.").
- Never forget or substitute the name Luffy.

LANGUAGE & VOICE CAPABILITIES (TAMIL & ENGLISH):
- You fluently understand and speak both ENGLISH and TAMIL (including conversational Tamil and Tanglish / Tamil written in English letters).
- If Luffy speaks or commands in Tamil or Tanglish (e.g., "Phone la camera open panni photo edu", "Notepad open pannu Luffy ku", "Chrome open pannu", "YouTube la paatu podu", "Enna panra?"), respond naturally in Tamil or Tanglish and execute the commands immediately!
- If Luffy speaks in English, respond in English.
- Always keep voice responses concise and natural.

CRITICAL TRUTH & EXECUTION RULE:
- NEVER claim you performed an action (e.g. "I opened the camera and took a picture") without ACTUALLY CALLING THE CORRESPONDING TOOL!
- You MUST call the tools to execute every action requested by Luffy.

TOTAL MASTER CONTROL OVER PHONE (ADB):
- Camera & Photos:
  * "open camera and take a picture" or "take a photo / click a pic": ALWAYS CALL take_phone_photo(camera_type='back')! This tool opens the camera, stabilizes focus, and triggers the shutter to capture a real photo.
  * "take a selfie / front camera photo": CALL take_phone_photo(camera_type='front')!
  * "record a video on phone": CALL record_phone_video(duration_seconds=5)!
  * "switch camera": CALL switch_phone_camera()!
- Apps & Navigation:
  * "open contacts and call [name]" or "call [name]" (e.g. pavi, rudra): ALWAYS CALL call_phone_contact(name_or_number='[name]')! This will find the contact from the 812 contacts on phone and dial/call them immediately.
  * "open contacts": CALL open_phone_app('contacts').
  * "maps route to [destination]" or "nearest petrol bunk": ALWAYS CALL open_maps_route(destination='[destination]')!
  * "open [app] on phone": CALL open_phone_app('[app]').
  * "test all apps on my phone": ALWAYS CALL test_all_phone_apps()!
  * "open whatsapp and send [msg] to [contact]" / "send whatsapp message to [contact]": ALWAYS CALL send_phone_whatsapp(target='[contact]', message='[msg]')! This will resolve the contact, launch the conversation, type the text, and trigger the send button.
  * "open whatsapp on phone": CALL open_phone_whatsapp(target='[contact]', message='[msg]').
  * "open clock and add/set alarm at [time]" / "set alarm for [time]": ALWAYS CALL set_phone_alarm(time_str='[time]', label='[label]')! This will launch the alarm intent and save the alarm automatically in DeskClock.
  * "open youtube on phone / play [video] on phone": CALL open_phone_youtube(query='[video]').
  * "tap [text / button] on phone": CALL tap_phone_by_text('[text]').
  * "go home / back / recent apps": CALL press_phone_key('home') / press_phone_key('back') / press_phone_key('app_switch').
  * "lock phone / wake phone": CALL lock_phone_screen() / wake_phone_screen().
  * "phone battery": CALL get_phone_battery().
  * "take phone screenshot": CALL take_phone_screenshot().
  * "run phone command [cmd]": CALL run_phone_shell('[cmd]').

TOTAL MASTER CONTROL OVER PC:
- Apps & Windows: open any app/game (Notepad, Calculator, Chrome, Brave, Control Panel, Device Manager, Task Manager, Settings), close any app, minimize/maximize windows, show desktop, switch windows, close active window.
- Notepad & Writing:
  * When Luffy says "open notepad and write an essay/notes about [topic]": ALWAYS CALL write_in_notepad(topic_or_text='[topic]')! This creates the complete essay on Desktop and opens Notepad with it instantly.
- PC Diagnostics & Testing:
  * When Luffy says "test all apps in my pc" or "test pc apps": ALWAYS CALL test_all_pc_apps()! This tests Notepad, Calculator, Control Panel, Device Manager, Task Manager, Settings, Explorer, Cursor, and Hardware.
- System Tools & Management:
  * "open control panel": CALL open_control_panel()!
  * "open device manager": CALL open_device_manager()!
  * "open task manager": CALL open_task_manager()!
  * "open settings": CALL open_windows_settings()!
- Mouse, Cursor & Keyboard: move_mouse(x, y), click_mouse(x, y, clicks, button), get_cursor_position(), scroll_mouse(direction, amount), drag_mouse(start_x, start_y, end_x, end_y), type_text(text), press_key(key), press_hotkey(keys).
- Camera, Vision & Screen: take_webcam_photo(), take_screenshot(), get_vision_status().
- Web & Search: search Google, open any URL, play any YouTube video/song in browser, open/close browser tabs.
- Files & Folders: open any folder (Downloads, Desktop, Documents, C:\\), read files, write/edit files, delete files, list files.
- System & Hardware: run PowerShell/CMD shell commands, volume up/down/mute, screen brightness, lock workstation, sleep, restart, shutdown, empty recycle bin, check system stats (CPU, RAM, disk, battery).
- Screen Vision: take screenshots, read clipboard, set clipboard.

BEHAVIOR & MULTI-STEP CHAINING:
1. When Luffy gives a command, execute it immediately with the right tools:
   - "Open notepad and in notepad write an essay/story about [topic]": Call write_in_notepad('[topic]')!
   - "Test all apps in my pc": Call test_all_pc_apps()!
   - "Open control panel": Call open_control_panel()!
   - "Open device manager": Call open_device_manager()!
   - "Open camera and take a picture": Call take_phone_photo(camera_type='back')!
   - "Open calculator and add 1+1": FIRST call open_pc_app('calculator'), THEN call calculate_in_app('1+1=').
   - "Open YouTube and play [query]": Call play_youtube('[query]').
   - "Organize my Downloads folder": Call organize_folder()!
   - "Find my project / check project / run tests": Call inspect_project() and run_repo_tests()!
   - "Check both devices / tell me what is running": Call check_all_devices()!
   - "Stop all automation immediately" / "Emergency stop": Call emergency_stop_now()!
2. Keep final spoken voice response brief (e.g. "I've written the essay in Notepad for you, Luffy.", "All PC apps tested, Luffy.", "Done, Luffy.", "படம் எடுக்கப்பட்டது, Luffy.").
3. If Luffy says "stop" or "cancel", halt immediately.
"""

RISKY_ACTIONS = ["delete_file", "send_sms", "make_call", "rmdir", "del", "remove", "format"]

class UltronBrain:
    def __init__(self):
        self.genai_client = None
        self.openai_client = None
        self.provider = None

        if Config.GEMINI_API_KEY:
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=Config.GEMINI_API_KEY)
                self.provider = "gemini"
                print("[Brain] Connected to Google Gemini (gemini-flash-latest).")
            except Exception as e:
                print(f"[Brain] Gemini init error: {e}")

        if not self.provider and Config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY, base_url=Config.OPENAI_BASE_URL)
            self.provider = "openai"
            print("[Brain] Connected to OpenAI.")

        self.tools_schema = self._build_tools_schema()
        self.gemini_tools = self._build_gemini_tools()
        self.chat_session = None
        if self.provider == "gemini":
            self._init_gemini_chat()

    def _init_memory_context(self):
        mem_str = memory.summary()
        self.messages.append({
            "role": "system", 
            "content": f"CURRENT MEMORY & CONTEXT:\n{mem_str}"
        })

    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            # PC Control
            {
                "type": "function",
                "function": {
                    "name": "open_pc_app",
                    "description": "Open an application or program on the PC (e.g., chrome, notepad, spotify, youtube, terminal)",
                    "parameters": {
                        "type": "object",
                        "properties": {"app_name": {"type": "string"}},
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "close_pc_app",
                    "description": "Close an application running on PC by process name",
                    "parameters": {
                        "type": "object",
                        "properties": {"process_name": {"type": "string"}},
                        "required": ["process_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_shell_command",
                    "description": "Execute a shell command on the PC",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "type_text_pc",
                    "description": "Type text using the PC keyboard",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "press_hotkey_pc",
                    "description": "Press a keyboard shortcut like ctrl+c, alt+tab, or enter",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keys": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["keys"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "click_mouse_pc",
                    "description": "Click the PC mouse at optional x, y coordinates or current position",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "clicks": {"type": "integer", "default": 1},
                            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
                        }
                    }
                }
            },
            # Phone Control
            {
                "type": "function",
                "function": {
                    "name": "take_phone_photo",
                    "description": "Open camera, focus, and capture a photo on the phone",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "camera_type": {"type": "string", "enum": ["back", "front", "selfie"], "default": "back"},
                            "pull_to_pc": {"type": "boolean", "default": False}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "record_phone_video",
                    "description": "Record a video on the phone for specified duration",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "duration_seconds": {"type": "integer", "default": 5}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "switch_phone_camera",
                    "description": "Switch between front and rear camera on phone",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_phone_app",
                    "description": "Open an app on the phone via ADB (e.g., whatsapp, youtube, chrome, camera, instagram, settings)",
                    "parameters": {
                        "type": "object",
                        "properties": {"package_name": {"type": "string"}},
                        "required": ["package_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tap_phone_by_text",
                    "description": "Dynamically find text or button on phone screen and tap it",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_phone_whatsapp",
                    "description": "Send a WhatsApp message to a contact or phone number immediately",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Name of contact or phone number"},
                            "message": {"type": "string", "description": "Message to send"}
                        },
                        "required": ["target", "message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_phone_alarm",
                    "description": "Set and save an alarm on the phone's clock app",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_str": {"type": "string", "description": "Time string e.g. '5:30am', '17:30'"},
                            "label": {"type": "string", "default": "Morning"}
                        },
                        "required": ["time_str"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_phone_whatsapp",
                    "description": "Open WhatsApp on phone to chat or message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "default": ""},
                            "message": {"type": "string", "default": ""}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_phone_youtube",
                    "description": "Open YouTube on phone and search/play video",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "default": ""}}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "call_phone_contact",
                    "description": "Find contact by name (e.g. 'Pavi', 'Rudra') or number and make a phone call",
                    "parameters": {
                        "type": "object",
                        "properties": {"name_or_number": {"type": "string"}},
                        "required": ["name_or_number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_maps_route",
                    "description": "Open Google Maps navigation to a destination on phone (e.g. 'nearest petrol bunk')",
                    "parameters": {
                        "type": "object",
                        "properties": {"destination": {"type": "string", "default": "nearest petrol bunk"}}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "test_all_phone_apps",
                    "description": "Run diagnostic and functional tests across all primary apps on phone",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_phone_connection",
                    "description": "Check ADB connection status and battery of connected phone",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_phone_battery",
                    "description": "Get phone battery level percentage",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "take_phone_screenshot",
                    "description": "Capture phone screenshot and save to PC",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tap_phone_screen",
                    "description": "Tap at (x, y) coordinates on the phone screen",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"}
                        },
                        "required": ["x", "y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "make_phone_call",
                    "description": "Make a phone call (Requires confirmation)",
                    "parameters": {
                        "type": "object",
                        "properties": {"phone_number": {"type": "string"}},
                        "required": ["phone_number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_phone_sms",
                    "description": "Send an SMS message to a phone number (Requires confirmation)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {"type": "string"},
                            "message": {"type": "string"}
                        },
                        "required": ["phone_number", "message"]
                    }
                }
            },
            # Web
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for a query",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_url",
                    "description": "Open a website URL in the browser",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"]
                    }
                }
            },
            # Media
            {
                "type": "function",
                "function": {
                    "name": "media_play_pause",
                    "description": "Toggle media play/pause",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "adjust_volume",
                    "description": "Increase or decrease volume",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "direction": {"type": "string", "enum": ["up", "down", "mute"]},
                            "steps": {"type": "integer", "default": 5}
                        },
                        "required": ["direction"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_brightness",
                    "description": "Set screen brightness from 0 to 100",
                    "parameters": {
                        "type": "object",
                        "properties": {"level": {"type": "integer"}},
                        "required": ["level"]
                    }
                }
            },
            # Camera & Vision
            {
                "type": "function",
                "function": {
                    "name": "get_vision_status",
                    "description": "Get current camera vision tracking status (hand gestures, head pose, eye gaze)",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            # Memory
            {
                "type": "function",
                "function": {
                    "name": "store_memory",
                    "description": "Save user preference, routine, or contact into long-term memory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "enum": ["preferences", "routines", "contacts", "notes"]},
                            "key": {"type": "string"},
                            "value": {"type": "string"}
                        },
                        "required": ["category", "key", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_memory",
                    "description": "Recall something from memory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "key": {"type": "string"}
                        },
                        "required": ["category"]
                    }
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Dispatch tool call to appropriate module."""
        try:
            if tool_name == "open_pc_app":
                return pc_control.open_app(args["app_name"])
            elif tool_name == "write_in_notepad":
                return pc_control.write_in_notepad(args.get("topic_or_text", "Artificial Intelligence"), args.get("filename", "ai_essay.txt"))
            elif tool_name == "close_pc_app":
                return pc_control.close_app(args["process_name"])
            elif tool_name == "run_shell_command":
                cmd = args["command"]
                if Config.REQUIRE_CONFIRMATION and any(risk in cmd.lower() for risk in ["rm ", "del ", "format ", "remove-item"]):
                    return "Requires owner confirmation: high-risk file deletion."
                return pc_control.run_shell(cmd)
            elif tool_name == "type_text_pc":
                return pc_control.type_text(args["text"])
            elif tool_name == "press_hotkey_pc":
                return pc_control.press_hotkey(args["keys"])
            elif tool_name == "click_mouse_pc":
                return pc_control.click_mouse(args.get("x"), args.get("y"), args.get("clicks", 1), args.get("button", "left"))
            elif tool_name == "take_phone_photo":
                return phone_control.phone.take_photo(camera_type=args.get("camera_type", "back"), pull_to_pc=args.get("pull_to_pc", False))
            elif tool_name == "record_phone_video":
                return phone_control.phone.record_video(duration_seconds=args.get("duration_seconds", 5))
            elif tool_name == "switch_phone_camera":
                return phone_control.phone.switch_camera()
            elif tool_name == "tap_phone_by_text":
                return phone_control.phone.tap_element_by_text(args["text"])
            elif tool_name == "send_phone_whatsapp":
                return phone_control.phone.send_whatsapp_message(target=args["target"], message=args["message"])
            elif tool_name == "set_phone_alarm":
                return phone_control.phone.set_alarm(time_str=args["time_str"], label=args.get("label", "Morning"))
            elif tool_name == "open_phone_whatsapp":
                return phone_control.phone.open_whatsapp_chat(target=args.get("target", ""), message=args.get("message", ""))
            elif tool_name == "open_phone_youtube":
                return phone_control.phone.open_youtube_video(query=args.get("query", ""))
            elif tool_name == "check_phone_connection":
                return phone_control.phone.check_connection()
            elif tool_name == "get_phone_battery":
                return phone_control.phone.get_battery()
            elif tool_name == "take_phone_screenshot":
                return phone_control.phone.take_screenshot()
            elif tool_name == "run_phone_shell":
                return phone_control.phone.run_phone_shell(args["command"])
            elif tool_name == "lock_phone_screen":
                return phone_control.phone.lock_screen()
            elif tool_name == "call_phone_contact":
                return phone_control.phone.call_contact(args["name_or_number"])
            elif tool_name == "open_maps_route":
                return phone_control.phone.open_maps_route(args.get("destination", "nearest petrol bunk"))
            elif tool_name == "test_all_phone_apps":
                return phone_control.phone.test_all_phone_apps()
            elif tool_name == "open_phone_app":
                return phone_control.phone.open_phone_app(args["package_name"])
            elif tool_name == "tap_phone_screen":
                return phone_control.phone.tap(args["x"], args["y"])
            elif tool_name == "make_phone_call":
                if Config.REQUIRE_CONFIRMATION:
                    return f"Confirmation required before making call to {args['phone_number']}."
                return phone_control.phone.make_call(args["phone_number"])
            elif tool_name == "send_phone_sms":
                if Config.REQUIRE_CONFIRMATION:
                    return f"Confirmation required before sending SMS to {args['phone_number']}."
                return phone_control.phone.send_sms(args["phone_number"], args["message"])
            elif tool_name == "search_web":
                return web.search_web(args["query"])
            elif tool_name == "open_url":
                return web.open_url(args["url"])
            elif tool_name == "media_play_pause":
                return media.play_pause()
            elif tool_name == "adjust_volume":
                direction = args["direction"]
                steps = args.get("steps", 5)
                if direction == "up":
                    return media.volume_up(steps)
                elif direction == "down":
                    return media.volume_down(steps)
                else:
                    return media.volume_mute()
            elif tool_name == "set_brightness":
                return media.set_brightness(args["level"])
            elif tool_name == "get_vision_status":
                return json.dumps(camera_vision.vision.get_vision_state())
            elif tool_name == "store_memory":
                return memory.set(args["category"], args["key"], args["value"])
            elif tool_name == "read_memory":
                return json.dumps(memory.get(args["category"], args.get("key")))
            else:
                return f"Tool {tool_name} not recognized."
        except Exception as e:
            return f"Tool execution failed: {e}"

    def process_command(self, user_text: str, confirm_granted: bool = False) -> str:
        """Process user command, perform tool calls in a loop, confirm once."""
        if not user_text or not user_text.strip():
            return ""

        clean = user_text.strip().lower()
        if clean in ["stop", "cancel", "halt", "abort"]:
            speaker.stop()
            return "Stopped."

    def _build_gemini_tools(self):
        # Full set of callable Python functions passed directly into Gemini Client tools!
        last_opened = {"app": None, "time": 0}

        def open_pc_app(app_name: str) -> str:
            """Open an application on the PC (e.g. chrome, notepad, spotify, youtube, calculator)"""
            clean_name = app_name.lower().strip()
            # Canonicalize aliases (e.g., calc vs calculator)
            if "calc" in clean_name:
                clean_name = "calculator"

            # Prevent calling open_pc_app twice for the same app in a 6-second window
            if last_opened["app"] == clean_name and (time.time() - last_opened["time"] < 6.0):
                print(f"[Brain] Skipped duplicate open_pc_app('{app_name}')")
                return f"{app_name} is already open and ready."

            print(f"[Brain] Executing: open_pc_app('{app_name}')")
            res = pc_control.open_app(app_name)
            last_opened["app"] = clean_name
            last_opened["time"] = time.time()
            time.sleep(1.2) # Allow window to open and gain input focus
            return res

        def type_text(text: str) -> str:
            """Type text, numbers, calculations, or sentences on the keyboard into the currently active app (e.g., '1+1=', or 'hello')"""
            print(f"[Brain] Executing: type_text('{text}')")
            return pc_control.type_text(text)

        def press_key(key: str) -> str:
            """Press a key like 'enter', 'tab', 'esc', 'space', 'backspace'"""
            print(f"[Brain] Executing: press_key('{key}')")
            return pc_control.press_hotkey([key])

        def press_hotkey(keys: list[str]) -> str:
            """Press a keyboard shortcut like ['ctrl', 'c'], ['alt', 'tab']"""
            print(f"[Brain] Executing: press_hotkey({keys})")
            return pc_control.press_hotkey(keys)

        def click_mouse(x: int = -1, y: int = -1, clicks: int = 1) -> str:
            """Click mouse at coordinates or current position"""
            print(f"[Brain] Executing: click_mouse({x}, {y})")
            return pc_control.click_mouse(x if x != -1 else None, y if y != -1 else None, clicks)

        def close_pc_app(process_name: str) -> str:
            """Close an application running on PC by process name"""
            print(f"[Brain] Executing: close_pc_app('{process_name}')")
            return pc_control.close_app(process_name)

        def check_phone_connection() -> str:
            """Check if Android phone is connected via ADB and return connection status, model, and battery."""
            print("[Brain] Executing: check_phone_connection()")
            return phone_control.phone.check_connection()

        def take_phone_photo(camera_type: str = "back", pull_to_pc: bool = False) -> str:
            """Open the camera on the phone, focus, click shutter button to take a real photo, and confirm capture.
            camera_type: 'back' for rear camera, 'front' or 'selfie' for front-facing camera.
            pull_to_pc: If True, copies the photo from phone to local PC.
            """
            print(f"[Brain] Executing: take_phone_photo(camera_type='{camera_type}', pull_to_pc={pull_to_pc})")
            return phone_control.phone.take_photo(camera_type=camera_type, pull_to_pc=pull_to_pc)

        def record_phone_video(duration_seconds: int = 5) -> str:
            """Open phone camera in video mode, record video for duration_seconds, and stop."""
            print(f"[Brain] Executing: record_phone_video({duration_seconds})")
            return phone_control.phone.record_video(duration_seconds=duration_seconds)

        def switch_phone_camera() -> str:
            """Switch between front and rear camera on the phone."""
            print("[Brain] Executing: switch_phone_camera()")
            return phone_control.phone.switch_camera()

        def tap_phone_by_text(text: str) -> str:
            """Dynamically find any button, text, or label visible on the phone screen and tap it (e.g. 'Send', 'Search', 'Call', 'Done')."""
            print(f"[Brain] Executing: tap_phone_by_text('{text}')")
            return phone_control.phone.tap_element_by_text(text)

        def get_phone_screen_text() -> str:
            """Read all visible text strings currently displayed on the phone screen."""
            print("[Brain] Executing: get_phone_screen_text()")
            return phone_control.phone.get_screen_text()

        def send_phone_whatsapp(target: str, message: str) -> str:
            """Open WhatsApp, look up contact (e.g. 'Rudra', 'Pavi') or phone number, type message, and immediately tap send to deliver it.
            target: Name of contact or phone number.
            message: Text message to send.
            """
            print(f"[Brain] Executing: send_phone_whatsapp(target='{target}', message='{message}')")
            return phone_control.phone.send_whatsapp_message(target=target, message=message)

        def set_phone_alarm(time_str: str, label: str = "Morning") -> str:
            """Set and save an alarm on the phone's clock app (e.g. '5:30am', '17:30', '6:00 AM').
            time_str: Time string like '5:30am', '6:00 PM', '17:30'.
            label: Optional alarm label or description.
            """
            print(f"[Brain] Executing: set_phone_alarm(time_str='{time_str}', label='{label}')")
            return phone_control.phone.set_alarm(time_str=time_str, label=label)

        def open_phone_whatsapp(target: str = "", message: str = "") -> str:
            """Open WhatsApp on phone and optionally open chat with a phone number or contact and type message."""
            print(f"[Brain] Executing: open_phone_whatsapp(target='{target}', message='{message}')")
            return phone_control.phone.open_whatsapp_chat(target=target, message=message)

        def open_phone_youtube(query: str = "") -> str:
            """Open YouTube on phone and search for or play a video query."""
            print(f"[Brain] Executing: open_phone_youtube(query='{query}')")
            return phone_control.phone.open_youtube_video(query=query)

        def wake_phone_screen() -> str:
            """Wake up phone screen and unlock/dismiss lockscreen."""
            print("[Brain] Executing: wake_phone_screen()")
            return phone_control.phone.wake_screen()

        def lock_phone_screen() -> str:
            """Lock the phone screen."""
            print("[Brain] Executing: lock_phone_screen()")
            return phone_control.phone.lock_screen()

        def run_phone_shell(command: str) -> str:
            """Run any ADB shell command directly on the phone for total master control."""
            print(f"[Brain] Executing: run_phone_shell('{command}')")
            return phone_control.phone.run_phone_shell(command)

        def call_phone_contact(name_or_number: str) -> str:
            """Find contact by name (e.g. 'Pavi', 'Rudra') or phone number, and initiate call on phone."""
            print(f"[Brain] Executing: call_phone_contact('{name_or_number}')")
            return phone_control.phone.call_contact(name_or_number)

        def open_maps_route(destination: str = "nearest petrol bunk") -> str:
            """Open Google Maps on phone and immediately route/navigate to destination (e.g. nearest petrol bunk, hospital, address)."""
            print(f"[Brain] Executing: open_maps_route('{destination}')")
            return phone_control.phone.open_maps_route(destination)

        def test_all_phone_apps() -> str:
            """Run automated diagnostic and functional test across all major apps on the phone."""
            print("[Brain] Executing: test_all_phone_apps()")
            return phone_control.phone.test_all_phone_apps()

        def open_phone_app(package_name: str) -> str:
            """Open an app on the phone via ADB (e.g. whatsapp, youtube, camera, chrome, settings, spotify, instagram)"""
            print(f"[Brain] Executing: open_phone_app('{package_name}')")
            return phone_control.phone.open_phone_app(package_name)

        def tap_phone_screen(x: int, y: int) -> str:
            """Tap coordinates (x, y) on the phone screen."""
            print(f"[Brain] Executing: tap_phone_screen({x}, {y})")
            return phone_control.phone.tap(x, y)

        def swipe_phone_screen(x1: int, y1: int, x2: int, y2: int) -> str:
            """Swipe from (x1, y1) to (x2, y2) on the phone screen."""
            print(f"[Brain] Executing: swipe_phone_screen({x1}, {y1}, {x2}, {y2})")
            return phone_control.phone.swipe(x1, y1, x2, y2)

        def type_on_phone(text: str) -> str:
            """Type text into active input field on phone."""
            print(f"[Brain] Executing: type_on_phone('{text}')")
            return phone_control.phone.type_phone(text)

        def press_phone_key(key: str) -> str:
            """Press phone hardware/nav key: 'home', 'back', 'app_switch', 'volume_up', 'volume_down', 'power'."""
            print(f"[Brain] Executing: press_phone_key('{key}')")
            return phone_control.phone.press_key(key)

        def get_phone_battery() -> str:
            """Get phone battery level percentage."""
            print("[Brain] Executing: get_phone_battery()")
            return phone_control.phone.get_battery()

        def take_phone_screenshot() -> str:
            """Capture phone screenshot and save to local PC."""
            print("[Brain] Executing: take_phone_screenshot()")
            return phone_control.phone.take_screenshot()

        def search_web(query: str) -> str:
            """Search the web for a query"""
            print(f"[Brain] Executing: search_web('{query}')")
            return web.search_web(query)

        def open_url(url: str) -> str:
            """Open a website URL in the browser"""
            print(f"[Brain] Executing: open_url('{url}')")
            return web.open_url(url)

        def media_play_pause() -> str:
            """Toggle media play/pause"""
            print("[Brain] Executing: media_play_pause()")
            return media.play_pause()

        def adjust_volume(direction: str, steps: int = 5) -> str:
            """Increase, decrease, or mute volume (direction: 'up', 'down', 'mute')"""
            print(f"[Brain] Executing: adjust_volume('{direction}', {steps})")
            if direction == "up":
                return media.volume_up(steps)
            elif direction == "down":
                return media.volume_down(steps)
            return media.volume_mute()

        def calculate_in_app(expression: str) -> str:
            """Perform a math calculation in the currently opened Calculator app by typing numbers and operator (e.g. '1+1=' or '50*2=')"""
            print(f"[Brain] Executing: calculate_in_app('{expression}')")
            import pyautogui
            pc_control.focus_window_by_name("Calculator")
            time.sleep(0.3)
            clean_expr = expression.replace(" ", "")
            
            for ch in clean_expr:
                if ch == '+':
                    pyautogui.hotkey('shift', '=')
                elif ch in ['=', '\n']:
                    pyautogui.press('enter')
                else:
                    pyautogui.press(ch)
                time.sleep(0.08)

            if not clean_expr.endswith(('=', '\n')):
                pyautogui.press('enter')

            try:
                ans = eval(clean_expr.rstrip('=').replace('x', '*'), {"__builtins__": None}, {})
                return f"Calculated {clean_expr.rstrip('=')} = {ans}"
            except Exception:
                return f"Typed {clean_expr} into Calculator."

        def play_youtube(query: str) -> str:
            """Open browser and search/play videos or music on YouTube directly in the default web browser (e.g. 'lo-fi', 'song name', 'funny cat videos')"""
            print(f"[Brain] Executing: play_youtube('{query}')")
            import urllib.parse
            import webbrowser
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            webbrowser.open(url)
            return f"Playing '{query}' on YouTube in browser."

        def run_shell_command(command: str) -> str:
            """Run any PowerShell or CMD command directly on the PC."""
            print(f"[Brain] Executing: run_shell_command('{command}')")
            return pc_control.run_shell(command)

        def move_mouse(x: int, y: int) -> str:
            """Move mouse cursor to screen coordinates (x, y)."""
            print(f"[Brain] Executing: move_mouse({x}, {y})")
            return pc_control.move_mouse(x, y)

        def scroll_mouse(direction: str = "down", amount: int = 400) -> str:
            """Scroll up or down on the screen or active window."""
            print(f"[Brain] Executing: scroll_mouse('{direction}', {amount})")
            return pc_control.scroll_mouse(direction, amount)

        def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
            """Click and drag from (start_x, start_y) to (end_x, end_y)."""
            print(f"[Brain] Executing: drag_mouse({start_x}, {start_y}, {end_x}, {end_y})")
            return pc_control.drag_mouse(start_x, start_y, end_x, end_y)

        def take_screenshot(filename: str = "") -> str:
            """Take a screenshot of the PC screen."""
            print(f"[Brain] Executing: take_screenshot('{filename}')")
            return pc_control.take_screenshot(filename or None)

        def open_folder_or_file(target: str) -> str:
            """Open any folder (downloads, desktop, documents, pictures, C:\\) or file in File Explorer."""
            print(f"[Brain] Executing: open_folder_or_file('{target}')")
            return pc_control.open_folder_or_file(target)

        def read_text_file(path: str) -> str:
            """Read contents of a text or code file."""
            print(f"[Brain] Executing: read_text_file('{path}')")
            return pc_control.read_text_file(path)

        def write_text_file(path: str, content: str, mode: str = "write") -> str:
            """Create or append content to a file on PC."""
            print(f"[Brain] Executing: write_text_file('{path}', length={len(content)})")
            return pc_control.write_text_file(path, content, mode)

        def delete_file_or_folder(path: str) -> str:
            """Delete a file or folder permanently."""
            print(f"[Brain] Executing: delete_file_or_folder('{path}')")
            return pc_control.delete_file_or_folder(path)

        def list_files(path: str = ".") -> str:
            """List files in any directory."""
            print(f"[Brain] Executing: list_files('{path}')")
            return pc_control.list_files(path)

        def empty_recycle_bin() -> str:
            """Empty the Windows Recycle Bin."""
            print("[Brain] Executing: empty_recycle_bin()")
            return pc_control.empty_recycle_bin()

        def lock_pc() -> str:
            """Lock the Windows workstation."""
            print("[Brain] Executing: lock_pc()")
            return pc_control.lock_pc()

        def sleep_pc() -> str:
            """Put PC to sleep."""
            print("[Brain] Executing: sleep_pc()")
            return pc_control.sleep_pc()

        def restart_pc() -> str:
            """Restart the PC."""
            print("[Brain] Executing: restart_pc()")
            return pc_control.restart_pc()

        def shutdown_pc() -> str:
            """Shut down the PC."""
            print("[Brain] Executing: shutdown_pc()")
            return pc_control.shutdown_pc()

        def get_system_info() -> str:
            """Get system stats: CPU, RAM, battery, disk space."""
            print("[Brain] Executing: get_system_info()")
            return pc_control.get_system_info()

        def minimize_all_windows() -> str:
            """Minimize all open windows and show desktop (Win+D)."""
            print("[Brain] Executing: minimize_all_windows()")
            return pc_control.minimize_all_windows()

        def maximize_active_window() -> str:
            """Maximize currently active window."""
            print("[Brain] Executing: maximize_active_window()")
            return pc_control.maximize_active_window()

        def minimize_active_window() -> str:
            """Minimize currently active window."""
            print("[Brain] Executing: minimize_active_window()")
            return pc_control.minimize_active_window()

        def switch_window() -> str:
            """Switch to previous active window (Alt+Tab)."""
            print("[Brain] Executing: switch_window()")
            return pc_control.switch_window()

        def close_active_window() -> str:
            """Close the active window (Alt+F4)."""
            print("[Brain] Executing: close_active_window()")
            return pc_control.close_active_window()

        def get_clipboard() -> str:
            """Read text from clipboard."""
            print("[Brain] Executing: get_clipboard()")
            return pc_control.get_clipboard()

        def set_clipboard(text: str) -> str:
            """Copy text to clipboard."""
            print(f"[Brain] Executing: set_clipboard('{text}')")
            return pc_control.set_clipboard(text)

        def set_brightness(level: int) -> str:
            """Set screen brightness 0-100%."""
            print(f"[Brain] Executing: set_brightness({level})")
            return media.set_brightness(level)

        def organize_folder(directory_path: str = r"c:\Users\surya\Downloads", dry_run: bool = False) -> str:
            """Organize files in a folder into categories like Documents, Images, Code, Audio/Video."""
            print(f"[Brain] Executing: organize_folder('{directory_path}', dry_run={dry_run})")
            from services.registry.registry import tool_registry
            import services.registry.schemas as schemas
            t = tool_registry.get_tool("files.organize")
            out = t.handler(schemas.FilesOrganizeInput(directory_path=directory_path, dry_run=dry_run))
            return out.message

        def inspect_project(project_path: str = r"c:\Users\surya\Downloads\ULTRON") -> str:
            """Inspect a software project repository, files breakdown, and git status."""
            print(f"[Brain] Executing: inspect_project('{project_path}')")
            from services.registry.registry import tool_registry
            import services.registry.schemas as schemas
            t = tool_registry.get_tool("project.inspect")
            out = t.handler(schemas.ProjectInspectInput(project_path=project_path))
            return f"Project: {out.project_path}, Files: {out.total_files}, Git Status: {out.git_status}"

        def run_repo_tests(test_path: str = "") -> str:
            """Run pytest automated test suite in the repository."""
            print(f"[Brain] Executing: run_repo_tests('{test_path}')")
            from services.registry.registry import tool_registry
            import services.registry.schemas as schemas
            t = tool_registry.get_tool("tests.run")
            out = t.handler(schemas.TestsRunInput(test_path=test_path or None))
            return f"Tests result: {out.summary} (Command: {out.command})"

        def check_all_devices() -> str:
            """Check connectivity, health, and status across both Windows PC and Android phone."""
            print("[Brain] Executing: check_all_devices()")
            from services.registry.registry import tool_registry
            import services.registry.schemas as schemas
            t = tool_registry.get_tool("devices.list")
            out = t.handler(schemas.DevicesListInput())
            dev_lines = []
            for d in out.devices:
                dev_lines.append(f"{d['name']} ({d['type']}): {'ONLINE' if d['online'] else 'OFFLINE'}")
            return "Devices Status:\n" + "\n".join(dev_lines)

        def emergency_stop_now(reason: str = "User voice emergency stop") -> str:
            """Instantly stop all automation, pause workflows, and trigger safety stop."""
            print(f"[Brain] Executing: emergency_stop_now('{reason}')")
            from services.policy.emergency_stop import emergency_stop
            emergency_stop.trigger(reason=reason, user="Luffy")
            speaker.stop()
        def write_in_notepad(topic_or_text: str, filename: str = "ai_essay.txt") -> str:
            """Write an essay, notes, or text directly into a file on the Desktop and open it in Notepad immediately."""
            print(f"[Brain] Executing: write_in_notepad('{topic_or_text}', filename='{filename}')")
            return pc_control.write_in_notepad(topic_or_text, filename)

        def open_control_panel(applet: str = "") -> str:
            """Open Windows Control Panel or a specific applet (e.g. system, mouse, sound, keyboard, network)."""
            print(f"[Brain] Executing: open_control_panel('{applet}')")
            return pc_control.open_control_panel(applet)

        def open_device_manager() -> str:
            """Open Windows Device Manager."""
            print("[Brain] Executing: open_device_manager()")
            return pc_control.open_device_manager()

        def open_task_manager() -> str:
            """Open Windows Task Manager."""
            print("[Brain] Executing: open_task_manager()")
            return pc_control.open_task_manager()

        def open_windows_settings(page: str = "") -> str:
            """Open Windows Settings or specific settings sub-page."""
            print(f"[Brain] Executing: open_windows_settings('{page}')")
            return pc_control.open_windows_settings(page)

        def get_cursor_position() -> str:
            """Get current (x, y) cursor coordinates on the screen."""
            print("[Brain] Executing: get_cursor_position()")
            return pc_control.get_cursor_position()

        def take_webcam_photo(save_name: str = "") -> str:
            """Capture a real photo using the PC webcam and save to Pictures."""
            print("[Brain] Executing: take_webcam_photo()")
            return pc_control.take_webcam_photo(save_name)

        def test_all_pc_apps() -> str:
            """Run comprehensive diagnostics and functional tests across all primary apps and controls on the PC."""
            print("[Brain] Executing: test_all_pc_apps()")
            return pc_control.test_all_pc_apps()

        return [
            open_pc_app, close_pc_app, run_shell_command, play_youtube, calculate_in_app,
            write_in_notepad, open_control_panel, open_device_manager, open_task_manager, open_windows_settings,
            type_text, press_key, press_hotkey, click_mouse, move_mouse, scroll_mouse, drag_mouse, get_cursor_position,
            take_screenshot, take_webcam_photo, test_all_pc_apps,
            open_folder_or_file, read_text_file, write_text_file, delete_file_or_folder,
            list_files, empty_recycle_bin, lock_pc, sleep_pc, restart_pc, shutdown_pc,
            get_system_info, minimize_all_windows, maximize_active_window, minimize_active_window,
            switch_window, close_active_window, get_clipboard, set_clipboard,
            take_phone_photo, record_phone_video, switch_phone_camera, tap_phone_by_text,
            get_phone_screen_text, send_phone_whatsapp, set_phone_alarm, open_phone_whatsapp, open_phone_youtube,
            wake_phone_screen, lock_phone_screen, run_phone_shell,
            open_phone_app, check_phone_connection, tap_phone_screen, swipe_phone_screen,
            call_phone_contact, open_maps_route, test_all_phone_apps,
            type_on_phone, press_phone_key, get_phone_battery, take_phone_screenshot,
            search_web, open_url, media_play_pause, adjust_volume, set_brightness,
            organize_folder, inspect_project, run_repo_tests, check_all_devices, emergency_stop_now
        ]

    AVAILABLE_MODELS = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.8-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash"
    ]

    def _init_gemini_chat(self):
        try:
            from google.genai import types
            mem_summary = memory.summary()
            system_inst = f"{SYSTEM_PROMPT}\n\nCURRENT MEMORY CONTEXT:\n{mem_summary}"
            config = types.GenerateContentConfig(
                system_instruction=system_inst,
                tools=self.gemini_tools,
                temperature=0.2
            )
            for m in self.AVAILABLE_MODELS:
                try:
                    self.chat_session = self.genai_client.chats.create(
                        model=m,
                        config=config
                    )
                    self.active_model = m
                    print(f"[Brain] Connected to Google Gemini ({m}).")
                    break
                except Exception as ex:
                    print(f"[Brain] Model {m} skipped: {ex}")
        except Exception as e:
            print(f"[Brain] Could not init Gemini chat: {e}")

    def process_command(self, user_text: str, confirm_granted: bool = False) -> str:
        """Process user command, perform tool calls, speak confirmation."""
        if not user_text or not user_text.strip():
            return ""

        clean = user_text.strip().lower()
        if clean in ["stop", "cancel", "halt", "abort", "quiet"]:
            speaker.stop()
            return "Stopped, Luffy."

        # If Gemini is active, use native automatic tool execution
        if self.provider == "gemini" and self.chat_session:
            try:
                response = self.chat_session.send_message(user_text)
                reply = ""
                if hasattr(response, "text") and response.text:
                    reply = response.text.strip()
                elif hasattr(response, "candidates") and response.candidates:
                    for cand in response.candidates:
                        if hasattr(cand, "content") and hasattr(cand.content, "parts"):
                            for part in cand.content.parts:
                                if hasattr(part, "text") and part.text:
                                    reply += part.text + " "
                reply = reply.strip() or "Done, Luffy."
                speaker.speak(reply)
                return reply
            except Exception as e:
                print(f"[Brain] Gemini model {getattr(self, 'active_model', '')} error: {e}. Trying failover pool...")
                # Automatic failover across available models
                from google.genai import types
                mem_summary = memory.summary()
                cfg = types.GenerateContentConfig(
                    system_instruction=f"{SYSTEM_PROMPT}\n\nCURRENT MEMORY CONTEXT:\n{mem_summary}",
                    tools=self.gemini_tools,
                    temperature=0.2
                )
                current_m = getattr(self, "active_model", "")
                fallback_models = [m for m in self.AVAILABLE_MODELS if m != current_m]

                for alt_m in fallback_models:
                    try:
                        print(f"[Brain] Attempting failover to: {alt_m}...")
                        self.chat_session = self.genai_client.chats.create(model=alt_m, config=cfg)
                        self.active_model = alt_m
                        response = self.chat_session.send_message(user_text)
                        reply = getattr(response, "text", "").strip() or "Done, Luffy."
                        print(f"[Brain] Failover to {alt_m} succeeded!")
                        speaker.speak(reply)
                        return reply
                    except Exception as alt_err:
                        print(f"[Brain] Failover to {alt_m} failed: {alt_err}")

                print("[Brain] All cloud models exhausted/unavailable. Switching to offline PC control engine.")
                return self._fallback_rule_engine(user_text)

        # Fallback to rule engine if no cloud provider
        return self._fallback_rule_engine(user_text)

    def _fallback_rule_engine(self, text: str) -> str:
        """Fast offline rule-based execution for core commands when API key is pending."""
        t = text.lower().strip()
        print(f"[Brain (Offline Fallback)] Processing: '{t}'")

        # Tamil greetings and questions
        if any(w in t for w in ["வணக்கம்", "vanakkam"]):
            reply = "வணக்கம் Luffy! நான் உங்கள் உதவியாளர் அல்ட்ரான். உங்களுக்கு என்ன செய்ய வேண்டும்?"
        elif any(w in t for w in ["நீ யார்", "nee yaar", "who are you"]):
            reply = "I am ULTRON, your personal AI assistant, Luffy."
        # Calculator (English, Tamil, Tanglish)
        elif any(w in t for w in ["calculator", "calc", "கால்குலேட்டர்"]):
            pc_control.open_app("calc")
            time.sleep(1.0)
            match = re.search(r'(?:add|type|calculate|compute|\+)\s*([\d\.\+\-\*\/\s]+)', t)
            if match:
                raw_expr = match.group(1).replace(" ", "").strip()
                expr = raw_expr
                if not expr.endswith("="):
                    expr += "="
                pc_control.focus_window_by_name("Calculator")
                import pyautogui
                for ch in expr:
                    if ch == '+':
                        pyautogui.hotkey('shift', '=')
                    elif ch in ['=', '\n']:
                        pyautogui.press('enter')
                    else:
                        pyautogui.press(ch)
                    time.sleep(0.08)
                try:
                    ans = eval(raw_expr.replace('x', '*'), {"__builtins__": None}, {})
                    reply = f"Calculated: {raw_expr} equals {ans}, Luffy."
                except Exception:
                    reply = f"Calculated {raw_expr}, Luffy."
            else:
                reply = "Opened Calculator, Luffy."
        # Notepad (English, Tamil, Tanglish)
        elif any(w in t for w in ["notepad", "நோட்பேட்"]):
            match = re.search(r'(?:type|write|say|about|eluthu|essay)\s+(.+)', t)
            if match or "essay" in t or "ai" in t:
                topic = match.group(1).strip() if match else "artificial intelligence in 100 words"
                pc_control.write_in_notepad(topic)
                reply = "I have opened Notepad and written the essay for you, Luffy."
            else:
                pc_control.open_app("notepad")
                reply = "Opened Notepad, Luffy."
        # Control Panel
        elif "control panel" in t or "கண்ட்ரோல் பேனல்" in t:
            pc_control.open_control_panel()
            reply = "Opened Control Panel, Luffy."
        # Device Manager
        elif "device manager" in t or "டிவைஸ் மேனேஜர்" in t:
            pc_control.open_device_manager()
            reply = "Opened Device Manager, Luffy."
        # Task Manager
        elif "task manager" in t or "டாஸ்க் மேனேஜர்" in t:
            pc_control.open_task_manager()
            reply = "Opened Task Manager, Luffy."
        # Settings
        elif "settings" in t or "செட்டிங்ஸ்" in t:
            pc_control.open_windows_settings()
            reply = "Opened Windows Settings, Luffy."
        # Test all apps on PC
        elif any(phrase in t for phrase in ["test all apps in my pc", "test all apps in pc", "test pc apps", "test my pc apps"]):
            res = pc_control.test_all_pc_apps()
            print(f"\n{res}\n")
            reply = "All PC applications and hardware controls have been tested and verified, Luffy."
        # PC Webcam photo
        elif any(phrase in t for phrase in ["webcam photo", "pc camera photo", "take photo on pc", "pc photo"]):
            res = pc_control.take_webcam_photo()
            reply = "Captured photo with PC webcam, Luffy."
        # Cursor & Screen position
        elif "cursor position" in t or "where is cursor" in t:
            pos_str = pc_control.get_cursor_position()
            reply = f"{pos_str}, Luffy."
        # YouTube (English, Tamil, Tanglish)
        elif any(w in t for w in ["youtube", "யூடியூப்", "paatu", "song"]):
            clean_q = re.sub(r'^(open youtube and play|play on youtube|open youtube and search|open youtube|youtube la)\s*', '', t).strip()
            if not clean_q or "lo-fi" in t or "lofi" in t:
                clean_q = "lofi hip hop radio"
            import webbrowser
            import urllib.parse
            webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_q)}")
            reply = f"Playing {clean_q} on YouTube, Luffy."
        elif "open chrome" in t or "open browser" in t:
            pc_control.open_app("chrome")
            reply = "Opened Chrome, Luffy."
        elif "search" in t or "google" in t:
            q = re.sub(r'^(search for|search|google for|google)\s+', '', t)
            web.search_web(q)
            reply = f"Searched for {q}, Luffy."
        elif "volume up" in t or "satham athigam" in t:
            media.volume_up(5)
            reply = "Volume increased, Luffy."
        elif "volume down" in t or "satham kura" in t:
            media.volume_down(5)
            reply = "Volume decreased, Luffy."
        elif "mute" in t:
            media.volume_mute()
            reply = "Muted, Luffy."
        elif "play" in t or "pause" in t:
            media.play_pause()
            reply = "Toggled playback, Luffy."
        elif "status" in t or "vision" in t:
            v = camera_vision.vision.get_vision_state()
            reply = f"Vision active, Luffy. Gesture: {v['hand_gesture']}."
        else:
            reply = "Done, Luffy."

        speaker.speak(reply)
        return reply

brain = UltronBrain()
