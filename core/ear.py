"""Unified low-latency microphone engine supporting Double-Clap triggers and full multi-sentence Speech Recognition."""
import collections
import time
import pyaudio
import numpy as np
from typing import Tuple, Optional
from scipy import signal
try:
    import noisereduce as nr
except ImportError:
    nr = None

from core.config import Config
from core.speaker import speaker

class Ear:
    def __init__(self, model_size: str = None):
        self.model_size = model_size or Config.WHISPER_MODEL or "tiny.en"
        self.whisper_model = None
        self.pa = None
        self.stream = None
        self.rate = 16000
        self.chunk_size = 512  # 32ms chunks
        self.last_spike_time = 0.0
        self.clap_threshold = 0.42 # Normalized peak spike threshold for hand clap
        self.ambient_rms = 0.010
        self.enable_clap_detection = True # Active in standby mode

        # Human vocal isolation bandpass filter (85 Hz to 7500 Hz)
        try:
            self.sos_filter = signal.butter(4, [85, 7500], btype='bandpass', fs=self.rate, output='sos')
        except Exception:
            self.sos_filter = None

    def _load_model(self):
        if self.whisper_model is None:
            from faster_whisper import WhisperModel
            print(f"[Ear] Loading Whisper ({self.model_size})...")
            self.whisper_model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=4
            )
            print("[Ear] Whisper engine online.")

    def _ensure_stream(self):
        """Ensure PyAudio stream is open."""
        if self.pa is None:
            self.pa = pyaudio.PyAudio()
        if self.stream is None or not self.stream.is_active():
            try:
                self.stream = self.pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
            except Exception as e:
                print(f"[Ear] Error opening microphone stream: {e}")

    def isolate_voice(self, audio_float: np.ndarray, noise_sample: Optional[np.ndarray] = None) -> np.ndarray:
        """Apply multi-stage spectral noise reduction, acoustic vocal bandpass filtering, and volume normalization."""
        try:
            # 1. Bandpass filter: strip non-vocal low hums (<85Hz) and ultra-high hiss (>7500Hz)
            if self.sos_filter is not None:
                audio_float = signal.sosfilt(self.sos_filter, audio_float)

            # 2. Spectral noise suppression / Voice Isolation
            if nr is not None:
                if noise_sample is not None and len(noise_sample) >= 512:
                    audio_float = nr.reduce_noise(
                        y=audio_float,
                        y_noise=noise_sample,
                        sr=self.rate,
                        stationary=False,
                        prop_decrease=0.88,
                        n_jobs=2
                    )
                else:
                    audio_float = nr.reduce_noise(
                        y=audio_float,
                        sr=self.rate,
                        stationary=True,
                        prop_decrease=0.85,
                        n_jobs=2
                    )

            # 3. Peak normalization to -1.0 dBFS (0.90) for crisp, clean Whisper recognition
            peak = float(np.max(np.abs(audio_float)))
            if peak > 1e-4:
                audio_float = (audio_float / peak) * 0.90

            return audio_float.astype(np.float32)
        except Exception as e:
            print(f"[Ear] Voice isolation fallback notice: {e}")
            return audio_float

    def listen_cycle(self, timeout: float = 3.5, max_phrase_time: float = 25.0) -> Tuple[str, str]:
        """Capture from mic, returning ('DOUBLE_CLAP', '') or ('SPEECH', transcript) or ('TIMEOUT', '').
        
        Applies real-time voice isolation and speech enhancement.
        """
        self._load_model()
        self._ensure_stream()

        # Wait while ULTRON is speaking to prevent self-echo
        while speaker.is_speaking:
            time.sleep(0.08)

        start_time = time.time()
        speech_start_time = None
        speech_chunks = []
        is_speaking = False
        silence_chunks = 0
        
        # 22 chunks = ~0.70 seconds of continuous silence required to signal end of sentence.
        # Fast, responsive turnaround without trailing delay.
        max_silence_chunks = 22
        
        # Ring buffer of recent 250ms audio so first consonant/syllable is never lost
        pre_buffer = collections.deque(maxlen=8)
        # Background noise profile buffer for adaptive voice isolation
        noise_buffer = collections.deque(maxlen=16)

        while True:
            # Check timeouts:
            # 1. If not speaking yet: obey initial wait timeout (e.g. 3.5s)
            if not is_speaking and (time.time() - start_time >= timeout):
                break
            # 2. If speaking: allow long phrases up to max_phrase_time (e.g. 25.0s)
            if is_speaking and (time.time() - speech_start_time >= max_phrase_time):
                break

            if speaker.is_speaking:
                speech_chunks.clear()
                is_speaking = False
                time.sleep(0.08)
                continue

            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            except Exception:
                time.sleep(0.02)
                continue

            pcm = np.frombuffer(data, dtype=np.int16)
            pcm_float = pcm.astype(np.float32) / 32768.0
            peak = float(np.max(np.abs(pcm_float)))
            rms = float(np.sqrt(np.mean(pcm_float**2)))

            # 1. Double-Clap Spike Detection (only when in standby mode)
            if self.enable_clap_detection and peak > self.clap_threshold:
                now = time.time()
                diff = now - self.last_spike_time
                if 0.15 <= diff <= 0.70:
                    self.last_spike_time = 0.0
                    return ("DOUBLE_CLAP", "")
                else:
                    self.last_spike_time = now

            # 2. Speech Activity Detection
            # Dynamically adapt to ambient noise while staying sensitive to voice
            speech_threshold = min(max(self.ambient_rms * 1.35, 0.012), 0.035)

            if not is_speaking:
                # Track ambient noise floor and profile while idle
                self.ambient_rms = 0.96 * self.ambient_rms + 0.04 * rms
                pre_buffer.append(data)
                noise_buffer.append(data)

                if rms > speech_threshold:
                    is_speaking = True
                    speech_start_time = time.time()
                    speech_chunks.extend(list(pre_buffer))
                    speech_chunks.append(data)
                    silence_chunks = 0
                    print(" [Listening...]", end="", flush=True)
            else:
                speech_chunks.append(data)
                if rms <= speech_threshold:
                    silence_chunks += 1
                    if silence_chunks >= max_silence_chunks:
                        # Speaker has paused for ~0.70s, full sentence complete
                        break
                else:
                    silence_chunks = 0

        if is_speaking and speech_chunks:
            print(" [Processing...]", flush=True)
            total_raw = b"".join(speech_chunks)
            audio_int16 = np.frombuffer(total_raw, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            # Ignore clicks or coughs shorter than 0.35s
            if len(audio_float32) >= int(self.rate * 0.35):
                try:
                    # Extract background ambient profile for targeted voice isolation
                    if noise_buffer:
                        raw_noise = b"".join(list(noise_buffer))
                        noise_float = np.frombuffer(raw_noise, dtype=np.int16).astype(np.float32) / 32768.0
                    else:
                        noise_float = None

                    # Apply Multi-stage Voice Isolation
                    isolated_audio = self.isolate_voice(audio_float32, noise_sample=noise_float)

                    # Dynamically transcribe English or Tamil with Silero VAD filtering on isolated voice
                    segments, info = self.whisper_model.transcribe(
                        isolated_audio,
                        beam_size=3,
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=280),
                        condition_on_previous_text=False
                    )

                    # Only accept English or Tamil to eliminate foreign hallucination artifacts
                    if info.language not in ("en", "ta"):
                        print(f" [Filtered noise: {info.language} ({info.language_probability:.2f})]")
                        return ("TIMEOUT", "")

                    transcript = " ".join([s.text for s in segments]).strip()
                    # Filter out empty or hallucinated noise tokens
                    hallucinations = {
                        "thank you.", "thank you", "thanks for watching.", "thanks for watching",
                        "you", ".", "..", "...", "subtitles by...", "[music]", "bye.", "bye",
                        "thank you for watching.", "okay.", "okay", "yeah.", "yeah"
                    }
                    if transcript and transcript.lower().strip() not in hallucinations:
                        return ("SPEECH", transcript)
                except Exception as e:
                    print(f"[Ear] Whisper transcription error: {e}")

        return ("TIMEOUT", "")

    def listen(self, timeout: float = 3.5, max_phrase_time: float = 25.0) -> str:
        """Helper that returns transcript string."""
        event, text = self.listen_cycle(timeout=timeout, max_phrase_time=max_phrase_time)
        return text if event == "SPEECH" else ""

    def close(self):
        """Close audio stream."""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.pa:
                self.pa.terminate()
        except Exception:
            pass

ear = Ear()
