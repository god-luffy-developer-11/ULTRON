"""Double clap audio detector using sounddevice and numpy volume spikes."""
import time
import threading
from typing import Callable, Optional
import numpy as np
import sounddevice as sd

class ClapDetector:
    def __init__(self, on_double_clap: Optional[Callable[[], None]] = None):
        self.on_double_clap = on_double_clap
        self.running = False
        self.thread = None
        self.sample_rate = 16000
        self.threshold = 0.4  # Audio spike threshold (normalized 0 to 1)
        self.last_spike_time = 0.0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _listen_loop(self):
        block_duration = 0.05  # 50ms chunks
        block_size = int(self.sample_rate * block_duration)

        def audio_callback(indata, frames, time_info, status):
            if not self.running:
                raise sd.CallbackStop()
            
            # Root mean square / peak amplitude
            amplitude = np.max(np.abs(indata))
            current_time = time.time()

            if amplitude > self.threshold:
                diff = current_time - self.last_spike_time
                # Double clap detected between 0.15s and 0.65s apart
                if 0.15 <= diff <= 0.65:
                    print("\n[Trigger] Double clap detected!")
                    self.last_spike_time = 0.0
                    if self.on_double_clap:
                        self.on_double_clap()
                else:
                    self.last_spike_time = current_time

        try:
            with sd.InputStream(channels=1, samplerate=self.sample_rate, blocksize=block_size, callback=audio_callback):
                while self.running:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[ClapDetector] Audio stream error: {e}")
