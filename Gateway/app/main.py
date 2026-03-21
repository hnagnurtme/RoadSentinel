"""
main.py – Gateway entry point.

Pipeline per frame:
  capture → preprocess → inference → postprocess → event logic → send

Threading model:
  - Capture runs in a background thread (WebcamCapture / ESP32Capture).
  - WebSocketSender runs in a background thread with its own asyncio loop.
  - This main thread runs the processing pipeline at ~TARGET_FPS.
"""

import signal
import sys
import time

from app.capture.esp32 import ESP32Capture
from app.capture.webcam import WebcamCapture
from app.event.logic import EventLogic
from app.inference.detect import run_inference
from app.inference.model import load_model
from app.processing.postprocess import filter_detections
from app.processing.preprocess import preprocess_frame
from app.sender.websocket import WebSocketSender
from app.utils.config import CONFIG
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Graceful shutdown ────────────────────────────────────────────────────────
_running = True


def _handle_signal(sig, frame):  # noqa: ANN001
    global _running
    logger.info("Shutdown signal received (%s) – stopping…", sig)
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Factory helpers ──────────────────────────────────────────────────────────

def _build_capture():
    """Instantiate the correct capture backend based on config."""
    source = CONFIG.capture.source
    if source == "esp32":
        capture = ESP32Capture(CONFIG.capture)
    else:
        capture = WebcamCapture(CONFIG.capture)
    logger.info("Capture source: %s", source)
    return capture


# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("=== Gateway DMS starting ===")

    # 1. Load YOLO model (once)
    load_model(CONFIG.inference)

    # 2. Build and start capture
    capture = _build_capture()
    capture.start()

    # 3. Start WebSocket sender
    sender = WebSocketSender(CONFIG.sender)
    sender.start()

    # 4. Build event classifier
    event_logic = EventLogic(CONFIG.event)

    # Frame timing
    frame_interval = 1.0 / CONFIG.capture.target_fps

    logger.info(
        "Main loop running at ~%d FPS. Press Ctrl+C to stop.",
        CONFIG.capture.target_fps,
    )

    try:
        while _running:
            loop_start = time.monotonic()

            # ── Capture ──────────────────────────────────────────────────────
            frame = capture.read(timeout=2.0)
            if frame is None:
                logger.warning("No frame received – skipping cycle.")
                time.sleep(frame_interval)
                continue

            # ── Preprocess ───────────────────────────────────────────────────
            try:
                processed = preprocess_frame(frame, CONFIG.preprocess)
            except Exception as exc:
                logger.error("Preprocess error: %s", exc)
                continue

            # ── Inference ────────────────────────────────────────────────────
            try:
                raw_detections = run_inference(processed, CONFIG.inference)
            except Exception as exc:
                logger.error("Inference error: %s", exc)
                continue

            # ── Postprocess ──────────────────────────────────────────────────
            detections = filter_detections(raw_detections)

            # ── Event classification ─────────────────────────────────────────
            event, confidence = event_logic.classify(detections)
            logger.info("Event=%s  conf=%.2f  dets=%d", event, confidence, len(detections))

            # ── Send result to backend ───────────────────────────────────────
            payload = {
                "device_id": CONFIG.sender.device_id,
                "event": event,
                "confidence": round(confidence, 4),
            }
            sender.send(payload)

            # ── FPS throttle ─────────────────────────────────────────────────
            elapsed = time.monotonic() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as exc:
        logger.critical("Unhandled exception in main loop: %s", exc, exc_info=True)
    finally:
        logger.info("Shutting down…")
        capture.stop()
        sender.stop()
        logger.info("=== Gateway DMS stopped ===")
        sys.exit(0)


if __name__ == "__main__":
    main()
