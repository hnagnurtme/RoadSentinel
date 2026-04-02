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
import time

from app.capture.esp32 import ESP32Capture
from app.capture.webcam import WebcamCapture
from app.event.logic import EventLogic
from app.evidence.recorder import EvidenceRecorder
from app.evidence.trigger import SleepWindowTrigger
from app.inference.detect import run_inference
from app.inference.model import load_model
from app.processing.postprocess import annotate_frame, filter_detections
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

    capture = None
    sender = None
    capture_started = False
    sender_started = False

    try:
        # 1. Load YOLO model (once)
        load_model(CONFIG.inference)

        # 2. Build and start capture
        capture = _build_capture()
        capture.start()
        capture_started = True

        # 3. Start WebSocket sender
        sender = WebSocketSender(CONFIG.sender)
        sender.start()
        sender_started = True

        # 4. Build event classifier
        event_logic = EventLogic(CONFIG.event)

        # 5. Build minimal evidence recorder
        evidence = EvidenceRecorder(
            CONFIG.evidence,
            fps=CONFIG.capture.target_fps,
            device_id=CONFIG.sender.device_id,
            cloudinary_cfg=CONFIG.cloudinary,
        )
        sleep_trigger = SleepWindowTrigger(
            fps=CONFIG.capture.target_fps,
            window_seconds=CONFIG.evidence.sleep_evidence_seconds,
            occupancy_threshold=1.0,
        )
        violation_events = set(CONFIG.event.event_priority)
        sleeping_release_grace_seconds = 1.0
        last_sleeping_seen_at: float | None = None
        last_sleeping_confidence = 0.0
        was_sleeping_event = False

        # Frame timing
        frame_interval = 1.0 / CONFIG.capture.target_fps

        logger.info(
            "Main loop running at ~%d FPS. Press Ctrl+C to stop.",
            CONFIG.capture.target_fps,
        )
        logger.info(
            "Evidence config: window=%ss ratio=%.2f proxy=%s min_sleep=%.2f",
            CONFIG.evidence.sleep_evidence_seconds,
            CONFIG.evidence.sleep_trigger_ratio,
            CONFIG.evidence.use_sleep_proxy,
            CONFIG.event.min_sleep_confidence,
        )

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
                time.sleep(frame_interval)
                continue

            # ── Inference ────────────────────────────────────────────────────
            try:
                raw_detections = run_inference(processed, CONFIG.inference)
            except Exception as exc:
                logger.error("Inference error: %s", exc)
                time.sleep(frame_interval)
                continue

            # ── Postprocess ──────────────────────────────────────────────────
            detections = filter_detections(raw_detections)

            # ── Event classification ─────────────────────────────────────────
            raw_event, raw_confidence = event_logic.classify(detections)
            now_monotonic = time.monotonic()

            if raw_event == "sleeping":
                last_sleeping_seen_at = now_monotonic
                last_sleeping_confidence = raw_confidence
                event = raw_event
                confidence = raw_confidence
            elif (
                last_sleeping_seen_at is not None
                and (now_monotonic - last_sleeping_seen_at)
                < sleeping_release_grace_seconds
            ):
                # Hold sleeping briefly to avoid close-open-close flicker.
                event = "sleeping"
                confidence = max(raw_confidence, last_sleeping_confidence)
            else:
                event = raw_event
                confidence = raw_confidence

            logger.info(
                "Event=%s  conf=%.2f  dets=%d", event, confidence, len(detections)
            )

            # Evidence clips should keep the same visual labels users see.
            proc_h, proc_w = processed.shape[:2]
            raw_h, raw_w = frame.shape[:2]
            scale_x = raw_w / proc_w if proc_w else 1.0
            scale_y = raw_h / proc_h if proc_h else 1.0
            annotated = annotate_frame(
                frame,
                detections,
                event,
                scale_x=scale_x,
                scale_y=scale_y,
            )

            is_sleeping_event = event == "sleeping"
            if is_sleeping_event:
                if not was_sleeping_event:
                    evidence.reset_buffer()
                evidence.push_frame(annotated)
            elif was_sleeping_event:
                # Sleeping broke before reaching full window: discard partial clip.
                evidence.reset_buffer()

            # Strict policy: require a full continuous sleeping window (8s).
            sleep_evidence_present = is_sleeping_event

            should_save = sleep_trigger.update(sleep_evidence_present)
            if should_save:
                saved = evidence.save_sleeping_clip(confidence)
                if saved is not None:
                    logger.warning("Evidence written to %s", saved)

            was_sleeping_event = is_sleeping_event

            # ── Realtime event stream: send active violations immediately ─────
            if event in violation_events:
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
        if capture_started and capture is not None:
            try:
                capture.stop()
            except Exception as exc:
                logger.error("Capture stop error: %s", exc)
        if sender_started and sender is not None:
            try:
                sender.stop()
            except Exception as exc:
                logger.error("Sender stop error: %s", exc)
        logger.info("=== Gateway DMS stopped ===")


if __name__ == "__main__":
    main()
