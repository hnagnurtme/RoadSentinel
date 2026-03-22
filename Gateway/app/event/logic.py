"""
logic.py – Driver-event classification with hysteresis.

The classifier consumes per-frame detections and outputs stable events:
"normal" | "using_phone" | "sleeping" | "distracted" | "unknown".

Key design:
- Event evidence is label-based (no-face is not interpreted as sleeping).
- Each event has enter/exit frame thresholds to reduce flicker.
- Long observation loss becomes "unknown" so upstream can treat it safely.
"""

from app.inference.detect import Detection
from app.utils.config import EventConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EventLogic:
    """
    Stateful event classifier with per-event hysteresis.

    Each event accumulates evidence over frames:
    - enters active state at enter_threshold
    - stays active until score falls below exit_threshold
    """

    def __init__(self, cfg: EventConfig) -> None:
        self._cfg = cfg
        self._no_presence_counter = 0

        self._event_scores: dict[str, int] = {
            "sleeping": 0,
            "using_phone": 0,
            "distracted": 0,
        }
        self._event_active: dict[str, bool] = {
            "sleeping": False,
            "using_phone": False,
            "distracted": False,
        }

        self._enter_thresholds = {
            "sleeping": cfg.sleep_enter_frames,
            "using_phone": cfg.phone_enter_frames,
            "distracted": cfg.distracted_enter_frames,
        }
        self._exit_thresholds = {
            "sleeping": cfg.sleep_exit_frames,
            "using_phone": cfg.phone_exit_frames,
            "distracted": cfg.distracted_exit_frames,
        }

        self._label_sets = {
            "sleeping": {label.lower() for label in cfg.sleep_labels},
            "using_phone": {label.lower() for label in cfg.phone_labels},
            "distracted": {label.lower() for label in cfg.distracted_labels},
        }

        self._confidence_thresholds = {
            "sleeping": cfg.min_sleep_confidence,
            "using_phone": cfg.min_phone_confidence,
            "distracted": cfg.min_distracted_confidence,
        }

        self._presence_labels = {label.lower() for label in cfg.presence_labels}

    @staticmethod
    def _max_conf_by_label(detections: list[Detection]) -> dict[str, float]:
        out: dict[str, float] = {}
        for det in detections:
            label = det["label"].lower()
            conf = det["confidence"]
            prev = out.get(label, 0.0)
            if conf > prev:
                out[label] = conf
        return out

    def _update_event_state(self, event: str, has_evidence: bool) -> None:
        score = self._event_scores[event]
        enter = self._enter_thresholds[event]
        exit_ = self._exit_thresholds[event]

        if has_evidence:
            score = min(enter, score + 1)
        else:
            score = max(0, score - 1)

        active = self._event_active[event]
        if active and score < exit_:
            active = False
        elif (not active) and score >= enter:
            active = True

        self._event_scores[event] = score
        self._event_active[event] = active

    def classify(self, detections: list[Detection]) -> tuple[str, float]:
        """
        Classify the current frame's detections into a driver event.

        Args:
            detections: List of Detection dicts from the inference step.

        Returns:
            (event, confidence) where event is one of:
                "using_phone" | "sleeping" | "distracted" | "unknown" | "normal"
            and confidence reflects event-specific evidence, not global max confidence.
        """
        label_conf = self._max_conf_by_label(detections)

        # Observation quality tracking: no presence -> unknown after threshold.
        has_presence = any(label in self._presence_labels for label in label_conf)
        if has_presence:
            self._no_presence_counter = 0
        else:
            self._no_presence_counter += 1

        event_confidence: dict[str, float] = {}
        for event in self._event_scores:
            evidence_conf = max(
                (
                    conf
                    for label, conf in label_conf.items()
                    if label in self._label_sets[event]
                ),
                default=0.0,
            )
            event_confidence[event] = evidence_conf
            has_evidence = evidence_conf >= self._confidence_thresholds[event]
            self._update_event_state(event, has_evidence)

        for event in self._cfg.event_priority:
            if self._event_active.get(event, False):
                conf = event_confidence.get(event, 0.0)
                logger.info("Event: %s (conf=%.2f)", event, conf)
                return event, conf

        if self._no_presence_counter >= self._cfg.unknown_enter_frames:
            logger.warning(
                "Event: unknown (no observable driver for %d frames)",
                self._no_presence_counter,
            )
            return "unknown", 0.0

        return "normal", 0.0

    def reset(self) -> None:
        """Reset internal counters (e.g. when the capture source restarts)."""
        self._no_presence_counter = 0
        for event in self._event_scores:
            self._event_scores[event] = 0
            self._event_active[event] = False
