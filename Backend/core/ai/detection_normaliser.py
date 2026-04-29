"""
core/ai/detection_normaliser.py
-----------------------------------
Normalises raw YOLO detections to canonical events with confidence weights.

This is the only place in the codebase where raw YOLO label strings appear.
All other components work with canonical events only.
"""

from dataclasses import dataclass
from typing import Final, List, Dict

# Canonical event types — the rest of the system only knows these.
CANONICAL_EVENTS: Final = frozenset({
    "sleeping", "drowsy", "using_phone", "distracted", "normal", "unknown"
})

# Map raw YOLO label → canonical event + base weight
# Weight reflects how strongly this label implies the event (0.0–1.0).
LABEL_EVENT_MAP: Final[Dict[str, tuple[str, float]]] = {
    "eyes closed":   ("sleeping",    1.0),  # direct physiological sign
    "microsleep":    ("sleeping",    0.9),  # brief closure, still sleeping
    "yawning":       ("drowsy",      1.0),  # fatigue, NOT sleeping
    "drowsy":        ("drowsy",      0.9),
    "mobile":        ("using_phone", 1.0),
    "cell phone":    ("using_phone", 0.95),
    "texting":       ("using_phone", 0.85),
    "distracted":    ("distracted",  1.0),
    "drinking":      ("distracted",  0.75),  # lower weight — ambiguous
    "seat belt":     ("distracted",  0.60),  # safety violation, not gaze
    "driver":        ("normal",      1.0),   # presence confirmation
    "face":          ("normal",      0.8),
    # Add more mappings as needed for your specific YOLO model
}


@dataclass(frozen=True)
class NormalisedDetection:
    """A single normalised detection with canonical event and weighted confidence."""
    event: str          # canonical event name
    raw_label: str      # original YOLO label
    confidence: float   # YOLO confidence * label weight
    bbox: List[int]     # bounding box [x, y, w, h] or similar


def normalise(detections: List[Dict]) -> List[NormalisedDetection]:
    """
    Convert raw YOLO detections to NormalisedDetections.
    Filters out labels not in LABEL_EVENT_MAP.
    Applies label weight to confidence.
    
    Args:
        detections: List of raw YOLO detections with 'label', 'conf', 'bbox' keys
        
    Returns:
        List of NormalisedDetection objects
    """
    result = []
    for det in detections:
        label = str(det.get("label", "")).lower().strip()
        conf  = float(det.get("conf", 0.0))
        mapping = LABEL_EVENT_MAP.get(label)
        if mapping is None:
            continue  # Skip unknown labels
        event, weight = mapping
        result.append(NormalisedDetection(
            event=event,
            raw_label=label,
            confidence=min(1.0, conf * weight),
            bbox=det.get("bbox", []),
        ))
    return result


def best_confidence_per_event(
    detections: List[NormalisedDetection],
) -> Dict[str, float]:
    """
    Return {event: max_confidence} from a normalised detection list.
    
    Args:
        detections: List of NormalisedDetection objects
        
    Returns:
        Dictionary mapping event names to their highest confidence in this frame
    """
    out: Dict[str, float] = {}
    for det in detections:
        if det.confidence > out.get(det.event, 0.0):
            out[det.event] = det.confidence
    return out


def apply_confidence_gates(
    event_conf: Dict[str, float],
    gates: Dict[str, float],
) -> Dict[str, float]:
    """
    Apply per-event minimum confidence gates.
    Detections below the gate are treated as absent for that frame.
    
    Args:
        event_conf: {event: confidence} from best_confidence_per_event
        gates: {event: minimum_confidence} configuration
        
    Returns:
        Filtered dictionary with only events above their gates
    """
    return {
        event: conf
        for event, conf in event_conf.items()
        if conf >= gates.get(event, 0.0)
    }
