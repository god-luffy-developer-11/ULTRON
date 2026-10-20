"""Main entry point for ULTRON - Personal Autonomous Assistant with Double-Clap Wake & Persistent Voice."""
import os
import sys

# Ensure Windows terminal prints Tamil and multilingual characters without UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import time
import threading
from rich.console import Console
from rich.panel import Panel

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from core.brain import brain
from core.speaker import speaker
from core.ear import ear
from triggers.hotkey_trigger import HotkeyTrigger
from tools.camera_vision import vision

console = Console()
voice_listener_running = True
is_online = False  # Starts in standby, waiting for the first Double-Clap trigger!
execution_lock = threading.Lock()

def set_online_state(online: bool, announce: bool = True):
    """Switch between Standby (clap detection ON) and Active (voice chat ON, clap detection OFF)."""
    global is_online
    is_online = online
    ear.enable_clap_detection = not online  # Only detect claps when sleeping!

    if online:
        if announce:
            speaker.speak("Ultron online. I am listening, Luffy.")
        console.print("\n[bold green]===============================================================[/bold green]")
        console.print("[bold green]>>> ULTRON IS ONLINE & ALWAYS LISTENING FOR LUFFY! <<<[/bold green]")
        console.print("[dim]Tamil & English voice modes active. Clap detection disabled while online.[/dim]")
        console.print("[dim]Listening will NOT turn off until you say 'stop' or 'sleep'.[/dim]")
        console.print("[bold green]===============================================================[/bold green]\n")
        console.print("[bold yellow]ULTRON > [/bold yellow]", end="")
    else:
        if announce:
            speaker.speak("Listening stopped, Luffy. Double clap to wake me.")
        console.print("\n[dim]ULTRON is in standby. Double clap or say 'Ultron' to activate.[/dim]\n")
        console.print("[bold yellow]ULTRON > [/bold yellow]", end="")

def process_input(text: str, source: str = "Voice"):
    """Handle command or chat from voice or terminal."""
    global is_online
    clean = text.lower().strip()
    if not clean:
        return

    # Check for stop / exit listening command
    stop_phrases = ["stop", "exit", "quit", "go to sleep", "sleep", "standby", "stop listening", "ultron stop", "ultron exit", "ultron sleep", "turn off"]
    if clean in stop_phrases or clean.rstrip(".!") in stop_phrases:
        set_online_state(False, announce=True)
        return

    # Check for wake / online command
    if any(w in clean for w in ["wake", "wake up", "online", "start listening"]):
        set_online_state(True, announce=True)
        return

    # Process command or conversational chat with Gemini
    brain.process_command(text)

def voice_listener_loop():
    """Single dedicated audio stream supporting Double-Clap wake and non-stop voice chat."""
    global is_online, voice_listener_running
    try:
        ear._load_model()
    except Exception as e:
        console.print(f"[red]Could not initialize voice listener: {e}[/red]")
        return

    console.print("\n[bold yellow]ULTRON Standby: Double clap now to activate voice listening![/bold yellow]\n")

    while voice_listener_running:
        try:
            # 1. When in STANDBY: Listen for the initial double-clap trigger
            if not is_online:
                event, transcript = ear.listen_cycle(timeout=2.0)
                if event == "DOUBLE_CLAP":
                    console.print("\n[bold green]👏 [Double Clap Detected] Activating ULTRON![/bold green]")
                    set_online_state(True, announce=True)
                    continue
                elif event == "SPEECH" and any(w in transcript.lower() for w in ["ultron", "wake up", "wake", "luffy", "அல்ட்ரான்"]):
                    console.print(f"\n[bold green]🗣️ [Wake Word Detected]: \"{transcript}\"[/bold green]")
                    set_online_state(True, announce=True)
                    continue
                continue

            # 2. When ONLINE: ULTRON is ALWAYS LISTENING to your voice commands and chat!
            # Note: ear.enable_clap_detection is False here, so accidental claps won't interrupt
            event, transcript = ear.listen_cycle(timeout=3.5)

            if event == "SPEECH" and transcript:
                with execution_lock:
                    console.print(f"\n[bold cyan]User (Voice):[/bold cyan] [white]{transcript}[/white]")
                    process_input(transcript, source="Voice")
                    console.print("[bold yellow]ULTRON > [/bold yellow]", end="")

        except Exception as e:
            time.sleep(0.1)

def interactive_terminal():
    """Interactive command-line interface running concurrently with voice listener."""
    console.print("\n[bold cyan]ULTRON Command Center Active.[/bold cyan]")
    console.print("[dim]Double clap to start voice listening, OR type your commands here. Type 'exit' to quit.[/dim]\n")

    while True:
        try:
            cmd = console.input("[bold yellow]ULTRON > [/bold yellow]").strip()
            if not cmd:
                continue
            if cmd.lower() in ["exit", "quit"] and not is_online:
                console.print("[bold red]Shutting down ULTRON...[/bold red]")
                speaker.speak("Shutting down.")
                break

            with execution_lock:
                console.print(f"[bold yellow]User (Type):[/bold yellow] [white]{cmd}[/white]")
                process_input(cmd, source="Type")

        except (KeyboardInterrupt, EOFError):
            break

def on_hotkey_wake():
    """Hotkey (Ctrl+Alt+U) also wakes ULTRON online."""
    set_online_state(True, announce=True)

def main():
    global voice_listener_running
    console.print(Panel.fit(
        "[bold red]U L T R O N[/bold red]\n"
        "[italic white]Personal Autonomous Voice & PC Controller[/italic white]\n"
        "[dim]Double-Clap Wake • Non-Stop Voice Listening • Gemini Brain • ElevenLabs[/dim]",
        border_style="red"
    ))

    # Check key statuses
    if Config.GEMINI_API_KEY:
        console.print("[bold green]Brain: Connected to Google Gemini (High Speed & 37 Direct Tools).[/bold green]")
    elif Config.OPENAI_API_KEY:
        console.print("[bold green]Brain: Connected to OpenAI.[/bold green]")
    else:
        console.print("[yellow]Notice: No cloud brain key set. Running in offline rule-engine fallback mode.[/yellow]")

    if Config.ELEVENLABS_API_KEY:
        console.print("[bold green]Voice: ElevenLabs Neural Engine Active (Female Voice).[/bold green]")
    else:
        console.print("[blue]Voice: Microsoft Edge Neural TTS Active (Ava - Female).[/blue]")

    # Start vision tracking if enabled
    if Config.ENABLE_GESTURES or Config.ENABLE_GAZE:
        console.print("[green]Starting MediaPipe Vision & Gesture tracking...[/green]")
        vision.start()

    # Start hotkey trigger (Ctrl+Alt+U)
    hotkey = HotkeyTrigger(hotkey="ctrl+alt+u", on_trigger=on_hotkey_wake)
    hotkey.start()

    # Start unified voice & double-clap listener thread in standby
    listener_thread = threading.Thread(target=voice_listener_loop, daemon=True, name="UltronVoiceEar")
    listener_thread.start()

    # Initial prompt
    speaker.speak("Ultron ready. Double clap to activate.")

    try:
        interactive_terminal()
    finally:
        voice_listener_running = False
        ear.close()
        vision.stop()
        hotkey.stop()

if __name__ == "__main__":
    if "--ui" in sys.argv or "--desktop" in sys.argv:
        from apps.windows.src.ultron_desktop.app import run_desktop_app
        run_desktop_app()
    else:
        main()
