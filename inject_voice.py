"""Inject a voice command directly into ULTRON's brain for instant execution."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.brain import brain

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
    else:
        cmd = "Open calculator and add 1+1"

    print(f"\n[Injecting Voice Command]: \"{cmd}\"")
    reply = brain.process_command(cmd)
    print(f"[ULTRON Replied]: \"{reply}\"\n")
