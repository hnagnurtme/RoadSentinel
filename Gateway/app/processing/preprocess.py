"""
preprocess.py – Frame preprocessing before YOLO inference.

Keeps all image-manipulation steps in one place so they're
easy to tune without touching inference or capture code.
"""

import cv2
import numpy as np
from app.utils.config import PreprocessConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


def preprocess_frame(frame: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    """
    Prepare a raw camera frame for YOLO inference.

    Steps:
    1. Resize to the configured resolution.
    2. Ensure the frame is in BGR format (YOLO expects BGR by default).

    Args:
        frame: Raw BGR frame from the capture module.
        cfg:   Preprocessing configuration (target width/height).

    Returns:
        Preprocessed BGR frame ready for inference.
    """
    target_size = (cfg.width, cfg.height)  # (width, height) for cv2.resize

    # --- Resize ---
    if frame.shape[1] != cfg.width or frame.shape[0] != cfg.height:
        frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)
        logger.debug("Resized frame to %dx%d", cfg.width, cfg.height)

    # --- Color sanity check ---
    # If grayscale (2D array), convert to BGR so YOLO receives 3 channels.
    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        logger.debug("Converted grayscale frame to BGR.")

    return frame
