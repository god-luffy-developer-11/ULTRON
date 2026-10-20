"""ULTRON Native Desktop Application with Sagar's Holographic 3D Orb UI & Full Main Voice Engine.

Combines the 3D Holographic Orb Interface with:
- Double-Clap Standby Wake Detection & Wake Words (ultron, wake up, luffy, அல்ட்ரான்)
- Non-stop Continuous Voice Listening & Execution
- Voice Sleep / Standby Triggers ("sleep", "go to sleep", "standby", "stop listening")
- Global Wake Hotkey (Ctrl+Alt+U)
- Real-time Console Terminal Input concurrently with the UI
- Total PC and Mobile Master Control via Gemini & Direct Tool Interceptors
"""
import os
import sys
import threading
import time
from pathlib import Path

# Ensure Windows terminal prints Tamil and multilingual characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from rich.console import Console
from rich.panel import Panel

from core.brain import brain
from core.config import Config
from core.ear import ear
from core.speaker import speaker
from triggers.hotkey_trigger import HotkeyTrigger
from tools import pc_control

console = Console()


class UltronWebBridge(QObject):
    """Bidirectional bridge between Desktop Python engine and Holographic Web UI."""

    # Signals emitted from Python to JavaScript
    transcript_received = Signal(str, str)  # role, text
    state_changed = Signal(str)  # 'STANDBY', 'LISTENING', 'THINKING', 'SPEAKING'
    device_status_updated = Signal(str, str, str)  # pc_status, phone_status, brain_status
    command_executed = Signal(str, str)  # command, result

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_state = "STANDBY"

    @Slot(str)
    def send_command(self, text: str):
        """Called by JavaScript or Console when Luffy submits text."""
        clean = (text or "").strip()
        if not clean:
            return
        threading.Thread(target=self._process_command_worker, args=(clean,), daemon=True).start()

    @Slot()
    def toggle_listening(self):
        """Called by JavaScript when Luffy clicks the Mic or Online button."""
        app = UltronDesktopWindow.instance
        if app:
            app.toggle_listening()

    @Slot()
    def emergency_stop(self):
        """Called by JavaScript when STOP button is clicked."""
        speaker.stop()
        self.state_changed.emit("STANDBY")
        self.transcript_received.emit("system", "Emergency stop triggered. Automation halted.")
        console.print("[bold red]⚠️ Emergency Stop Triggered by User.[/bold red]")

    def _process_command_worker(self, text: str):
        clean = text.lower().strip()
        stop_phrases = ["stop", "exit", "quit", "go to sleep", "sleep", "standby", "stop listening", "ultron stop", "turn off"]
        if clean in stop_phrases or clean.rstrip(".!") in stop_phrases:
            app = UltronDesktopWindow.instance
            if app:
                app.set_online_state(False, announce=True)
            return

        wake_phrases = ["wake", "wake up", "online", "start listening"]
        if any(w in clean for w in wake_phrases):
            app = UltronDesktopWindow.instance
            if app:
                app.set_online_state(True, announce=True)
            return

        self.state_changed.emit("THINKING")
        self.transcript_received.emit("user", text)
        console.print(f"\n[bold yellow]User:[/bold yellow] [white]{text}[/white]")

        try:
            reply = brain.process_command(text)
            self.transcript_received.emit("assistant", reply or "Done, Luffy.")
            self.command_executed.emit(text, reply or "Success")
            console.print(f"[bold green]ULTRON:[/bold green] [cyan]{reply}[/cyan]")
        except Exception as e:
            err = f"Execution error: {e}"
            self.transcript_received.emit("system", err)
            console.print(f"[bold red]{err}[/bold red]")
        finally:
            app = UltronDesktopWindow.instance
            if app and app.is_listening:
                self.state_changed.emit("LISTENING")
            else:
                self.state_changed.emit("STANDBY")


class UltronWebPage(QWebEnginePage):
    """Custom WebEnginePage that forwards JavaScript console messages."""

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Filter noisy deprecation warnings
        if "THREE.Clock" in message or "deprecated" in message:
            return
        print(f"[UI JS {level.name}] L{lineNumber}: {message}")


class UltronDesktopWindow(QMainWindow):
    """Main Holographic Desktop Window combining 3D Orb UI and Main Voice Engine."""

    instance = None

    def __init__(self):
        super().__init__()
        UltronDesktopWindow.instance = self

        self.setWindowTitle("ULTRON — Holographic AI Operator // Master Control")
        self.resize(1280, 800)
        self.setMinimumSize(960, 640)

        # Assets & UI path
        self.ui_dir = PROJECT_ROOT / "apps" / "windows" / "src" / "ultron_desktop" / "ui" / "dist"
        self.index_html = self.ui_dir / "index.html"

        # WebEngine setup
        try:
            import psutil
            psutil.cpu_percent(None)
        except Exception:
            pass

        self.view = QWebEngineView(self)
        self.page = UltronWebPage(self.view)
        self.view.setPage(self.page)

        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)

        # WebChannel bridge
        self.channel = QWebChannel(self.page)
        self.bridge = UltronWebBridge(self)
        self.channel.registerObject("ultronBridge", self.bridge)
        self.page.setWebChannel(self.channel)

        # Grant webcam and audio permissions for hand tracking
        self.page.featurePermissionRequested.connect(self._handle_permission_request)

        self.setCentralWidget(self.view)

        # Load UI
        if self.index_html.exists():
            self.view.load(QUrl.fromLocalFile(str(self.index_html)))
        else:
            self.view.setHtml("<h1>Error: UI bundle not found</h1>")

        # Initial telemetry push once page loads
        self.view.loadFinished.connect(lambda ok: QTimer.singleShot(600, self._push_telemetry))

        # Online / Standby state tracking (matching main.py behavior)
        self.is_listening = True  # Starts ready to accept commands
        ear.enable_clap_detection = False
        self.voice_thread = None
        self._start_voice_monitor()

        # Global Hotkey (Ctrl+Alt+U) to toggle listening/standby
        try:
            self.hotkey = HotkeyTrigger(hotkey="ctrl+alt+u", on_trigger=self.toggle_listening)
            self.hotkey.start()
        except Exception as e:
            print(f"[Hotkey] Notice: {e}")

        # Telemetry timer
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._push_telemetry)
        self.telemetry_timer.start(3000)

        # Interactive Terminal thread
        self._start_terminal_cli()

    def _handle_permission_request(self, security_origin, feature):
        """Auto-grant webcam permission for MediaPipe 3D Orb hand gesture control."""
        self.page.setFeaturePermission(
            security_origin,
            feature,
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
        )

    def set_online_state(self, online: bool, announce: bool = True):
        """Switch between Standby (clap detection ON) and Active (voice chat ON, clap detection OFF)."""
        self.is_listening = online
        ear.enable_clap_detection = not online

        state = "LISTENING" if online else "STANDBY"
        self.bridge.state_changed.emit(state)

        if online:
            msg = "Ultron online. I am listening, Luffy."
            if announce:
                speaker.speak(msg)
            self.bridge.transcript_received.emit("system", msg)
            console.print("\n[bold green]===============================================================[/bold green]")
            console.print("[bold green]>>> ULTRON IS ONLINE & ALWAYS LISTENING FOR LUFFY! <<<[/bold green]")
            console.print("[dim]Tamil & English voice modes active. Double-clap paused while online.[/dim]")
            console.print("[dim]Listening stays on until you say 'stop' or 'sleep'.[/dim]")
            console.print("[bold green]===============================================================[/bold green]\n")
        else:
            msg = "Listening stopped, Luffy. Double clap to wake me."
            if announce:
                speaker.speak(msg)
            self.bridge.transcript_received.emit("system", msg)
            console.print("\n[dim]ULTRON is in standby. Double clap or say 'Ultron' to activate.[/dim]\n")

    def toggle_listening(self):
        """Toggle between Active Listening and Standby."""
        self.set_online_state(not self.is_listening, announce=True)

    def _start_voice_monitor(self):
        """Dedicated audio listener thread supporting Double-Clap wake & continuous multi-turn commands."""
        def ear_worker():
            try:
                ear._load_model()
            except Exception as e:
                console.print(f"[red]Could not load Whisper model: {e}[/red]")

            stop_phrases = ["stop", "exit", "quit", "go to sleep", "sleep", "standby", "stop listening", "ultron stop", "turn off"]
            wake_phrases = ["ultron", "wake up", "wake", "luffy", "அல்ட்ரான்"]

            while True:
                try:
                    if self.is_listening:
                        event, transcript = ear.listen_cycle(timeout=3.5)
                        if event == "SPEECH" and transcript:
                            clean = transcript.lower().strip()
                            # Check if user told ULTRON to go to sleep
                            if clean in stop_phrases or clean.rstrip(".!") in stop_phrases:
                                self.set_online_state(False, announce=True)
                                continue

                            console.print(f"\n[bold cyan]User (Voice):[/bold cyan] [white]{transcript}[/white]")
                            self.bridge.transcript_received.emit("user", transcript)
                            self.bridge.state_changed.emit("THINKING")

                            reply = brain.process_command(transcript)

                            self.bridge.transcript_received.emit("assistant", reply or "Done, Luffy.")
                            console.print(f"[bold green]ULTRON:[/bold green] [cyan]{reply}[/cyan]")

                            if self.is_listening:
                                self.bridge.state_changed.emit("LISTENING")
                    else:
                        # STANDBY: Listen for Double-Clap or wake words
                        event, transcript = ear.listen_cycle(timeout=2.0)
                        if event == "DOUBLE_CLAP":
                            console.print("\n[bold green]👏 [Double Clap Detected] Activating ULTRON![/bold green]")
                            self.set_online_state(True, announce=True)
                            continue
                        elif event == "SPEECH" and any(w in transcript.lower() for w in wake_phrases):
                            console.print(f"\n[bold green]🗣️ [Wake Word Detected]: \"{transcript}\"[/bold green]")
                            self.set_online_state(True, announce=True)
                            continue

                except Exception as ex:
                    time.sleep(0.3)

        self.voice_thread = threading.Thread(target=ear_worker, daemon=True, name="UltronCombinedEarWorker")
        self.voice_thread.start()

    def closeEvent(self, event):
        """Clean shutdown on window close."""
        if hasattr(self, "hotkey"):
            self.hotkey.stop()
        ear.close()
        event.accept()

    def _start_terminal_cli(self):
        """Allows typing commands directly in the terminal while UI is running."""
        def cli_worker():
            if not sys.stdin or not sys.stdin.isatty():
                return
            time.sleep(2.0)
            console.print("\n[bold cyan]Interactive Terminal CLI Active.[/bold cyan]")
            console.print("[dim]Type your commands below, speak aloud, or click on the 3D Desktop UI:[/dim]\n")

            while True:
                try:
                    cmd = console.input("[bold yellow]ULTRON > [/bold yellow]").strip()
                    if not cmd:
                        continue
                    self.bridge.send_command(cmd)
                except (KeyboardInterrupt, EOFError):
                    break
                except Exception:
                    time.sleep(0.5)

        t = threading.Thread(target=cli_worker, daemon=True, name="UltronTerminalCLI")
        t.start()

    def _push_telemetry(self):
        """Periodically update UI with PC hardware & device status."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            pc_stat = f"PC: CPU {cpu:.0f}% · RAM {ram:.0f}%"

            from tools import phone_control
            phone_stat = "PHONE: " + ("CONNECTED" if phone_control.phone.is_connected else "DISCONNECTED")

            brain_stat = "GEMINI 3.8 ONLINE" if Config.GEMINI_API_KEY else "OFFLINE RULE ENGINE"
            self.bridge.device_status_updated.emit(pc_stat, phone_stat, brain_stat)
        except Exception:
            pass


def run_desktop_app():
    """Combined Entry Point: 3D Holographic Desktop Window + Full ULTRON Engine."""
    console.print(Panel.fit(
        "[bold red]U L T R O N[/bold red]\n"
        "[italic white]Personal Autonomous Voice, Holographic 3D UI & PC Operator[/italic white]\n"
        "[dim]3D Orb UI • Double-Clap Wake • Non-Stop Voice • Hand Gestures • Gemini Brain[/dim]",
        border_style="red"
    ))

    # Print connection statuses
    if Config.GEMINI_API_KEY:
        console.print("[bold green]Brain: Connected to Google Gemini (High Speed & 37 Direct Tools).[/bold green]")
    console.print("[dim]Languages: English and Tamil | Owner: Luffy[/dim]\n")

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("ULTRON")
    app.setOrganizationName("Luffy")

    win = UltronDesktopWindow()
    win.show()

    # Initial voice announcement
    QTimer.singleShot(1500, lambda: speaker.speak("Ultron holographic operator online. I am listening, Luffy."))

    sys.exit(app.exec())


if __name__ == "__main__":
    run_desktop_app()
