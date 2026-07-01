"""Human RPS gesture recognizers."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..gesture_schema import CameraFrame, GesturePrediction


class HumanGestureRecognizer(ABC):
    @abstractmethod
    def predict(self, frame: CameraFrame) -> GesturePrediction:
        ...


class MockRecognizer(HumanGestureRecognizer):
    """Returns random gestures for testing."""

    def __init__(self, choices: Optional[List[str]] = None):
        self.choices = choices or ["rock", "paper", "scissors"]

    def predict(self, frame: CameraFrame) -> GesturePrediction:
        label = random.choice(self.choices)
        return GesturePrediction(label=label, confidence=0.9)


class KeyboardRecognizer(HumanGestureRecognizer):
    """Reads human gesture from keyboard input for mock mode."""

    def __init__(self, prompt: str = "Your move (r/p/s): "):
        self.prompt = prompt

    def predict(self, frame: CameraFrame) -> GesturePrediction:
        mapping = {"r": "rock", "p": "paper", "s": "scissors"}
        while True:
            try:
                key = input(self.prompt).strip().lower()
            except EOFError:
                return GesturePrediction(label="unknown", confidence=0.0)
            if key in mapping:
                return GesturePrediction(label=mapping[key], confidence=1.0)
            if key == "":
                return GesturePrediction(label="unknown", confidence=0.0)
            print("Invalid input. Use r (rock), p (paper), s (scissors), or Enter (unknown).")


class MediaPipeRecognizer(HumanGestureRecognizer):
    """RGB hand-landmark heuristic recognizer using MediaPipe Hands."""

    LABELS = ["rock", "paper", "scissors", "unknown"]

    def __init__(self, min_confidence: float = 0.65):
        self.min_confidence = min_confidence
        self._hands = None
        self._mp_draw = None

    def _ensure_model(self):
        if self._hands is not None:
            return
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("mediapipe not installed") from exc
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._mp_draw = mp.solutions.drawing_utils

    def predict(self, frame: CameraFrame) -> GesturePrediction:
        try:
            self._ensure_model()
        except RuntimeError:
            return GesturePrediction(label="unknown", confidence=0.0)

        import cv2
        import mediapipe as mp

        image = cv2.cvtColor(frame.color, cv2.COLOR_BGR2RGB)
        results = self._hands.process(image)
        if not results.multi_hand_landmarks:
            return GesturePrediction(label="unknown", confidence=0.0)

        landmarks = results.multi_hand_landmarks[0].landmark
        extended = self._count_extended_fingers(landmarks)
        label, conf = self._heuristic_from_fingers(extended)
        return GesturePrediction(label=label, confidence=conf, landmarks=[(lm.x, lm.y, lm.z) for lm in landmarks])

    @staticmethod
    def _count_extended_fingers(landmarks) -> Dict[str, bool]:
        """Return whether index/middle/ring/pinky are extended."""
        # Tip ids: index=8, middle=12, ring=16, pinky=20; PIP ids: 6,10,14,18
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        extended = {}
        names = ["index", "middle", "ring", "pinky"]
        wrist = landmarks[0]
        for name, tip_id, pip_id in zip(names, tips, pips):
            tip = landmarks[tip_id]
            pip = landmarks[pip_id]
            # simple distance-from-wrist heuristic
            tip_dist = (tip.x - wrist.x) ** 2 + (tip.y - wrist.y) ** 2
            pip_dist = (pip.x - wrist.x) ** 2 + (pip.y - wrist.y) ** 2
            extended[name] = tip_dist > pip_dist
        return extended

    def _heuristic_from_fingers(self, extended: Dict[str, bool]) -> tuple:
        count = sum(extended.values())
        if count >= 4:
            return "paper", 0.9
        if count == 2 and extended.get("index") and extended.get("middle"):
            return "scissors", 0.9
        if count <= 1:
            return "rock", 0.8
        return "unknown", 0.0


def build_recognizer(config: dict) -> HumanGestureRecognizer:
    source = config.get("source", "mock")
    if source == "keyboard":
        return KeyboardRecognizer()
    if source in ("mediapipe", "realsense", "ros2"):
        return MediaPipeRecognizer(min_confidence=float(config.get("min_confidence", 0.65)))
    return MockRecognizer()
