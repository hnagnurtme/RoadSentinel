from typing import cast

from app.inference.detect import Detection
from app.event.logic import EventLogic
from app.utils.config import EventConfig


def _det(label: str, confidence: float = 0.9) -> Detection:
    return cast(
        Detection,
        {
            "label": label,
            "class_id": 0,
            "confidence": confidence,
            "bbox": [0.0, 0.0, 1.0, 1.0],
        },
    )


def test_phone_has_highest_priority() -> None:
    logic = EventLogic(EventConfig(sleep_frame_threshold=3))

    event, conf = logic.classify([_det("cell phone", 0.88), _det("distracted", 0.95)])

    assert event == "using_phone"
    assert conf == 0.88


def test_sleeping_triggered_after_threshold() -> None:
    logic = EventLogic(EventConfig(sleep_frame_threshold=3))
    empty: list[Detection] = []

    assert logic.classify(empty)[0] == "normal"
    assert logic.classify(empty)[0] == "normal"
    event, _ = logic.classify(empty)

    assert event == "sleeping"


def test_face_presence_resets_sleep_counter() -> None:
    logic = EventLogic(EventConfig(sleep_frame_threshold=3))
    empty: list[Detection] = []

    logic.classify(empty)
    logic.classify(empty)
    logic.classify([_det("face", 0.7)])

    event, _ = logic.classify(empty)
    assert event == "normal"


def test_distracted_when_not_sleeping_or_phone() -> None:
    logic = EventLogic(EventConfig(sleep_frame_threshold=3))

    event, conf = logic.classify([_det("distracted", 0.76)])

    assert event == "distracted"
    assert conf == 0.76
