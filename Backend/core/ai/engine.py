"""YOLO inference engine wrapper."""

from __future__ import annotations

import importlib.util
import logging
import pathlib
from typing import Final

logger = logging.getLogger(__name__)

MODEL_PATH: Final[pathlib.Path] = (
    pathlib.Path(__file__).parents[3] / "Simulator" / "model" / "best.pt"
)

INFER_W: Final[int] = 320
INFER_H: Final[int] = 240
CONF_THRESH: Final[float] = 0.2
SKIP_FRAMES: Final[int] = 2  # run inference every N frames
MAX_BATCH_SIZE: Final[int] = 4  # max frames to batch for inference

RELEVANT_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "drinking",
        "eyes closed",
        "looking away",
        "mobile",
        "reaching behind",
        "distracted",
        "seat belt",
        "yawning",
    }
)

_AI_AVAILABLE: bool = all(
    importlib.util.find_spec(pkg) is not None for pkg in ("cv2", "numpy", "ultralytics")
)

if not _AI_AVAILABLE:
    logger.warning("[AI] ultralytics/opencv not installed — detection disabled")


class YOLOInferenceEngine:
    """Wrapper around a YOLO model with warmup and inference helpers."""

    def __init__(self) -> None:
        self._model: object | None = None

    def load(self) -> None:
        logger.info("[AI] Starting model loading...")
        logger.info(f"[AI] AI available: {_AI_AVAILABLE}")
        logger.info(f"[AI] Model path: {MODEL_PATH}")
        logger.info(f"[AI] Model exists: {MODEL_PATH.exists()}")
        if not _AI_AVAILABLE:
            logger.error("[AI] AI libraries not available - detection disabled")
            return
        if not MODEL_PATH.exists():
            logger.error("[AI] model not found at %s — detection disabled", MODEL_PATH)
            return

        import numpy as _np  # type: ignore
        from ultralytics import YOLO as _YOLO  # type: ignore

        try:
            logger.info("[AI] Loading YOLO model...")
            self._model = _YOLO(str(MODEL_PATH))
            logger.info("[AI] Model loaded successfully")

            logger.info("[AI] Running warmup...")
            dummy = _np.zeros((INFER_H, INFER_W, 3), dtype=_np.uint8)
            self._model(dummy, verbose=False)  # type: ignore[operator]
            logger.info("[AI] Warmup completed - model ready for inference")
        except Exception as e:
            logger.error(f"[AI] Failed to load model: {e}")
            self._model = None

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def run_inference(self, jpeg_bytes: bytes) -> list[dict]:
        if not self.is_ready:
            logger.warning("[AI] Model not ready for inference")
            return []

        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        arr = _np.frombuffer(jpeg_bytes, dtype=_np.uint8)
        frame = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("[AI] Failed to decode JPEG frame")
            return []

        h, w = frame.shape[:2]
        small = _cv2.resize(frame, (INFER_W, INFER_H), interpolation=_cv2.INTER_LINEAR)
        sx, sy = w / float(INFER_W), h / float(INFER_H)

        logger.debug(
            f"[AI] Running inference on {w}x{h} frame, conf_thresh={CONF_THRESH}"
        )

        results = self._model(small, conf=CONF_THRESH, verbose=False)[0]  # type: ignore[index]
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            label = self._model.names[int(box.cls[0])]  # type: ignore[index]
            conf = float(box.conf[0])

            logger.debug(
                f"[AI] Detection: {label} conf={conf:.3f} bbox=({x1},{y1},{x2},{y2})"
            )

            detections.append(
                {
                    "label": label,
                    "conf": round(conf, 3),
                    "bbox": [int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)],
                }
            )

        logger.info(f"[AI] Found {len(detections)} detections")
        return detections

    def run_batch_inference(self, jpeg_batch: list[bytes]) -> list[list[dict]]:
        if not self.is_ready or not jpeg_batch:
            return [[] for _ in jpeg_batch]

        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        frames = []
        scales = []

        for jpeg_bytes in jpeg_batch:
            arr = _np.frombuffer(jpeg_bytes, dtype=_np.uint8)
            frame = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
            if frame is None:
                frames.append(None)
                scales.append((1.0, 1.0))
                continue

            h, w = frame.shape[:2]
            small = _cv2.resize(
                frame, (INFER_W, INFER_H), interpolation=_cv2.INTER_LINEAR
            )
            frames.append(small)
            scales.append((w / float(INFER_W), h / float(INFER_H)))

        try:
            batch_results = self._model(frames, conf=CONF_THRESH, verbose=False)  # type: ignore[operator]

            all_detections = []
            for i, results in enumerate(batch_results):
                if frames[i] is None:
                    all_detections.append([])
                    continue

                sx, sy = scales[i]
                detections = []

                for box in results.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    detections.append(
                        {
                            "label": self._model.names[int(box.cls[0])],  # type: ignore[index]
                            "conf": round(float(box.conf[0]), 3),
                            "bbox": [
                                int(x1 * sx),
                                int(y1 * sy),
                                int(x2 * sx),
                                int(y2 * sy),
                            ],
                        }
                    )
                all_detections.append(detections)

            return all_detections

        except Exception as e:
            logger.warning(f"Batch inference failed, falling back to individual: {e}")
            return [self.run_inference(jpeg) for jpeg in jpeg_batch]


inference_engine = YOLOInferenceEngine()


def filter_detections(detections: list[dict]) -> list[dict]:
    """Keep only detections whose label is in ``RELEVANT_CLASSES``, sorted by
    confidence (highest first)."""
    return sorted(
        (d for d in detections if str(d.get("label", "")).lower() in RELEVANT_CLASSES),
        key=lambda d: float(d.get("conf", d.get("confidence", 0.0))),
        reverse=True,
    )
