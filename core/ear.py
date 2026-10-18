"""Unified low-latency microphone engine supporting Double-Clap triggers and full multi-sentence Speech Recognition."""
import collections
import time
import pyaudio
import numpy as np
from typing import Tuple, Optional
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

    def listen_cycle(self, timeout: float = 3.5, max_phrase_time: float = 25.0) -> Tuple[str, str]:
        """Capture from mic, returning ('DOUBLE_CLAP', '') or ('SPEECH', transcript) or ('TIMEOUT', '').
        
        Allows long multi-clause sentences without mid-sentence cutoff.
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
        
        # 48 chunks = ~1.54 seconds of continuous silence required to signal end of sentence.
        # This completely prevents premature cutoffs when the user takes a natural breath or pauses between clauses!
        max_silence_chunks = 48
        
        # Ring buffer of recent 250ms audio so first consonant/syllable is never lost
        pre_buffer = collections.deque(maxlen=8)

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
                # Track ambient noise floor while idle
                self.ambient_rms = 0.96 * self.ambient_rms + 0.04 * rms
                pre_buffer.append(data)

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
                        # Speaker has paused for ~1.54s, full sentence complete
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
                    # Dynamically transcribe English or Tamil (automatic language detection)
                    segments, info = self.whisper_model.transcribe(
                        audio_float32,
                        beam_size=1,
                        condition_on_previous_text=False
                    )
                    transcript = " ".join([s.text for s in segments]).strip()
                    # Filter out empty or hallucinated noise tokens
                    hallucinations = {"thank you.", "thank you", "thanks for watching.", "thanks for watching", "you", ".", "subtitles by...", "[music]", "bye."}
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
