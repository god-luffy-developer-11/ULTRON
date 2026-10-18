"""Quick diagnostic script to verify microphone recording and Whisper transcription."""
import time
from core.ear import ear

print("========================================")
print("ULTRON Microphone Diagnostic Test")
print("========================================")
print("Speak into your microphone now...")

text = ear.listen(timeout=6.0, phrase_time_limit=8.0)
if text:
    print(f"\nSUCCESS! Heard: \"{text}\"")
else:
    print("\nNo speech detected during the 6-second window.")
print("========================================")
