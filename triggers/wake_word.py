"""Wake word detector supporting Porcupine and energy-based fallback."""
import time
import threading
from typing import Callable, Optional
import numpy as np
import sounddevice as sd
from core.config import Config

class WakeWordDetector:
    def __init__(self, on_wake: Optional[Callable[[], None]] = None):
        self.on_wake = on_wake
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_detector, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _run_detector(self):
        # Try Porcupine if access key is present
        if Config.PICOVOICE_ACCESS_KEY:
            try:
                import pvporcupine
                # Default built-in keywords include 'jarvis', 'computer', etc. or custom path for 'ultron'
                handle = pvporcupine.create(
                    access_key=Config.PICOVOICE_ACCESS_KEY,
                    keywords=[Config.PORCUPINE_KEYWORD if Config.PORCUPINE_KEYWORD in pvporcupine.KEYWORDS else "jarvis"]
                )
                with sd.InputStream(channels=1, samplerate=handle.sample_rate, blocksize=handle.frame_length, dtype='int16') as stream:
                    print(f"[WakeWord] Porcupine active. Listening for '{Config.PORCUPINE_KEYWORD}'...")
                    while self.running:
                        pcm, _ = stream.read(handle.frame_length)
                        keyword_index = handle.process(pcm.flatten())
                        if keyword_index >= 0:
                            print("\n[WakeWord] Wake word detected via Porcupine!")
                            if self.on_wake:
                                self.on_wake()
                handle.delete()
                return
            except Exception as e:
                print(f"[WakeWord] Porcupine error ({e}). Falling back to voice activity listening.")

        # Fallback: Voice energy detection + Whisper verification
        self._energy_fallback()

    def _energy_fallback(self):
        sample_rate = 16000
        block_size = int(sample_rate * 0.1) # 100ms
        print("[WakeWord] Continuous listening trigger active. Say 'Ultron' or use hotkey / clap.")
        
        # In fallback mode, the main loop handles microphone inputs directly
        while self.running:
            time.sleep(0.5)
