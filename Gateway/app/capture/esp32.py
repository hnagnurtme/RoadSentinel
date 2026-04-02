"""
esp32.py – Capture frames from an ESP32-CAM MJPEG stream.

The ESP32-CAM outputs a multipart/x-mixed-replace HTTP stream.
We parse the JPEG boundaries and decode each frame.
"""

import queue
import threading
import time

import cv2
import numpy as np
import requests
from app.utils.config import CaptureConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

_BOUNDARY_MARKER = b"--"
_JPEG_START = b"\xff\xd8"
_JPEG_END = b"\xff\xd9"
_MAX_STREAM_BUFFER_BYTES = 2 * 1024 * 1024
_BUFFER_TRIM_BYTES = 512 * 1024


class ESP32Capture:
    """Captures frames from an ESP32-CAM MJPEG HTTP stream."""

    def __init__(self, cfg: CaptureConfig) -> None:
        self._cfg = cfg
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background streaming thread."""
        logger.info("Starting ESP32-CAM capture: %s", self._cfg.esp32_url)
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._stream_loop, daemon=True, name="ESP32Thread"
        )
        self._thread.start()

    def read(self, timeout: float = 2.0) -> np.ndarray | None:
        """Return the most recent frame or None on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            logger.warning("ESP32 read timed out after %.1fs", timeout)
            return None

    def stop(self) -> None:
        """Signal the streaming thread to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("ESP32 capture stopped.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _stream_loop(self) -> None:
        """
        Background thread: connect to the MJPEG endpoint and parse frames.
        Reconnects automatically on failure.
        """
        while not self._stop_event.is_set():
            try:
                self._connect_and_read()
            except Exception as exc:
                logger.error("ESP32 stream error: %s – reconnecting in 3 s", exc)
                time.sleep(3)

    def _connect_and_read(self) -> None:
        """Open the HTTP stream and decode JPEG frames until stop is signaled."""
        with requests.get(
            self._cfg.esp32_url,
            stream=True,
            timeout=(5, 15),
            headers={"User-Agent": "RoadSentinel-Gateway/1.0", "Accept": "*/*"},
        ) as response:
            response.raise_for_status()
            logger.info("Connected to ESP32-CAM stream.")
            buf = bytearray()

            for chunk in response.iter_content(chunk_size=4096):
                if self._stop_event.is_set():
                    break

                if not chunk:
                    continue
                buf.extend(chunk)

                if len(buf) > _MAX_STREAM_BUFFER_BYTES:
                    logger.warning(
                        "ESP32 stream buffer exceeded %d bytes; trimming.",
                        _MAX_STREAM_BUFFER_BYTES,
                    )
                    del buf[:-_BUFFER_TRIM_BYTES]

                # Extract as many complete JPEG frames as available.
                while True:
                    start = buf.find(_JPEG_START)
                    if start == -1:
                        # Keep a small tail in case marker spans chunk boundary.
                        if len(buf) > 2:
                            del buf[:-2]
                        break

                    if start > 0:
                        # Drop preamble/truncated bytes before JPEG SOI.
                        del buf[:start]
                        start = 0

                    end = buf.find(_JPEG_END, start + 2)
                    if end == -1:
                        break

                    jpg_bytes = bytes(buf[start : end + 2])
                    del buf[: end + 2]  # discard consumed data

                    frame = self._decode_jpeg(jpg_bytes)
                    if frame is not None:
                        # Keep queue fresh
                        if self._queue.full():
                            try:
                                self._queue.get_nowait()
                            except queue.Empty:
                                pass
                        self._queue.put(frame)

    @staticmethod
    def _decode_jpeg(jpg_bytes: bytes) -> np.ndarray | None:
        """Decode raw JPEG bytes into a BGR numpy array."""
        arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            logger.debug("Failed to decode a JPEG frame – skipping.")
        return frame
