import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import os
import tempfile
import threading
import sounddevice as sd
import numpy as np
import requests
from core.config import Config

class Speaker:
    def __init__(self):
        self._lock = threading.Lock()
        self.stop_requested = False
        self.is_speaking = False
        self.elevenlabs_quota_exceeded = False
        self.preferred_engine = os.getenv("VOICE_ENGINE", "edge").lower().strip()

    def speak(self, text: str, wait: bool = False) -> str:
        """Speak out text asynchronously (non-blocking) using Edge Neural TTS or ElevenLabs."""
        if not text or not text.strip():
            return "No text to speak."
        
        self.stop_requested = False
        text = text.strip()
        print(f"\n[ULTRON]: \"{text}\"")

        def _worker():
            with self._lock:
                self.is_speaking = True
                try:
                    # 1. ElevenLabs if explicitly configured
                    if self.preferred_engine == "elevenlabs" and Config.ELEVENLABS_API_KEY and not self.elevenlabs_quota_exceeded:
                        try:
                            if self._speak_elevenlabs(text):
                                return
                        except Exception:
                            pass

                    # 2. Unlimited Edge Neural TTS
                    self._speak_edge_tts(text)
                except Exception as e:
                    print(f"[Speaker] Speech playback notice: {e}")
                finally:
                    self.is_speaking = False

        t = threading.Thread(target=_worker, daemon=True, name="UltronSpeakerThread")
        t.start()
        if wait:
            t.join()
        return f"Spoke: {text}"

    def _speak_elevenlabs(self, text: str) -> bool:
        voice_id = Config.ELEVENLABS_VOICE_ID or "cgSgspJ2msm6clMCkdW9" # Jessica - female
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": Config.ELEVENLABS_API_KEY
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8
            }
        }
        try:
            resp = requests.post(url, json=data, headers=headers, timeout=8)
            if resp.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                    f.write(resp.content)
                    temp_path = f.name
                self._play_audio_file(temp_path)
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                return True
            else:
                if "quota_exceeded" in resp.text or resp.status_code in [401, 429]:
                    self.elevenlabs_quota_exceeded = True
                    print("[Speaker] ElevenLabs monthly quota exhausted. Seamlessly switched to Microsoft Neural Voice (Ava & Pallavi) - Unlimited Free.")
                return False
        except Exception:
            return False

    def _speak_edge_tts(self, text: str):
        import edge_tts

        # Detect Tamil Unicode range (\u0B80 - \u0BFF)
        has_tamil = any('\u0b80' <= c <= '\u0bff' for c in text)
        voice = "ta-IN-PallaviNeural" if has_tamil else "en-US-AvaMultilingualNeural"

        async def _run():
            communicate = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                temp_path = f.name
            await communicate.save(temp_path)
            return temp_path

        loop = asyncio.new_event_loop()
        temp_path = loop.run_until_complete(_run())
        loop.close()
        
        self._play_audio_file(temp_path)
        try:
            os.remove(temp_path)
        except Exception:
            pass

    def _play_audio_file(self, path: str):
        if self.stop_requested:
            return
        
        self.is_speaking = True
        try:
            # Primary: pygame mixer for instant low-latency local audio playback
            try:
                import pygame
                import time
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and not self.stop_requested:
                    time.sleep(0.04)
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                return
            except Exception as e:
                print(f"[Speaker] Pygame audio error: {e}. Trying system player fallback.")

            # Secondary fallback: Windows Media Player via PowerShell
            import subprocess
            ps_cmd = (
                f"$wm = New-Object -ComObject WMPlayer.OCX; "
                f"$wm.URL = '{path}'; "
                f"$wm.controls.play(); "
                f"$timeout = 0; "
                f"while($wm.playState -ne 1 -and $timeout -lt 60) {{ Start-Sleep -Milliseconds 100; $timeout++ }}; "
                f"[System.Runtime.Interopservices.Marshal]::ReleaseComObject($wm) | Out-Null"
            )
            try:
                subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, timeout=12)
            except Exception:
                pass
        finally:
            self.is_speaking = False

    def stop(self):
        self.stop_requested = True
        self.is_speaking = False
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

speaker = Speaker()
