import {
  FilesetResolver,
  HandLandmarker,
  type NormalizedLandmark,
} from "@mediapipe/tasks-vision";

const WASM_CDN =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm";
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

// Landmark indices (MediaPipe hand model)
const WRIST = 0;
const THUMB_TIP = 4;
const INDEX_TIP = 8;
const MIDDLE_MCP = 9;

// Pinch hysteresis: thumb–index distance relative to hand size
const PINCH_ON = 0.32;
const PINCH_OFF = 0.45;

// How strongly hand movement rotates the orb (radians per normalized unit)
const ROTATE_SPEED = 5.0;
// Smoothing factor for grab-point tracking (0..1, higher = snappier)
const SMOOTHING = 0.4;

export type GestureMode = "idle" | "spin" | "zoom";

export interface TrackerStatus {
  hands: number;
  mode: GestureMode;
}

export interface HandTrackerCallbacks {
  /** Called when a single pinched hand drags: deltas in mirrored normalized coords. */
  onRotate(deltaTheta: number, deltaPhi: number): void;
  /** Called when both hands pinch and spread/close: multiply camera distance by factor. */
  onZoom(factor: number): void;
  onStatus(status: TrackerStatus): void;
}

interface Point {
  x: number;
  y: number;
}

interface HandState {
  pinching: boolean;
  grab: Point; // smoothed pinch midpoint, mirrored
}

export class HandTracker {
  private video: HTMLVideoElement;
  private overlay: HTMLCanvasElement;
  private callbacks: HandTrackerCallbacks;
  private landmarker: HandLandmarker | null = null;
  private stream: MediaStream | null = null;
  private rafId = 0;
  private running = false;
  private lastVideoTime = -1;

  // keyed by handedness label so state survives re-ordering between frames
  private handStates = new Map<string, HandState>();
  private prevMode: GestureMode = "idle";
  private prevSpinGrab: Point | null = null;
  private prevZoomDist: number | null = null;
  private lastStatus: TrackerStatus = { hands: 0, mode: "idle" };

  constructor(
    video: HTMLVideoElement,
    overlay: HTMLCanvasElement,
    callbacks: HandTrackerCallbacks,
  ) {
    this.video = video;
    this.overlay = overlay;
    this.callbacks = callbacks;
  }

  async start(): Promise<void> {
    const isVirtualOrPhone = (label: string) => {
      const l = (label || "").toLowerCase();
      return (
        l.includes("phone link") ||
        l.includes("link to windows") ||
        l.includes("virtual") ||
        l.includes("droidcam") ||
        l.includes("obs") ||
        l.includes("iriun") ||
        l.includes("epoccam") ||
        l.includes("ip camera")
      );
    };

    // 1. Initial media stream request (triggers browser permission if needed)
    let activeStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "user" },
      audio: false,
    });

    const activeTrack = activeStream.getVideoTracks()[0];
    const activeLabel = (activeTrack?.label || "").toLowerCase();
    console.log("[HandTracker] Default camera opened:", activeLabel);

    // 2. If Windows defaulted to Phone Link or a virtual camera, switch to PC physical webcam
    if (isVirtualOrPhone(activeLabel)) {
      console.log("[HandTracker] Detected Phone Link or virtual camera. Searching for physical PC webcam...");
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter((d) => d.kind === "videoinput");
        console.log("[HandTracker] Available cameras:", videoDevices.map((d) => d.label));

        // Prioritize physical/integrated/USB webcam
        const physicalCam = videoDevices.find((d) => {
          const l = (d.label || "").toLowerCase();
          return !isVirtualOrPhone(l);
        });

        if (physicalCam && physicalCam.deviceId) {
          console.log("[HandTracker] Switching to PC webcam:", physicalCam.label);
          activeTrack.stop();
          activeStream = await navigator.mediaDevices.getUserMedia({
            video: {
              deviceId: { exact: physicalCam.deviceId },
              width: 640,
              height: 480,
            },
            audio: false,
          });
        }
      } catch (enumErr) {
        console.warn("[HandTracker] Failed to switch camera:", enumErr);
      }
    }

    this.stream = activeStream;
    this.video.srcObject = this.stream;
    await this.video.play();

    const fileset = await FilesetResolver.forVisionTasks(WASM_CDN);
    const options = {
      baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" as const },
      runningMode: "VIDEO" as const,
      numHands: 2,
      minHandDetectionConfidence: 0.6,
      minHandPresenceConfidence: 0.6,
      minTrackingConfidence: 0.6,
    };
    try {
      this.landmarker = await HandLandmarker.createFromOptions(fileset, options);
    } catch {
      // Some browsers/GPUs reject the GPU delegate — fall back to CPU
      this.landmarker = await HandLandmarker.createFromOptions(fileset, {
        ...options,
        baseOptions: { ...options.baseOptions, delegate: "CPU" as const },
      });
    }

    this.running = true;
    this.loop();
  }

  stop(): void {
    this.running = false;
    cancelAnimationFrame(this.rafId);
    this.landmarker?.close();
    this.landmarker = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.video.srcObject = null;
    this.handStates.clear();
    this.prevMode = "idle";
    this.prevSpinGrab = null;
    this.prevZoomDist = null;
    const ctx = this.overlay.getContext("2d");
    ctx?.clearRect(0, 0, this.overlay.width, this.overlay.height);
    this.emitStatus({ hands: 0, mode: "idle" });
  }

  private loop = () => {
    if (!this.running) return;
    this.rafId = requestAnimationFrame(this.loop);

    if (!this.landmarker || this.video.readyState < 2) return;
    if (this.video.currentTime === this.lastVideoTime) return;
    this.lastVideoTime = this.video.currentTime;

    const result = this.landmarker.detectForVideo(this.video, performance.now());
    this.processHands(result.landmarks, result.handedness.map((h) => h[0]?.categoryName ?? "?"));
    this.drawOverlay(result.landmarks);
  };

  private processHands(
    landmarksList: NormalizedLandmark[][],
    labels: string[],
  ): void {
    const handsCount = landmarksList.length;

    // Update each detected hand's pinch + grab state
    const currentHands: Array<{ label: string; state: HandState }> = [];
    for (let i = 0; i < handsCount; i++) {
      const lm = landmarksList[i];
      // Fall back to index if labels collide
      const label = labels[i] && !currentHands.some((h) => h.label === labels[i])
        ? labels[i]
        : `Hand_${i}`;

      const thumb = lm[THUMB_TIP];
      const index = lm[INDEX_TIP];
      const wrist = lm[WRIST];
      const middleMcp = lm[MIDDLE_MCP];

      // Scale: wrist to middle MCP knuckle distance
      const handScale = Math.hypot(middleMcp.x - wrist.x, middleMcp.y - wrist.y) || 0.1;
      const pinchDist = Math.hypot(thumb.x - index.x, thumb.y - index.y) / handScale;

      const prev = this.handStates.get(label);
      const wasPinching = prev?.pinching ?? false;
      const pinching = wasPinching ? pinchDist < PINCH_OFF : pinchDist < PINCH_ON;

      // Raw midpoint, mirrored in X so it matches user's perspective
      const rawX = 1 - (thumb.x + index.x) * 0.5;
      const rawY = (thumb.y + index.y) * 0.5;

      const grab: Point = prev
        ? {
            x: prev.grab.x + (rawX - prev.grab.x) * SMOOTHING,
            y: prev.grab.y + (rawY - prev.grab.y) * SMOOTHING,
          }
        : { x: rawX, y: rawY };

      const state: HandState = { pinching, grab };
      this.handStates.set(label, state);
      currentHands.push({ label, state });
    }

    // Drop states for hands no longer present
    for (const key of Array.from(this.handStates.keys())) {
      if (!currentHands.some((h) => h.label === key)) {
        this.handStates.delete(key);
      }
    }

    const pinchingHands = currentHands.filter((h) => h.state.pinching);

    // ——— TWO HANDS PINCHING -> ZOOM ———
    if (pinchingHands.length >= 2) {
      const p1 = pinchingHands[0].state.grab;
      const p2 = pinchingHands[1].state.grab;
      const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);

      if (this.prevMode === "zoom" && this.prevZoomDist !== null && this.prevZoomDist > 0.01) {
        // Distance ratio: if hands move apart, dist/prevDist > 1 -> zoom in
        // In our API zoomBy(factor): factor < 1 zooms in (reduces camera distance)
        const ratio = dist / this.prevZoomDist;
        // Dampen the ratio to keep zoom smooth
        const factor = Math.exp(-(ratio - 1) * 1.5);
        this.callbacks.onZoom(factor);
      }
      this.prevZoomDist = dist;
      this.prevSpinGrab = null;
      this.prevMode = "zoom";
      this.emitStatus({ hands: handsCount, mode: "zoom" });
      return;
    }

    // ——— ONE HAND PINCHING -> SPIN ———
    if (pinchingHands.length === 1) {
      const grab = pinchingHands[0].state.grab;

      if (this.prevMode === "spin" && this.prevSpinGrab) {
        const dx = grab.x - this.prevSpinGrab.x;
        const dy = grab.y - this.prevSpinGrab.y;
        this.callbacks.onRotate(dx * ROTATE_SPEED, dy * ROTATE_SPEED);
      }
      this.prevSpinGrab = grab;
      this.prevZoomDist = null;
      this.prevMode = "spin";
      this.emitStatus({ hands: handsCount, mode: "spin" });
      return;
    }

    // ——— IDLE ———
    this.prevSpinGrab = null;
    this.prevZoomDist = null;
    this.prevMode = "idle";
    this.emitStatus({ hands: handsCount, mode: "idle" });
  }

  private drawOverlay(landmarksList: NormalizedLandmark[][]): void {
    const ctx = this.overlay.getContext("2d");
    if (!ctx) return;
    const w = this.overlay.width;
    const h = this.overlay.height;
    ctx.clearRect(0, 0, w, h);

    ctx.save();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(255, 170, 48, 0.4)";
    ctx.fillStyle = "#ffaa30";

    for (const lm of landmarksList) {
      for (const pt of lm) {
        // Mirrored in X to match video mirror
        const x = (1 - pt.x) * w;
        const y = pt.y * h;
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw pinch indicator
      const thumb = lm[THUMB_TIP];
      const index = lm[INDEX_TIP];
      const tx = (1 - thumb.x) * w;
      const ty = thumb.y * h;
      const ix = (1 - index.x) * w;
      const iy = index.y * h;

      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(ix, iy);
      ctx.stroke();
    }
    ctx.restore();
  }

  private emitStatus(status: TrackerStatus): void {
    if (
      status.hands !== this.lastStatus.hands ||
      status.mode !== this.lastStatus.mode
    ) {
      this.lastStatus = status;
      this.callbacks.onStatus(status);
    }
  }
}
