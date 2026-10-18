"""Camera vision, hand gesture tracking, head and gaze tracking with MediaPipe and OpenCV."""
import threading
import time
import math
import numpy as np
from core.config import Config

class VisionTracker:
    def __init__(self, camera_index: int = None):
        self.camera_index = camera_index if camera_index is not None else Config.CAMERA_INDEX
        self.running = False
        self.thread = None
        self.last_gesture = "none"
        self.last_head_pose = "neutral"
        self.last_eye_gaze = "center"
        self.last_frame_time = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _run_loop(self):
        try:
            import cv2
            import mediapipe as mp
        except ImportError:
            print("[Vision] opencv-python or mediapipe not installed. Vision tracking disabled.")
            self.running = False
            return

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"[Vision] Could not open camera {self.camera_index}.")
            self.running = False
            return

        mp_hands = mp.solutions.hands
        mp_face_mesh = mp.solutions.face_mesh

        hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.5)
        face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.6)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape

            # Hand gesture analysis
            if Config.ENABLE_GESTURES:
                hand_results = hands.process(frame_rgb)
                if hand_results.multi_hand_landmarks:
                    for lm in hand_results.multi_hand_landmarks:
                        self.last_gesture = self._detect_hand_gesture(lm.landmark)
                else:
                    self.last_gesture = "none"

            # Face & Gaze analysis
            if Config.ENABLE_GAZE:
                face_results = face_mesh.process(frame_rgb)
                if face_results.multi_face_landmarks:
                    for flm in face_results.multi_face_landmarks:
                        self.last_head_pose, self.last_eye_gaze = self._detect_face_pose_and_gaze(flm.landmark, w, h)
                else:
                    self.last_head_pose = "none"
                    self.last_eye_gaze = "none"

            self.last_frame_time = time.time()
            time.sleep(0.03)

        cap.release()
        hands.close()
        face_mesh.close()

    def _detect_hand_gesture(self, landmarks) -> str:
        # Landmark indices: Thumb 4, Index 8, Middle 12, Ring 16, Pinky 20, Wrist 0
        tips = [8, 12, 16, 20]
        extended = []
        for tip in tips:
            # Tip is higher (smaller y) than PIP joint (tip - 2)
            if landmarks[tip].y < landmarks[tip - 2].y:
                extended.append(tip)

        # Palm open: all 4 fingers extended
        if len(extended) == 4:
            return "open_palm"
        # Fist: 0 fingers extended
        elif len(extended) == 0:
            return "fist"
        # Pointing index: only index extended
        elif extended == [8]:
            return "point"
        # Peace / victory: index + middle extended
        elif extended == [8, 12]:
            return "peace"
        # Thumbs up: thumb above index, other fingers closed
        elif len(extended) == 0 and landmarks[4].y < landmarks[3].y:
            return "thumbs_up"
        return "other"

    def _detect_face_pose_and_gaze(self, landmarks, width: int, height: int):
        # Nose tip: 1, Left face: 234, Right face: 454, Chin: 152, Forehead: 10
        nose = landmarks[1]
        left = landmarks[234]
        right = landmarks[454]
        
        # Horizontal ratio for yaw
        dist_left = abs(nose.x - left.x)
        dist_right = abs(right.x - nose.x)
        ratio = dist_left / (dist_right + 1e-6)

        pose = "facing_forward"
        if ratio < 0.6:
            pose = "looking_right"
        elif ratio > 1.6:
            pose = "looking_left"

        # Iris centers from refined landmarks: Left iris: 468, Right iris: 473
        gaze = "center"
        if len(landmarks) > 473:
            left_iris = landmarks[468]
            left_eye_inner = landmarks[133]
            left_eye_outer = landmarks[33]
            eye_width = abs(left_eye_inner.x - left_eye_outer.x)
            if eye_width > 0:
                pos = (left_iris.x - left_eye_outer.x) / eye_width
                if pos < 0.4:
                    gaze = "left"
                elif pos > 0.6:
                    gaze = "right"

        return pose, gaze

    def get_vision_state(self) -> dict:
        return {
            "hand_gesture": self.last_gesture,
            "head_pose": self.last_head_pose,
            "eye_gaze": self.last_eye_gaze,
            "active": self.running
        }

vision = VisionTracker()
