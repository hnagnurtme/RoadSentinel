"""
model.py – YOLO model loader (singleton pattern).

The model is loaded exactly once and reused across frames, avoiding the
overhead of re-initialising the weights on every inference call.
"""

from app.utils.config import InferenceConfig
from app.utils.logger import get_logger
from ultralytics import YOLO

logger = get_logger(__name__)

_model_instance: YOLO | None = None


def load_model(cfg: InferenceConfig) -> YOLO:
    """
    Load and return the YOLO model, creating the instance only once.

    Args:
        cfg: Inference configuration (model path, device, etc.)

    Returns:
        Loaded YOLO model ready for inference.
    """
    global _model_instance
    if _model_instance is None:
        logger.info(
            "Loading YOLO model from '%s' on device='%s'",
            cfg.model_path,
            cfg.device,
        )
        _model_instance = YOLO(cfg.model_path)
        # Move to the configured device
        _model_instance.to(cfg.device)
        logger.info("Model loaded successfully.")
    return _model_instance


def get_model() -> YOLO:
    """
    Return the already-loaded model instance.

    Raises:
        RuntimeError: if load_model() has not been called yet.
    """
    if _model_instance is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return _model_instance
