"""
postprocess.py – Post-process raw YOLO detections.

Provides helpers to filter, sort, and annotate detections before they
are handed off to the event-logic layer.
"""

import cv2
import numpy as np

from app.inference.detect import Detection
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Classes that are relevant to Driver Monitoring.
# Only these will be acted upon by the event layer.
RELEVANT_CLASSES = {
    "cell phone",
    "mobile",
    "texting",
    "driver talking on phone",
    "person",
    "driver",
    "face",
    "eye",
    "eyes open",
    "sleeping",
    "eyes closed",
    "yawning",
    "drowsy",
    "distracted",
    "driver looking away",
    "driver reaching behind",
}


def filter_detections(detections: list[Detection]) -> list[Detection]:
    """
    Keep only detections whose label is in RELEVANT_CLASSES.

    Args:
        detections: Raw list from detect.run_inference().

    Returns:
        Filtered list, sorted by confidence descending.
    """
    filtered = [d for d in detections if d["label"].lower() in RELEVANT_CLASSES]
    filtered.sort(key=lambda d: d["confidence"], reverse=True)
    return filtered


def annotate_frame(
    frame: np.ndarray,
    detections: list[Detection],
    event: str,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> np.ndarray:
    """
    Draw bounding boxes and labels on a copy of the frame for debugging.

    Args:
        frame:      BGR frame.
        detections: List of Detection dicts.
        event:      Current event string (displayed as an overlay).

    Returns:
        Annotated BGR frame (a copy – original is not modified).
    """
    annotated = frame.copy()
    height, width = annotated.shape[:2]

    # Dynamic style so text remains readable across resolutions.
    min_dim = max(1, min(width, height))
    font_scale = max(0.5, min_dim / 900.0)
    text_thickness = max(1, int(round(min_dim / 480.0)))
    box_thickness = max(2, int(round(min_dim / 320.0)))

    # Colour depends on event severity
    colour_map = {
        "normal": (0, 255, 0),  # green
        "sleeping": (0, 0, 255),  # red
        "using_phone": (0, 140, 255),  # orange
        "distracted": (0, 255, 255),  # yellow
    }
    box_colour = colour_map.get(event, (200, 200, 200))

    class_color_map: dict[str, tuple[int, int, int]] = {
        "driver": (59, 130, 246),
        "person": (59, 130, 246),
        "face": (16, 185, 129),
        "eye": (16, 185, 129),
        "eyes open": (16, 185, 129),
        "eyes closed": (239, 68, 68),
        "sleeping": (220, 38, 38),
        "drowsy": (220, 38, 38),
        "yawning": (6, 182, 212),
        "mobile": (168, 85, 247),
        "cell phone": (168, 85, 247),
        "texting": (99, 102, 241),
        "driver talking on phone": (236, 72, 153),
        "distracted": (245, 158, 11),
        "driver looking away": (249, 115, 22),
        "driver reaching behind": (132, 204, 22),
    }

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        x1 = int(round(x1 * scale_x))
        y1 = int(round(y1 * scale_y))
        x2 = int(round(x2 * scale_x))
        y2 = int(round(y2 * scale_y))

        x1 = max(0, min(width - 1, x1))
        y1 = max(0, min(height - 1, y1))
        x2 = max(0, min(width - 1, x2))
        y2 = max(0, min(height - 1, y2))
        if x2 <= x1 or y2 <= y1:
            continue

        label_name = det["label"]
        label = f"{label_name} {det['confidence']:.0%}"
        class_color = class_color_map.get(label_name.lower(), box_colour)
        bgr = (class_color[2], class_color[1], class_color[0])

        cv2.rectangle(annotated, (x1, y1), (x2, y2), bgr, box_thickness)

        (text_w, text_h), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            text_thickness,
        )
        label_x = x1
        above_y = y1 - 6
        label_y = above_y if above_y > text_h + baseline + 4 else y1 + text_h + 6
        top = label_y - text_h - baseline - 4
        bottom = label_y + baseline + 2

        cv2.rectangle(
            annotated,
            (label_x, top),
            (label_x + text_w + 8, bottom),
            bgr,
            -1,
        )
        cv2.putText(
            annotated,
            label,
            (label_x + 4, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            text_thickness,
            cv2.LINE_AA,
        )

    # Overlay the current event in the top-left corner
    event_text = f"EVENT: {event.upper()}"
    (event_w, event_h), event_baseline = cv2.getTextSize(
        event_text,
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.7, font_scale * 1.1),
        max(2, text_thickness),
    )
    cv2.rectangle(
        annotated,
        (8, 8),
        (8 + event_w + 12, 8 + event_h + event_baseline + 10),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        annotated,
        event_text,
        (14, 8 + event_h + 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.7, font_scale * 1.1),
        box_colour,
        max(2, text_thickness),
        cv2.LINE_AA,
    )

    return annotated
