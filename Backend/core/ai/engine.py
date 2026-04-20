"""
core/ai/engine.py
-----------------
YOLO inference engine wrapper.

Responsibilities:
- Model loading with optional warmup
- Thread-safe inference (designed to run in executor)
- Graceful fallback when AI libraries are not installed
"""
from __future__ import annotations

import importlib.util
import logging
import pathlib
from typing import Final

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MODEL_PATH: Final[pathlib.Path] = (
    pathlib.Path(__file__).parents[3] / "AI" / "model" / "best.pt"
)

INFER_W: Final[int] = 320
INFER_H: Final[int] = 240
CONF_THRESH: Final[float] = 0.4
SKIP_FRAMES: Final[int] = 2  # run inference every N frames

#: Exact label strings output by the YOLO model (lowercased for matching).
#: These were measured from the training set:
#:   Distracted  12.4%  |  Drinking    2.2%  |  Eyes Closed  23.0%
#:   Mobile      13.7%  |  Seat Belt  21.2%  |  Yawning      27.5%
RELEVANT_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "distracted",   # driver not looking at road
        "drinking",     # consuming beverage while driving
        "eyes closed",  # direct sleeping indicator
        "mobile",       # phone in hand / at ear
        "seat belt",    # safety-belt violation
        "yawning",      # fatigue / drowsy indicator
    }
)

# ── AI availability check ─────────────────────────────────────────────────────

_AI_AVAILABLE: bool = all(
    importlib.util.find_spec(pkg) is not None
    for pkg in ("cv2", "numpy", "ultralytics")
)

if not _AI_AVAILABLE:
    logger.warning("[AI] ultralytics/opencv not installed — detection disabled")


# ── Inference Engine ──────────────────────────────────────────────────────────


class YOLOInferenceEngine:
    """Wrapper around a YOLO model that handles loading, warmup, and inference.

    Designed to be instantiated once at application startup and shared across
    all WebSocket sessions. All public methods are safe to call from a thread
    pool executor.
    """

    def __init__(self) -> None:
        self._model: object | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load the YOLO model and run a warmup pass.

        Call this from the FastAPI lifespan handler via
        ``asyncio.to_thread(engine.load)``.
        Calling ``load()`` when AI libs are unavailable or the model file is
        missing is a no-op (a warning is logged).
        """
        if not _AI_AVAILABLE:
            return
        if not MODEL_PATH.exists():
            logger.warning("[AI] model not found at %s — detection disabled", MODEL_PATH)
            return

        from ultralytics import YOLO as _YOLO  # type: ignore
        import numpy as _np  # type: ignore

        self._model = _YOLO(str(MODEL_PATH))

        # Warmup — avoids latency spike on the first real frame.
        dummy = _np.zeros((INFER_H, INFER_W, 3), dtype=_np.uint8)
        self._model(dummy, verbose=False)  # type: ignore[operator]
        logger.info("[AI] YOLO model loaded from %s", MODEL_PATH)

    @property
    def is_ready(self) -> bool:
        """Return ``True`` when the model is loaded and ready for inference."""
        return self._model is not None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def run_inference(self, jpeg_bytes: bytes) -> list[dict]:
        """Decode a JPEG frame, run YOLO and return raw detections.

        Returns:
            List of ``{label: str, conf: float, bbox: [x1, y1, x2, y2]}``
            dicts, scaled back to the *original* frame resolution.
            Returns ``[]`` when the engine is not ready or the frame is
            undecodeable.
        """
        if not self.is_ready:
            return []

        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        arr = _np.frombuffer(jpeg_bytes, dtype=_np.uint8)
        frame = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
        if frame is None:
            return []

        h, w = frame.shape[:2]
        small = _cv2.resize(frame, (INFER_W, INFER_H), interpolation=_cv2.INTER_LINEAR)
        sx, sy = w / float(INFER_W), h / float(INFER_H)

        results = self._model(small, conf=CONF_THRESH, verbose=False)[0]  # type: ignore[index]

        detections: list[dict] = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            detections.append(
                {
                    "label": self._model.names[int(box.cls[0])],  # type: ignore[index]
                    "conf": round(float(box.conf[0]), 3),
                    "bbox": [int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)],
                }
            )
        return detections


# ── Module-level singleton ────────────────────────────────────────────────────

#: Shared engine instance — import and use this everywhere.
inference_engine = YOLOInferenceEngine()


# ── Helper functions ──────────────────────────────────────────────────────────


def filter_detections(detections: list[dict]) -> list[dict]:
    """Keep only detections whose label is in ``RELEVANT_CLASSES``, sorted by
    confidence (highest first)."""
    return sorted(
        (d for d in detections if str(d.get("label", "")).lower() in RELEVANT_CLASSES),
        key=lambda d: float(d.get("conf", d.get("confidence", 0.0))),
        reverse=True,
    )
