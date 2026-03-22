"""
esp32_cam_simulator.py - Simulate an ESP32-CAM MJPEG server using a local webcam.

This server exposes:
  - GET /stream  -> MJPEG stream (multipart/x-mixed-replace)
  - GET /health  -> plain text health check

Example:
  python esp32_cam_simulator.py --host 0.0.0.0 --port 8081 --webcam-index 0
"""

from __future__ import annotations

import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2


class FrameStore:
    """Thread-safe store for latest JPEG frame bytes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None

    def set(self, jpeg: bytes) -> None:
        with self._lock:
            self._jpeg = jpeg

    def get(self) -> bytes | None:
        with self._lock:
            return self._jpeg


class WebcamStreamer:
    """Background webcam reader that continuously encodes latest frame to JPEG."""

    def __init__(
        self,
        frame_store: FrameStore,
        webcam_index: int,
        width: int,
        height: int,
        fps: int,
        jpeg_quality: int,
    ) -> None:
        self._frame_store = frame_store
        self._webcam_index = webcam_index
        self._width = width
        self._height = height
        self._fps = fps
        self._jpeg_quality = jpeg_quality

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cap: cv2.VideoCapture | None = None

    def start(self) -> None:
        self._cap = cv2.VideoCapture(self._webcam_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open webcam index={self._webcam_index}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="webcam")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
        if self._cap is not None:
            self._cap.release()

    def _run(self) -> None:
        assert self._cap is not None
        delay = 1.0 / max(self._fps, 1)

        while not self._stop_event.is_set():
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.1)
                continue

            ok, encoded = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality],
            )
            if ok:
                self._frame_store.set(encoded.tobytes())

            time.sleep(delay)


class MJPEGHandler(BaseHTTPRequestHandler):
    """Serve webcam frames as MJPEG to mimic ESP32-CAM stream endpoint."""

    frame_store: FrameStore
    stream_interval: float

    def log_message(self, *_args) -> None:  # type: ignore[override]
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path != "/stream":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            while True:
                frame = self.frame_store.get()
                if frame is not None:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                time.sleep(self.stream_interval)
        except (BrokenPipeError, ConnectionResetError):
            return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate ESP32-CAM MJPEG stream from local webcam"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8081, help="Bind port")
    parser.add_argument(
        "--webcam-index",
        type=int,
        default=0,
        help="OpenCV webcam device index",
    )
    parser.add_argument("--width", type=int, default=640, help="Capture width")
    parser.add_argument("--height", type=int, default=480, help="Capture height")
    parser.add_argument(
        "--fps", type=int, default=12, help="Capture and stream frame rate"
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=80,
        help="JPEG quality (1-100)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.port <= 0:
        raise ValueError("--port must be > 0")
    if args.fps <= 0:
        raise ValueError("--fps must be > 0")
    if args.width <= 0 or args.height <= 0:
        raise ValueError("--width/--height must be > 0")
    if not 1 <= args.jpeg_quality <= 100:
        raise ValueError("--jpeg-quality must be in [1, 100]")

    frame_store = FrameStore()
    streamer = WebcamStreamer(
        frame_store=frame_store,
        webcam_index=args.webcam_index,
        width=args.width,
        height=args.height,
        fps=args.fps,
        jpeg_quality=args.jpeg_quality,
    )
    streamer.start()

    handler = MJPEGHandler
    handler.frame_store = frame_store
    handler.stream_interval = 1.0 / args.fps

    server = ThreadingHTTPServer((args.host, args.port), handler)

    print("=" * 58)
    print("ESP32-CAM simulator is running")
    print(f"Stream : http://{args.host}:{args.port}/stream")
    print(f"Health : http://{args.host}:{args.port}/health")
    print("Press Ctrl+C to stop")
    print("=" * 58)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        streamer.stop()


if __name__ == "__main__":
    main()
