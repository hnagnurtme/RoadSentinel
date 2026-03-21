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
    "person",
    "face",
    "eye",
    "sleeping",
    "drowsy",
    "distracted",
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

    # Colour depends on event severity
    colour_map = {
        "normal": (0, 255, 0),        # green
        "sleeping": (0, 0, 255),      # red
        "using_phone": (0, 140, 255), # orange
        "distracted": (0, 255, 255),  # yellow
    }
    box_colour = colour_map.get(event, (200, 200, 200))

    for det in detections:
        x1, y1, x2, y2 = (int(v) for v in det["bbox"])
        label = f"{det['label']} {det['confidence']:.2f}"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), box_colour, 2)
        cv2.putText(
            annotated,
            label,
            (x1, max(y1 - 5, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            box_colour,
            1,
            cv2.LINE_AA,
        )

    # Overlay the current event in the top-left corner
    cv2.putText(
        annotated,
        f"EVENT: {event.upper()}",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        box_colour,
        2,
        cv2.LINE_AA,
    )

    return annotated
