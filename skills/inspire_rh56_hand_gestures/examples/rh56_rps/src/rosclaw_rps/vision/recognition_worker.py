"""Background thread that reads camera frames and runs gesture recognition."""
from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

from ..gesture_schema import CameraFrame, GesturePrediction
from .camera_source import CameraSource
from .hand_gesture_recognizer import HumanGestureRecognizer
from .majority_vote import MajorityVoteBuffer


class RecognitionWorker(threading.Thread):
    """Continuously capture frames and update the vote buffer in the background.

    This decouples the expensive MediaPipe inference from the OpenCV UI loop,
    so the camera feed stays smooth even if recognition runs slower than capture.
    """

    def __init__(
        self,
        camera: CameraSource,
        recognizer: HumanGestureRecognizer,
        vote_buffer: MajorityVoteBuffer,
        process_every_n: int = 2,
        name: str = "recognition-worker",
    ):
        super().__init__(name=name, daemon=True)
        self._camera = camera
        self._recognizer = recognizer
        self._vote = vote_buffer
        self._process_every_n = max(1, process_every_n)
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._latest_frame: Optional[CameraFrame] = None
        self._latest_pred: GesturePrediction = GesturePrediction(label="unknown", confidence=0.0)
        self._frame_counter = 0

    def run(self) -> None:
        while not self._stop_event.is_set():
            frame = self._camera.read()
            if frame is None:
                time.sleep(0.01)
                continue

            with self._lock:
                self._latest_frame = frame

            if self._frame_counter % self._process_every_n == 0:
                pred = self._recognizer.predict(frame)
                with self._lock:
                    self._latest_pred = pred
                    self._vote.update(pred)

            self._frame_counter += 1

    def get_latest(self) -> Tuple[Optional[CameraFrame], GesturePrediction]:
        with self._lock:
            return self._latest_frame, self._latest_pred

    def reset_vote(self) -> None:
        with self._lock:
            self._vote.reset()

    def final_vote(self) -> GesturePrediction:
        with self._lock:
            return self._vote.final()

    def stop(self) -> None:
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=2.0)
