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


def test_event_config_rejects_non_positive_sleep_threshold() -> None:
    with pytest.raises(ValueError, match="sleep_frame_threshold"):
        EventConfig(sleep_frame_threshold=0)


def test_sender_config_rejects_non_positive_queue_size() -> None:
    with pytest.raises(ValueError, match="queue_maxsize"):
        SenderConfig(queue_maxsize=0)
