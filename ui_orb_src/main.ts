import { createOrbScene, type OrbSceneApi } from "./lib/orbScene";
import { HandTracker, type TrackerStatus } from "./lib/handTracker";
import "./app/globals.css";

// Declare global QWebChannel from qwebchannel.js
declare const QWebChannel: any;
declare const qt: any;

let ultronBridge: any = null;
let sceneApi: OrbSceneApi | null = null;
let tracker: HandTracker | null = null;
let cameraActive = false;
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

  // Set up View Controls
  document.getElementById("btn-zoom-in")?.addEventListener("click", () => sceneApi?.zoomIn());
  document.getElementById("btn-zoom-out")?.addEventListener("click", () => sceneApi?.zoomOut());
  document.getElementById("btn-reset")?.addEventListener("click", () => sceneApi?.resetView());

  // Set up Hand Tracking Gesture toggle
  const gesturesBtn = document.getElementById("btn-gestures") as HTMLButtonElement;
  gesturesBtn?.addEventListener("click", () => toggleHandGestures());

  // Set up Stop button
  document.getElementById("btn-stop")?.addEventListener("click", () => {
    if (ultronBridge) {
      ultronBridge.emergency_stop();
    }
    showToast("EMERGENCY STOP TRIGGERED");
  });

  // Set up Mic / Listen toggle button
  const micBtn = document.getElementById("btn-mic");
  micBtn?.addEventListener("click", () => {
    if (ultronBridge) {
      ultronBridge.toggle_listening();
    } else {
      showToast("PySide6 Desktop Bridge offline.");
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
      case "g":
      case "G":
        toggleHandGestures();
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

async function toggleHandGestures() {
  const gesturesBtn = document.getElementById("btn-gestures") as HTMLButtonElement;
  const video = document.getElementById("camera-video") as HTMLVideoElement;
  const overlay = document.getElementById("camera-overlay") as HTMLCanvasElement;

  if (cameraActive) {
    tracker?.stop();
    tracker = null;
    cameraActive = false;
    if (gesturesBtn) {
      gesturesBtn.textContent = "GESTURES OFF";
      gesturesBtn.setAttribute("aria-pressed", "false");
    }
    setStatus("STANDBY");
    showToast("Hand tracking stopped");
  } else {
    if (!video || !overlay) return;
    if (gesturesBtn) gesturesBtn.textContent = "CONNECTING CAM…";

    try {
      tracker = new HandTracker(video, overlay, {
        onRotate: (dt, dp) => sceneApi?.rotateBy(dt, dp),
        onZoom: (factor) => sceneApi?.zoomBy(factor),
        onStatus: (st) => {
          if (st.mode !== "idle") {
            setStatus(st.mode === "spin" ? "SPINNING" : "ZOOMING");
          } else {
            setStatus("GESTURES ON");
          }
        },
      });

      await tracker.start();
      cameraActive = true;
      if (gesturesBtn) {
        gesturesBtn.textContent = "GESTURES ON";
        gesturesBtn.setAttribute("aria-pressed", "true");
      }
      setStatus("GESTURES ON");
      showToast("PC Default Camera Active: Pinch & Move to control Orb");
    } catch (err: any) {
      console.error("[Ultron Hand Tracking] Failed to start:", err);
      tracker = null;
      cameraActive = false;
      if (gesturesBtn) {
        gesturesBtn.textContent = "GESTURES OFF";
        gesturesBtn.setAttribute("aria-pressed", "false");
      }
      showToast(err?.name === "NotAllowedError" ? "Camera access denied" : "PC Camera not found");
    }
  }
}

function executeCommand(cmd: string) {
  setStatus("THINKING");
  showToast(`Executing: "${cmd}"`);

  if (ultronBridge) {
    ultronBridge.send_command(cmd);
  } else {
    console.log("[Ultron UI] Bridge pending, queueing command:", cmd);
    pendingCommands.push(cmd);
    setTimeout(() => {
      if (!ultronBridge) {
        showToast(`Simulated: "${cmd}"`);
        setStatus("STANDBY");
      }
    }, 2000);
  }
}

function showToast(message: string) {
  let toast = document.getElementById("hud-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "hud-toast";
    toast.className = "hud-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout((toast as any)._timeout);
  (toast as any)._timeout = setTimeout(() => {
    toast?.classList.remove("show");
  }, 3500);
}

let lastState = "";
function setStatus(state: string) {
  if (state === lastState) return;
  lastState = state;
  const badge = document.getElementById("state-badge");
  if (badge) {
    badge.textContent = state;
    badge.className = `status-pill state-${state.toLowerCase().replace(/\s+/g, "-")}`;
  }
}

function initWebChannel() {
  if (typeof qt !== "undefined" && qt.webChannelTransport) {
    new QWebChannel(qt.webChannelTransport, (channel: any) => {
      ultronBridge = channel.objects.ultronBridge;
      console.log("[Ultron UI] QWebChannel connected to desktop bridge.");

      showToast("ULTRON Desktop Bridge Connected");

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
        if (role === "assistant" || role === "system") {
          showToast(text);
        }
      });

      ultronBridge.state_changed.connect((state: string) => {
        if (!cameraActive || state === "THINKING" || state === "LISTENING") {
          setStatus(state);
        }
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
