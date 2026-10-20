import { createOrbScene } from "./lib/orbScene";
import "./app/globals.css";

// Declare global QWebChannel from qwebchannel.js
declare const QWebChannel: any;
declare const qt: any;

let ultronBridge: any = null;
let sceneApi: any = null;
const pendingCommands: string[] = [];

// Initialize 3D Holographic Orb
window.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("orb-root");
  if (container) {
    try {
      sceneApi = createOrbScene(container);
      console.log("[Ultron UI] 3D Orb Scene initialized successfully.");
    } catch (err) {
      console.error("[Ultron UI] Failed to initialize Orb Scene:", err);
    }
  }

  // Set up Controls
  document.getElementById("btn-zoom-in")?.addEventListener("click", () => sceneApi?.zoomIn());
  document.getElementById("btn-zoom-out")?.addEventListener("click", () => sceneApi?.zoomOut());
  document.getElementById("btn-reset")?.addEventListener("click", () => sceneApi?.resetView());

  // Set up Stop button
  document.getElementById("btn-stop")?.addEventListener("click", () => {
    if (ultronBridge) {
      ultronBridge.emergency_stop();
    }
    appendLog("SYSTEM", "EMERGENCY STOP TRIGGERED.");
  });

  // Set up Mic / Listen toggle button
  const micBtn = document.getElementById("btn-mic");
  micBtn?.addEventListener("click", () => {
    if (ultronBridge) {
      ultronBridge.toggle_listening();
    } else {
      appendLog("SYSTEM", "PySide6 Desktop Bridge offline. Connect via desktop launcher.");
    }
  });

  // Set up Command Input Form
  const inputForm = document.getElementById("command-form") as HTMLFormElement;
  const commandInput = document.getElementById("command-input") as HTMLInputElement;

  inputForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const cmd = commandInput.value.trim();
    if (!cmd) return;
    executeCommand(cmd);
    commandInput.value = "";
  });

  // Quick Command pills
  document.querySelectorAll(".quick-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      const cmd = pill.getAttribute("data-cmd");
      if (cmd) executeCommand(cmd);
    });
  });

  // Keyboard Shortcuts
  window.addEventListener("keydown", (e) => {
    // Only handle global shortcuts when input is not focused
    if (document.activeElement === commandInput) return;

    switch (e.key) {
      case "+":
      case "=":
        sceneApi?.zoomIn();
        break;
      case "-":
      case "_":
        sceneApi?.zoomOut();
        break;
      case "r":
      case "R":
        sceneApi?.resetView();
        break;
      case " ":
        e.preventDefault();
        micBtn?.click();
        break;
    }
  });

  // Connect to PySide6 QWebChannel
  initWebChannel();
});

function executeCommand(cmd: string) {
  setStatus("THINKING");

  if (ultronBridge) {
    ultronBridge.send_command(cmd);
  } else {
    appendLog("USER", cmd);
    // Queue if bridge is currently handshaking
    console.log("[Ultron UI] Bridge pending, queueing command:", cmd);
    pendingCommands.push(cmd);
    setTimeout(() => {
      if (!ultronBridge) {
        appendLog("ASSISTANT", `Simulated action for: "${cmd}" (Run inside ULTRON desktop app for live PC control).`);
        setStatus("STANDBY");
      }
    }, 2000);
  }
}

function appendLog(sender: string, text: string) {
  const terminal = document.getElementById("hud-terminal");
  if (!terminal) return;

  const row = document.createElement("div");
  row.className = `log-row log-${sender.toLowerCase()}`;

  const timeStr = new Date().toLocaleTimeString("en-GB", { hour12: false });
  row.innerHTML = `<span class="log-time">[${timeStr}]</span> <span class="log-tag">${sender}:</span> <span class="log-msg"></span>`;
  (row.querySelector(".log-msg") as HTMLElement).textContent = text;

  terminal.appendChild(row);
  terminal.scrollTop = terminal.scrollHeight;
}

function setStatus(state: string) {
  const badge = document.getElementById("state-badge");
  if (badge) {
    badge.textContent = state;
    badge.className = `status-pill state-${state.toLowerCase()}`;
  }
}

function initWebChannel() {
  if (typeof qt !== "undefined" && qt.webChannelTransport) {
    new QWebChannel(qt.webChannelTransport, (channel: any) => {
      ultronBridge = channel.objects.ultronBridge;
      console.log("[Ultron UI] QWebChannel connected to desktop bridge.");

      appendLog("SYSTEM", "ULTRON Holographic Desktop Bridge connected.");

      // Flush any queued commands
      while (pendingCommands.length > 0) {
        const queued = pendingCommands.shift();
        if (queued) {
          console.log("[Ultron UI] Dispatching queued command:", queued);
          ultronBridge.send_command(queued);
        }
      }

      // Register callbacks from Python
      ultronBridge.transcript_received.connect((role: string, text: string) => {
        appendLog(role.toUpperCase(), text);
      });

      ultronBridge.state_changed.connect((state: string) => {
        setStatus(state);
      });

      ultronBridge.device_status_updated.connect((pc: string, phone: string, brain: string) => {
        const pcEl = document.getElementById("pill-pc");
        const phoneEl = document.getElementById("pill-phone");
        const brainEl = document.getElementById("pill-brain");

        if (pcEl) pcEl.textContent = pc;
        if (phoneEl) phoneEl.textContent = phone;
        if (brainEl) brainEl.textContent = brain;
      });

      ultronBridge.command_executed.connect((cmd: string, result: string) => {
        console.log(`[Ultron UI] Command finished: ${cmd} -> ${result}`);
      });
    });
  } else {
    console.log("[Ultron UI] WebChannel transport not found; running standalone preview mode.");
  }
}
