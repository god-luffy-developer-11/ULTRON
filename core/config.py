"""Configuration loader for ULTRON."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o").strip()

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB").strip()

    PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "").strip()
    PORCUPINE_KEYWORD = os.getenv("PORCUPINE_KEYWORD", "ultron").strip()

    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base").strip()

    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
    ENABLE_GESTURES = os.getenv("ENABLE_GESTURES", "true").lower() == "true"
    ENABLE_GAZE = os.getenv("ENABLE_GAZE", "true").lower() == "true"

    ADB_DEVICE_SERIAL = os.getenv("ADB_DEVICE_SERIAL", "").strip() or None
    ADB_HOST = os.getenv("ADB_HOST", "127.0.0.1").strip()
    ADB_PORT = int(os.getenv("ADB_PORT", "5037"))

    REQUIRE_CONFIRMATION = os.getenv("REQUIRE_CONFIRMATION_FOR_RISKY_ACTIONS", "true").lower() == "true"
    MEMORY_FILE = ROOT_DIR / "ultron_memory.json"
