"""
core/ai/annotator.py
--------------------
OpenCV-based frame annotation utilities for evidence clips.

Kept separate so the pure Python classifier logic in event_classifier.py
has no cv2 dependency.
"""
from __future__ import annotations

import importlib.util
import logging

logger = logging.getLogger(__name__)


def annotate_evidence_jpeg(
    jpeg_bytes: bytes,
    detections: list[dict],
    event: str,
    duration_ms: int,
    confidence: float,
) -> bytes:
    """Draw detection bounding boxes and an event overlay onto a JPEG frame.

    Silently returns the original ``jpeg_bytes`` when cv2/numpy are not
    installed or when the frame cannot be decoded.

    Args:
        jpeg_bytes: Raw JPEG bytes.
        detections: List of ``{label, conf, bbox}`` dicts.
        event: Current driver event label (e.g. ``"sleeping"``).
        duration_ms: How long the event has been active, in milliseconds.
        confidence: Overall event confidence score.

    Returns:
        Annotated JPEG bytes (possibly identical to the input on failure).
    """
    if (
        importlib.util.find_spec("cv2") is None
        or importlib.util.find_spec("numpy") is None
    ):
        return jpeg_bytes

    try:
        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        frame = _cv2.imdecode(_np.frombuffer(jpeg_bytes, dtype=_np.uint8), _cv2.IMREAD_COLOR)
        if frame is None:
            return jpeg_bytes

        _draw_detections(frame, detections, _cv2)
        _draw_event_overlay(frame, event, duration_ms, confidence, _cv2)

        ok, encoded = _cv2.imencode(".jpg", frame, [_cv2.IMWRITE_JPEG_QUALITY, 90])
        return encoded.tobytes() if ok else jpeg_bytes

    except Exception:
        logger.debug("Frame annotation failed", exc_info=True)
        return jpeg_bytes


# ── Private helpers ───────────────────────────────────────────────────────────


def _draw_detections(frame: object, detections: list[dict], cv2: object) -> None:
    """Draw bounding boxes and labels for each detection in-place."""
    for det in detections:
        bbox = det.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = (int(v) for v in bbox)
        conf = float(det.get("conf", det.get("confidence", 0.0)))
        label_name = str(det.get("label", "unknown"))
        label = f"{label_name} {conf:.0%}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 136), 2)  # type: ignore[attr-defined]
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)  # type: ignore[attr-defined]
        top = max(0, y1 - th - baseline - 6)
        cv2.rectangle(frame, (x1, top), (x1 + tw + 8, top + th + baseline + 4), (0, 255, 136), -1)  # type: ignore[attr-defined]
        cv2.putText(  # type: ignore[attr-defined]
            frame,
            label,
            (x1 + 4, top + th + 1),
            cv2.FONT_HERSHEY_SIMPLEX,  # type: ignore[attr-defined]
            0.45,
            (0, 0, 0),
            1,
            cv2.LINE_AA,  # type: ignore[attr-defined]
        )


def _draw_event_overlay(
    frame: object,
    event: str,
    duration_ms: int,
    confidence: float,
    cv2: object,
) -> None:
    """Draw a top-left event status banner in-place."""
    seconds = max(0, duration_ms // 1000)
    mm, ss = divmod(seconds, 60)
    event_label = f"{event.upper()}  {mm:02d}:{ss:02d}  conf={confidence:.2f}"

    (tw, th), baseline = cv2.getTextSize(event_label, cv2.FONT_HERSHEY_SIMPLEX, 0.62, 2)  # type: ignore[attr-defined]
    cv2.rectangle(frame, (10, 10), (10 + tw + 14, 10 + th + baseline + 12), (220, 38, 38), -1)  # type: ignore[attr-defined]
    cv2.putText(  # type: ignore[attr-defined]
        frame,
        event_label,
        (17, 10 + th + 2),
        cv2.FONT_HERSHEY_SIMPLEX,  # type: ignore[attr-defined]
        0.62,
        (255, 255, 255),
        2,
        cv2.LINE_AA,  # type: ignore[attr-defined]
    )
