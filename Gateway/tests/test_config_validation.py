import pytest

from app.utils.config import (
    CaptureConfig,
    EventConfig,
    InferenceConfig,
    PreprocessConfig,
    SenderConfig,
)


def test_capture_config_rejects_non_positive_fps() -> None:
    with pytest.raises(ValueError, match="target_fps"):
        CaptureConfig(target_fps=0)


def test_preprocess_config_rejects_invalid_dimensions() -> None:
    with pytest.raises(ValueError, match="width/height"):
        PreprocessConfig(width=0, height=240)


def test_inference_config_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="confidence_threshold"):
        InferenceConfig(confidence_threshold=1.2)

    with pytest.raises(ValueError, match="iou_threshold"):
        InferenceConfig(iou_threshold=-0.1)


def test_event_config_rejects_invalid_unknown_enter_frames() -> None:
    with pytest.raises(ValueError, match="unknown_enter_frames"):
        EventConfig(unknown_enter_frames=0)


def test_event_config_rejects_invalid_confidence_thresholds() -> None:
    with pytest.raises(ValueError, match="min_phone_confidence"):
        EventConfig(min_phone_confidence=1.1)


def test_event_config_rejects_invalid_hysteresis_pairs() -> None:
    with pytest.raises(ValueError, match="phone_exit_frames"):
        EventConfig(phone_enter_frames=2, phone_exit_frames=3)


def test_sender_config_rejects_non_positive_queue_size() -> None:
    with pytest.raises(ValueError, match="queue_maxsize"):
        SenderConfig(queue_maxsize=0)
