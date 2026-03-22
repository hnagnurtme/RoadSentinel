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
    logic = EventLogic(
        EventConfig(
            phone_enter_frames=2,
            phone_exit_frames=1,
            distracted_enter_frames=2,
            distracted_exit_frames=1,
        )
    )

    assert (
        logic.classify([_det("cell phone", 0.88), _det("distracted", 0.95)])[0]
        == "normal"
    )
    event, conf = logic.classify([_det("cell phone", 0.88), _det("distracted", 0.95)])

    assert event == "using_phone"
    assert conf == 0.88


def test_sleeping_requires_direct_sleep_evidence() -> None:
    logic = EventLogic(
        EventConfig(
            sleep_enter_frames=2,
            sleep_exit_frames=1,
            min_sleep_confidence=0.5,
            unknown_enter_frames=10,
        )
    )

    assert logic.classify([_det("sleeping", 0.6)])[0] == "normal"
    event, conf = logic.classify([_det("sleeping", 0.7)])

    assert event == "sleeping"
    assert conf == 0.7


def test_no_presence_emits_unknown_not_sleeping() -> None:
    logic = EventLogic(EventConfig(unknown_enter_frames=3))
    empty: list[Detection] = []

    assert logic.classify(empty)[0] == "normal"
    assert logic.classify(empty)[0] == "normal"
    event, _ = logic.classify(empty)

    assert event == "unknown"


def test_presence_resets_unknown_counter() -> None:
    logic = EventLogic(EventConfig(unknown_enter_frames=3))
    empty: list[Detection] = []

    logic.classify(empty)
    logic.classify(empty)
    logic.classify([_det("face", 0.7)])
    event, _ = logic.classify(empty)

    assert event == "normal"


def test_distracted_uses_hysteresis() -> None:
    logic = EventLogic(
        EventConfig(
            distracted_enter_frames=2,
            distracted_exit_frames=1,
            min_distracted_confidence=0.5,
        )
    )

    assert logic.classify([_det("distracted", 0.8)])[0] == "normal"
    assert logic.classify([_det("distracted", 0.9)])[0] == "distracted"

    # One blank frame should keep distracted active (exit threshold = 1).
    empty: list[Detection] = []
    assert logic.classify(empty)[0] == "distracted"

    # Another blank frame should clear it.
    event, _ = logic.classify(empty)
    assert event == "normal"


def test_phone_labels_include_mobile_alias() -> None:
    logic = EventLogic(EventConfig(phone_enter_frames=1, phone_exit_frames=1))

    event, _ = logic.classify([_det("mobile", 0.75)])

    assert event == "using_phone"
