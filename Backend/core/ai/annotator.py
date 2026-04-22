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
from typing import Any

logger = logging.getLogger(__name__)


def _has_cv_stack() -> bool:
    return (
        importlib.util.find_spec("cv2") is not None
        and importlib.util.find_spec("numpy") is not None
    )


def annotate_evidence_frame(
    frame: Any,
    detections: list[dict],
    event: str,
    duration_ms: int,
    confidence: float,
) -> bool:
    """Draw overlays in-place onto an already decoded OpenCV frame.

    Returns ``True`` when drawing succeeded, else ``False``.
    """
    if not _has_cv_stack():
        return False

    try:
        import cv2 as _cv2  # type: ignore

        _draw_detections(frame, detections, _cv2)
        _draw_event_overlay(frame, event, duration_ms, confidence, _cv2)
        return True
    except Exception:
        logger.debug("Frame annotation failed", exc_info=True)
        return False


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
    if not _has_cv_stack():
        return jpeg_bytes

    try:
        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        frame = _cv2.imdecode(_np.frombuffer(jpeg_bytes, dtype=_np.uint8), _cv2.IMREAD_COLOR)
        if frame is None:
            return jpeg_bytes

        if not annotate_evidence_frame(frame, detections, event, duration_ms, confidence):
            return jpeg_bytes

        ok, encoded = _cv2.imencode(".jpg", frame, [_cv2.IMWRITE_JPEG_QUALITY, 90])
        return encoded.tobytes() if ok else jpeg_bytes

    except Exception:
        logger.debug("Frame annotation failed", exc_info=True)
        return jpeg_bytes


# ── Private helpers ───────────────────────────────────────────────────────────


def _draw_detections(frame: object, detections: list[dict], cv2: object) -> None:
    """Draw bounding boxes and labels for each detection in-place."""
    frame_h = int(getattr(frame, "shape", [0, 0])[0])
    frame_w = int(getattr(frame, "shape", [0, 0])[1])
    base = max(240, min(frame_w, frame_h))
    line_w = max(2, int(round(base / 200)))
    font_scale = max(0.45, base / 720.0)
    text_thickness = max(1, line_w - 1)
    label_pad_x = max(4, int(round(base / 180)))
    label_pad_y = max(3, int(round(base / 260)))

    for det in detections:
        bbox = det.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = (int(v) for v in bbox)
        x1 = max(0, min(frame_w - 1, x1))
        x2 = max(0, min(frame_w - 1, x2))
        y1 = max(0, min(frame_h - 1, y1))
        y2 = max(0, min(frame_h - 1, y2))
        if x2 <= x1 or y2 <= y1:
            continue

        conf = float(det.get("conf", det.get("confidence", 0.0)))
        label_name = str(det.get("label", "unknown"))
        label = f"{label_name} {conf:.0%}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 136), line_w)  # type: ignore[attr-defined]
        (tw, th), baseline = cv2.getTextSize(  # type: ignore[attr-defined]
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness
        )
        top = max(0, y1 - th - baseline - (2 * label_pad_y))
        left = max(0, x1)
        right = min(frame_w - 1, x1 + tw + (2 * label_pad_x))
        bottom = min(frame_h - 1, top + th + baseline + (2 * label_pad_y))

        overlay = frame.copy()
        cv2.rectangle(overlay, (left, top), (right, bottom), (0, 255, 136), -1)  # type: ignore[attr-defined]
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)  # type: ignore[attr-defined]

        cv2.putText(  # type: ignore[attr-defined]
            frame,
            label,
            (left + label_pad_x, top + th + label_pad_y),
            cv2.FONT_HERSHEY_SIMPLEX,  # type: ignore[attr-defined]
            font_scale,
            (0, 0, 0),
            text_thickness,
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
    frame_h = int(getattr(frame, "shape", [0, 0])[0])
    frame_w = int(getattr(frame, "shape", [0, 0])[1])
    base = max(240, min(frame_w, frame_h))
    font_scale = max(0.58, base / 560.0)
    text_thickness = max(2, int(round(base / 260)))
    pad_x = max(10, int(round(base / 55)))
    pad_y = max(8, int(round(base / 85)))

    seconds = max(0, duration_ms // 1000)
    mm, ss = divmod(seconds, 60)
    event_label = f"{event.replace('_', ' ').upper()}  {mm:02d}:{ss:02d}  conf={confidence:.2f}"

    (tw, th), baseline = cv2.getTextSize(  # type: ignore[attr-defined]
        event_label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness
    )
    left = max(8, int(round(base / 70)))
    top = max(8, int(round(base / 70)))
    right = min(frame_w - 1, left + tw + (2 * pad_x))
    bottom = min(frame_h - 1, top + th + baseline + (2 * pad_y))

    overlay = frame.copy()
    cv2.rectangle(overlay, (left, top), (right, bottom), (220, 38, 38), -1)  # type: ignore[attr-defined]
    cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)  # type: ignore[attr-defined]

    cv2.putText(  # type: ignore[attr-defined]
        frame,
        event_label,
        (left + pad_x, top + th + pad_y),
        cv2.FONT_HERSHEY_SIMPLEX,  # type: ignore[attr-defined]
        font_scale,
        (255, 255, 255),
        text_thickness,
        cv2.LINE_AA,  # type: ignore[attr-defined]
    )
