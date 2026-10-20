"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createOrbScene, type OrbSceneApi } from "@/lib/orbScene";
import { HandTracker, type TrackerStatus } from "@/lib/handTracker";

type CameraState = "off" | "starting" | "on" | "error";

interface SystemStatus {
  emergency_stop: boolean;
  pc: {
    cpu_percent: number;
    ram_percent: number;
    info: string;
  };
  phone: {
    connected: boolean;
    status_text: string;
  };
}

interface FeedLog {
  id: string;
  type: "user" | "ultron" | "sys";
  text: string;
  time: string;
}

const MODE_LABEL: Record<TrackerStatus["mode"], string> = {
  idle: "STANDBY",
  spin: "SPIN",
  zoom: "ZOOM",
};

const API_BASE = "http://127.0.0.1:8000";

const QUICK_ACTIONS = [
  "Open Notepad & write an essay about AI in 100 words",
  "Test all apps in my PC",
  "Open camera and take a picture",
  "Open Clock and set alarm at 5:30am",
  "Open WhatsApp and send message to Rudra: Ultron online",
  "Calculate 125 * 8",
];

export default function JarvisOrb() {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<OrbSceneApi | null>(null);
  const trackerRef = useRef<HandTracker | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);

  const [camera, setCamera] = useState<CameraState>("off");
  const [status, setStatus] = useState<TrackerStatus>({ hands: 0, mode: "idle" });
  const [error, setError] = useState<string | null>(null);

  // ULTRON Backend & Command HUD states
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [sysStatus, setSysStatus] = useState<SystemStatus | null>(null);
  const [commandText, setCommandText] = useState<string>("");
  const [isTransmitting, setIsTransmitting] = useState<boolean>(false);
  const [feedLogs, setFeedLogs] = useState<FeedLog[]>([
    {
      id: "init",
      type: "sys",
      text: "U.L.T.R.O.N. Autonomous Cross-Device AI Core Initialized.",
      time: new Date().toLocaleTimeString(),
    },
  ]);

  // Three.js Orb initialization
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const scene = createOrbScene(container);
    sceneRef.current = scene;
    return () => {
      trackerRef.current?.stop();
      trackerRef.current = null;
      scene.dispose();
      sceneRef.current = null;
    };
  }, []);

  // Poll ULTRON backend status
  useEffect(() => {
    let active = true;

    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/system/status`, { signal: AbortSignal.timeout(2500) });
        if (res.ok) {
          const data = (await res.json()) as SystemStatus;
          if (active) {
            setBackendOnline(true);
            setSysStatus(data);
          }
        } else {
          if (active) setBackendOnline(false);
        }
      } catch {
        if (active) setBackendOnline(false);
      }
    };

    void checkStatus();
    const interval = setInterval(checkStatus, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Scroll feed to bottom on new log
  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feedLogs]);

  const addLog = (type: FeedLog["type"], text: string) => {
    setFeedLogs((prev) => [
      ...prev.slice(-30),
      {
        id: Math.random().toString(36).substring(2, 9),
        type,
        text,
        time: new Date().toLocaleTimeString(),
      },
    ]);
  };

  const handleSendCommand = async (cmd: string) => {
    const clean = cmd.trim();
    if (!clean || isTransmitting) return;

    setCommandText("");
    setIsTransmitting(true);
    addLog("user", `> ${clean}`);

    try {
      const res = await fetch(`${API_BASE}/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: clean, user: "Luffy" }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const msg = (errData as { detail?: string }).detail || `HTTP Error ${res.status}`;
        addLog("sys", `[ERROR] ${msg}`);
      } else {
        const data = (await res.json()) as { reply?: string };
        addLog("ultron", data.reply || "Action completed, Luffy.");
      }
    } catch (e) {
      addLog("sys", `[DISPATCH FAILED] Could not reach backend: ${String(e)}`);
    } finally {
      setIsTransmitting(false);
    }
  };

  const handleEmergencyStop = async () => {
    try {
      addLog("sys", "EMERGENCY STOP TRIGGERED BY USER.");
      await fetch(`${API_BASE}/emergency-stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "UI Emergency Stop Button", user: "Luffy" }),
      });
      setSysStatus((prev) => (prev ? { ...prev, emergency_stop: true } : null));
    } catch (e) {
      addLog("sys", `Emergency stop failed: ${String(e)}`);
    }
  };

  const handleEmergencyResume = async () => {
    try {
      addLog("sys", "EMERGENCY STOP CLEARED.");
      await fetch(`${API_BASE}/emergency-stop/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user: "Luffy" }),
      });
      setSysStatus((prev) => (prev ? { ...prev, emergency_stop: false } : null));
    } catch (e) {
      addLog("sys", `Resume failed: ${String(e)}`);
    }
  };

  const stopGestures = useCallback(() => {
    trackerRef.current?.stop();
    trackerRef.current = null;
    setCamera("off");
    setStatus({ hands: 0, mode: "idle" });
  }, []);

  const startGestures = useCallback(async () => {
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video || !overlay || trackerRef.current) return;

    setCamera("starting");
    setError(null);

    const tracker = new HandTracker(video, overlay, {
      onRotate: (dt, dp) => sceneRef.current?.rotateBy(dt, dp),
      onZoom: (factor) => sceneRef.current?.zoomBy(factor),
      onStatus: setStatus,
    });
    trackerRef.current = tracker;

    try {
      await tracker.start();
      setCamera("on");
    } catch (err) {
      trackerRef.current = null;
      tracker.stop();
      setCamera("error");
      setError(
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "CAMERA ACCESS DENIED"
          : "TRACKING INIT FAILED",
      );
    }
  }, []);

  const toggleGestures = useCallback(() => {
    if (trackerRef.current) stopGestures();
    else void startGestures();
  }, [startGestures, stopGestures]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Don't intercept shortcut keys when typing inside command input
      if (document.activeElement?.tagName === "INPUT") return;

      switch (e.key) {
        case "+":
        case "=":
          sceneRef.current?.zoomIn();
          break;
        case "-":
        case "_":
          sceneRef.current?.zoomOut();
          break;
        case "r":
        case "R":
          sceneRef.current?.resetView();
          break;
        case "g":
        case "G":
          toggleGestures();
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleGestures]);

  const cameraOn = camera === "on";
  const isEStopActive = sysStatus?.emergency_stop ?? false;

  return (
    <>
      <div ref={containerRef} className="orb-root" />

      <div className="overlay-vignette" />
      <div className="overlay-grain" />
      <div className="overlay-scanlines" />

      {/* ——— TOP HEADER & TELEMETRY HUD ——— */}
      <header className="hud-header">
        <div className="hud-title" style={{ position: "static" }}>
          U.L.T.R.O.N.
        </div>

        <div className="hud-badges">
          <div className={`hud-badge ${backendOnline ? "online" : "offline"}`}>
            BACKEND: {backendOnline ? "ONLINE" : "OFFLINE"}
          </div>

          {sysStatus && (
            <>
              <div className="hud-badge">
                PC: {Math.round(sysStatus.pc.cpu_percent)}% CPU · {Math.round(sysStatus.pc.ram_percent)}% RAM
              </div>
              <div className={`hud-badge ${sysStatus.phone.connected ? "online" : "offline"}`}>
                PHONE: {sysStatus.phone.connected ? "CONNECTED" : "OFFLINE"}
              </div>
            </>
          )}

          <button
            type="button"
            className="hud-estop-btn"
            onClick={isEStopActive ? handleEmergencyResume : handleEmergencyStop}
          >
            {isEStopActive ? "RESUME" : "EMERGENCY STOP"}
          </button>
        </div>
      </header>

      {/* Emergency Stop Active Alert Banner */}
      {isEStopActive && (
        <div className="hud-estop-banner">
          <span>⚠️ EMERGENCY STOP ACTIVE — ALL AUTOMATION HALTED</span>
          <button type="button" className="hud-resume-btn" onClick={handleEmergencyResume}>
            RESUME AUTOMATION
          </button>
        </div>
      )}

      {/* ——— INTERACTIVE COMMAND CONSOLE ——— */}
      <div className="hud-console">
        <div className="hud-feed">
          {feedLogs.map((log) => (
            <div key={log.id} className={`hud-log-${log.type}`}>
              <span style={{ opacity: 0.5, marginRight: "6px" }}>[{log.time}]</span>
              {log.text}
            </div>
          ))}
          <div ref={feedEndRef} />
        </div>

        <div className="hud-chips">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action}
              type="button"
              className="hud-chip"
              onClick={() => handleSendCommand(action)}
              disabled={isTransmitting || isEStopActive}
            >
              {action}
            </button>
          ))}
        </div>

        <form
          className="hud-input-row"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSendCommand(commandText);
          }}
        >
          <input
            type="text"
            className="hud-input"
            value={commandText}
            onChange={(e) => setCommandText(e.target.value)}
            placeholder={
              isEStopActive
                ? "Emergency Stop active..."
                : isTransmitting
                ? "Ultron executing..."
                : "Enter command for PC or Phone (or use voice)..."
            }
            disabled={isTransmitting || isEStopActive}
          />
          <button
            type="submit"
            className="hud-transmit-btn"
            disabled={isTransmitting || isEStopActive || !commandText.trim()}
          >
            {isTransmitting ? "TRANSMITTING…" : "TRANSMIT"}
          </button>
        </form>
      </div>

      {/* ——— NAVIGATION & SHORTCUT HINTS ——— */}
      <div className="hud hud-hint">
        <div>
          <span className="key">DRAG</span> spin&nbsp;&nbsp;
          <span className="key">SCROLL</span> zoom
        </div>
        {cameraOn ? (
          <div>
            <span className="key">PINCH + MOVE</span> spin&nbsp;&nbsp;
            <span className="key">PINCH BOTH HANDS ± SPREAD</span> zoom
          </div>
        ) : (
          <div>
            <span className="key">G</span> hand gestures&nbsp;&nbsp;
            <span className="key">R</span> reset&nbsp;&nbsp;
            <span className="key">+/−</span> zoom
          </div>
        )}
      </div>

      {/* ——— CAMERA & CONTROLS HUD ——— */}
      <div className="hud hud-controls">
        <div className={`camera-panel${cameraOn ? " visible" : ""}`}>
          <video ref={videoRef} muted playsInline className="camera-video" />
          <canvas ref={overlayRef} width={208} height={156} className="camera-overlay" />
          <div className="camera-status">
            {status.hands > 0
              ? `${status.hands} HAND${status.hands > 1 ? "S" : ""} · ${MODE_LABEL[status.mode]}`
              : "SHOW HANDS"}
          </div>
        </div>

        {error && <div className="hud-error">{error}</div>}

        <div className="hud-row">
          <button
            type="button"
            className="hud-btn"
            aria-pressed={cameraOn}
            onClick={toggleGestures}
            disabled={camera === "starting"}
          >
            {camera === "starting" ? "INITIALIZING…" : cameraOn ? "GESTURES ON" : "GESTURES OFF"}
          </button>
        </div>
        <div className="hud-row">
          <button type="button" className="hud-btn" onClick={() => sceneRef.current?.zoomIn()} aria-label="Zoom in">
            +
          </button>
          <button type="button" className="hud-btn" onClick={() => sceneRef.current?.zoomOut()} aria-label="Zoom out">
            −
          </button>
          <button type="button" className="hud-btn" onClick={() => sceneRef.current?.resetView()}>
            RESET
          </button>
        </div>
      </div>
    </>
  );
}
