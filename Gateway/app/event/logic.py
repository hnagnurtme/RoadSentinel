"""
logic.py – Driver-event classification logic.

Translates raw YOLO detections into a human-readable event string
("normal" | "using_phone" | "sleeping" | "distracted").
Uses a simple stateful counter so transient false negatives for face/eye
detection don't immediately trigger a "sleeping" alert.
"""

from app.inference.detect import Detection
from app.utils.config import EventConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Class labels to treat as face/eye presence indicators
_FACE_LABELS = {"face", "person", "eye"}

# Class labels interpreted as phone usage
_PHONE_LABELS = {"cell phone"}


class EventLogic:
    """
    Stateful event classifier.

    Maintains a counter of consecutive frames where no face/eyes are visible,
    and raises "sleeping" once the threshold is exceeded.
    """

    def __init__(self, cfg: EventConfig) -> None:
        self._cfg = cfg
        # Counts consecutive frames with no face/eye detected
        self._no_face_counter: int = 0

    def classify(self, detections: list[Detection]) -> tuple[str, float]:
        """
        Classify the current frame's detections into a driver event.

        Args:
            detections: List of Detection dicts from the inference step.

        Returns:
            (event, confidence) where event is one of:
                "using_phone" | "sleeping" | "distracted" | "normal"
            and confidence is the highest confidence among relevant detections.
        """
        labels = {d["label"].lower() for d in detections}
        confidences = [d["confidence"] for d in detections] or [0.0]
        max_confidence = max(confidences)

        # --- Priority 1: Phone usage ---
        if labels & _PHONE_LABELS:
            self._no_face_counter = 0
            event = "using_phone"
            conf = max(
                d["confidence"]
                for d in detections
                if d["label"].lower() in _PHONE_LABELS
            )
            logger.info("Event: %s (conf=%.2f)", event, conf)
            return event, conf

        # --- Priority 2: Sleeping / no face ---
        face_present = bool(labels & _FACE_LABELS)
        if not face_present:
            self._no_face_counter += 1
            logger.debug(
                "No face/eye detected (%d/%d frames)",
                self._no_face_counter,
                self._cfg.sleep_frame_threshold,
            )
        else:
            self._no_face_counter = 0

        if self._no_face_counter >= self._cfg.sleep_frame_threshold:
            logger.warning(
                "Sleeping event triggered after %d frames with no face/eye",
                self._no_face_counter,
            )
            return "sleeping", max_confidence

        # --- Priority 3: Distracted (face present but model flags distraction) ---
        distraction_labels = {"distracted", "drowsy"}
        if labels & distraction_labels:
            conf = max(
                d["confidence"]
                for d in detections
                if d["label"].lower() in distraction_labels
            )
            logger.info("Event: distracted (conf=%.2f)", conf)
            return "distracted", conf

        # --- Default: normal ---
        return "normal", max_confidence

    def reset(self) -> None:
        """Reset internal counters (e.g. when the capture source restarts)."""
        self._no_face_counter = 0
