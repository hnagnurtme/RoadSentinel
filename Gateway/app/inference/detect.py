"""
detect.py – Run YOLO inference on a single frame.

Returns a list of structured detection dicts so downstream components
don't need to interact with the raw ultralytics Result object.
"""

from typing import TypedDict

import numpy as np
from app.inference.model import get_model
from app.utils.config import InferenceConfig
from app.utils.logger import get_logger
from ultralytics.engine.results import Results

logger = get_logger(__name__)


class Detection(TypedDict):
    """A single YOLO object detection result."""

    label: str  # Human-readable class name (e.g. "cell phone")
    class_id: int  # Integer class ID from the model
    confidence: float  # Detection confidence [0, 1]
    bbox: list[float]  # [x1, y1, x2, y2] in pixel coordinates


def run_inference(frame: np.ndarray, cfg: InferenceConfig) -> list[Detection]:
    """
    Run YOLO inference on the provided frame.

    Args:
        frame: BGR numpy array (H × W × 3).
        cfg:   Inference configuration (thresholds etc.)

    Returns:
        List of Detection dicts, filtered by confidence threshold.
    """
    model = get_model()

    results: list[Results] = model.predict(
        source=frame,
        conf=cfg.confidence_threshold,
        iou=cfg.iou_threshold,
        verbose=False,  # suppress per-frame console spam
    )

    detections: list[Detection] = []

    for result in results:
        if result.boxes is None:
            continue

        names: dict[int, str] = result.names  # {class_id: class_name}

        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            label = names.get(class_id, str(class_id))

            detections.append(
                Detection(
                    label=label,
                    class_id=class_id,
                    confidence=confidence,
                    bbox=bbox,
                )
            )
            logger.debug("Detected: %s  conf=%.2f  bbox=%s", label, confidence, bbox)

    return detections
