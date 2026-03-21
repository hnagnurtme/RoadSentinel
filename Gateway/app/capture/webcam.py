"""
webcam.py – Capture frames from a local webcam.

Yields frames one at a time via a blocking iterator.
Thread-safe: a background thread fills a queue so the main loop
never blocks waiting for the camera.
"""

import queue
import threading
import time

import cv2
import numpy as np

from app.utils.config import CaptureConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebcamCapture:
    """Captures frames from a USB/built-in webcam in a background thread."""

    def __init__(self, cfg: CaptureConfig) -> None:
        self._cfg = cfg
        self._cap: cv2.VideoCapture | None = None
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open the camera and start the background capture thread."""
        self._cap = cv2.VideoCapture(self._cfg.webcam_index)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Cannot open webcam (index={self._cfg.webcam_index})"
            )
        logger.info("Webcam opened (index=%d)", self._cfg.webcam_index)

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="WebcamThread"
        )
        self._thread.start()

    def read(self, timeout: float = 2.0) -> np.ndarray | None:
        """
        Return the most recent frame, or None on timeout.
        Drops stale frames so the caller always gets a fresh one.
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            logger.warning("Webcam read timed out after %.1fs", timeout)
            return None

    def stop(self) -> None:
        """Signal the background thread to stop and release the camera."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self._cap:
            self._cap.release()
        logger.info("Webcam released.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Background thread: continuously grab frames from the camera."""
        assert self._cap is not None
        while not self._stop_event.is_set():
            ret, frame = self._cap.read()
            if not ret:
                logger.error("Failed to read frame from webcam – retrying…")
                time.sleep(0.1)
                continue

            # Overwrite the queue so the consumer always gets the latest frame
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
            self._queue.put(frame)
