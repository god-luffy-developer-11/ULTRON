"""ULTRON Native Desktop Application with Sagar's Holographic 3D Orb UI.

Embeds Three.js holographic orb and connects to ULTRON Brain, Voice Ear,
ElevenLabs/Edge TTS, System Diagnostics, and Total PC/Mobile Automation.
"""
import os
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.brain import brain
from core.config import Config
from core.ear import ear
from core.speaker import speaker
from tools import pc_control


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
        """Called by JavaScript when Luffy submits text in the UI."""
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

    def _process_command_worker(self, text: str):
        self.state_changed.emit("THINKING")
        self.transcript_received.emit("user", text)
        try:
            reply = brain.process_command(text)
            self.transcript_received.emit("assistant", reply or "Done, Luffy.")
            self.command_executed.emit(text, reply or "Success")
        except Exception as e:
            err = f"Execution error: {e}"
            self.transcript_received.emit("system", err)
        finally:
            self.state_changed.emit("STANDBY")


class UltronWebPage(QWebEnginePage):
    """Custom WebEnginePage that forwards JavaScript console messages."""

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[Desktop UI JS {level.name}] L{lineNumber}: {message}")


class UltronDesktopWindow(QMainWindow):
    """Main Holographic Desktop Window for ULTRON."""

    instance = None

    def __init__(self):
        super().__init__()
        UltronDesktopWindow.instance = self

        self.setWindowTitle("ULTRON — Personal Autonomous AI Operator")
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
        self.view.loadFinished.connect(lambda ok: QTimer.singleShot(500, self._push_telemetry))

        # Background Voice loop monitor
        self.is_listening = True
        self.voice_thread = None
        self._start_voice_monitor()

        # Telemetry timer
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._push_telemetry)
        self.telemetry_timer.start(3000)

    def _handle_permission_request(self, security_origin, feature):
        """Auto-grant webcam permission for MediaPipe 3D Orb hand gesture control."""
        print(f"[Desktop WebEngine] Auto-granting permission {feature} to {security_origin}")
        self.page.setFeaturePermission(
            security_origin,
            feature,
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
        )

    def _start_voice_monitor(self):
        """Starts ear listener in background thread."""
        def ear_worker():
            try:
                ear._load_model()
            except Exception as e:
                print(f"[Ear Worker] Model load notice: {e}")

            while True:
                try:
                    if self.is_listening:
                        self.bridge.state_changed.emit("LISTENING")
                        event, transcript = ear.listen_cycle(timeout=3.0)
                        if event == "SPEECH" and transcript:
                            print(f"[Voice] Transcript: {transcript}")
                            self.bridge.transcript_received.emit("user", transcript)
                            self.bridge.state_changed.emit("THINKING")
                            reply = brain.process_command(transcript)
                            self.bridge.transcript_received.emit("assistant", reply or "Done, Luffy.")
                            self.bridge.state_changed.emit("STANDBY")
                    else:
                        # Standby double-clap wake detection
                        event, transcript = ear.listen_cycle(timeout=2.0)
                        if event == "DOUBLE_CLAP" or (event == "SPEECH" and any(w in transcript.lower() for w in ["ultron", "wake up", "luffy"])):
                            print("[Voice] Wake trigger detected!")
                            self.is_listening = True
                            self.bridge.state_changed.emit("LISTENING")
                            speaker.speak("Ultron online. I am listening, Luffy.")
                except Exception as ex:
                    time.sleep(0.5)

        self.voice_thread = threading.Thread(target=ear_worker, daemon=True, name="UltronDesktopEar")
        self.voice_thread.start()

    def toggle_listening(self):
        self.is_listening = not self.is_listening
        state = "LISTENING" if self.is_listening else "STANDBY"
        self.bridge.state_changed.emit(state)
        msg = "Ultron listening online." if self.is_listening else "Listening paused. Standby."
        speaker.speak(msg)
        self.bridge.transcript_received.emit("system", msg)

    def _push_telemetry(self):
        """Periodically update UI with PC hardware & device status."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            pc_stat = f"PC: CPU {cpu:.0f}% · RAM {ram:.0f}%"

            # Check phone connection via adb
            from tools import phone_control
            phone_stat = "PHONE: " + ("CONNECTED" if phone_control.phone.is_connected else "DISCONNECTED")

            brain_stat = "GEMINI 3.8 ONLINE" if Config.GEMINI_API_KEY else "OFFLINE RULE ENGINE"
            self.bridge.device_status_updated.emit(pc_stat, phone_stat, brain_stat)
        except Exception:
            pass


def run_desktop_app():
    """Entry point for native desktop application."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set application metadata
    app.setApplicationName("ULTRON")
    app.setOrganizationName("Luffy")

    win = UltronDesktopWindow()
    win.show()

    # Initial greeting
    QTimer.singleShot(1500, lambda: speaker.speak("Ultron holographic interface loaded."))

    sys.exit(app.exec())


if __name__ == "__main__":
    run_desktop_app()
