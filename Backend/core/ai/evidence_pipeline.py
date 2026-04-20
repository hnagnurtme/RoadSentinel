"""
core/ai/evidence_pipeline.py
-----------------------------
Evidence clip recording and alert persistence pipeline.

Key design decisions vs. the original implementation
-----------------------------------------------------
- **No direct `SessionLocal()` usage**: the pipeline receives a
  ``session_factory`` callable so it stays decoupled from the infrastructure
  layer and is independently testable.
- The Cloudinary configuration is deferred to ``_configure_cloudinary()``
  which is called exactly once during ``__init__``.
- Clip encoding and cloud upload are pure helper methods that can be tested
  or mocked independently.
"""
from __future__ import annotations

import importlib.util
import logging
import pathlib
import time
import uuid
from collections import deque
from collections.abc import Callable

from core.ai.annotator import annotate_evidence_jpeg
from domain.alert.value_objects import AlertType
from shared.config import settings

logger = logging.getLogger(__name__)

EVIDENCE_DIR: pathlib.Path = (
    pathlib.Path(__file__).parents[3] / "evidence"
)


# ── Evidence Pipeline ─────────────────────────────────────────────────────────


class DriverEvidencePipeline:
    """Records annotated JPEG frames, encodes a clip, optionally uploads it to
    Cloudinary, and persists an alert record via a provided factory callable.

    Args:
        event_key: Short identifier used in filenames/logs (e.g. ``"sleeping"``).
        alert_type: The domain-level ``AlertType`` value for this event.
        session_factory: Zero-arg callable that returns an open SQLAlchemy
            ``Session``.  Injected so the pipeline does not import or create
            sessions directly.
    """

    #: Human-readable alert messages keyed by event type.
    _MESSAGES: dict[str, str] = {
        "sleeping": "Driver sleeping detected",
        "using_phone": "Driver using phone while driving",
        "distracted": "Driver distracted — not looking at road",
        "drowsy": "Driver drowsy (yawning detected)",
    }

    def __init__(
        self,
        *,
        event_key: str,
        alert_type: AlertType,
        session_factory: Callable,
    ) -> None:
        self._event_key = event_key
        self._alert_type = alert_type
        self._session_factory = session_factory

        self._enabled: bool = settings.DRIVER_EVENT_EVIDENCE_ENABLED
        self._fps: int = max(1, settings.DRIVER_EVENT_EVIDENCE_FPS)
        self._window_seconds: int = max(1, settings.DRIVER_EVENT_EVIDENCE_SECONDS)
        self._codec: str = settings.DRIVER_EVENT_EVIDENCE_CODEC

        self._buffer: deque[bytes] = deque(maxlen=self._fps * self._window_seconds)
        self._cloudinary_ready: bool = False

        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        self._configure_cloudinary()

    # ------------------------------------------------------------------
    # Frame buffer management
    # ------------------------------------------------------------------

    def push_frame(self, jpeg_bytes: bytes) -> None:
        """Append a JPEG frame to the rolling evidence buffer."""
        if self._enabled:
            self._buffer.append(jpeg_bytes)

    def reset_buffer(self) -> None:
        """Clear the evidence buffer (called when an event starts or ends)."""
        self._buffer.clear()

    # ------------------------------------------------------------------
    # Alert persistence
    # ------------------------------------------------------------------

    def save_event_alert(self, confidence: float) -> dict | None:
        """Encode the buffered frames into a clip, upload if configured, and
        persist an alert record.

        Returns:
            A plain ``dict`` representation of the saved alert, or ``None``
            on failure or when evidence recording is disabled.
        """
        if not self._enabled:
            return None

        frames = list(self._buffer)
        if not frames:
            return None

        # Encode clip from buffered JPEG frames.
        clip_path = self._encode_clip(frames)
        evidence_url: str | None = None
        if clip_path is not None:
            local_url = (
                f"{settings.APP_PUBLIC_BASE_URL}/evidence/{clip_path.name}"
            )
            evidence_url = self._upload_cloudinary(clip_path, confidence) or local_url

        alert_message = (
            f"{self._MESSAGES.get(self._event_key, 'Driver event detected')}"
            f" (confidence={confidence:.2f})"
        )

        db = self._session_factory()
        try:
            return self._persist_alert(db, alert_message, evidence_url)
        except Exception as exc:
            logger.error(
                "Failed to create %s alert in DB: %s", self._event_key, exc, exc_info=True
            )
            return None
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Private: Cloudinary setup
    # ------------------------------------------------------------------

    def _configure_cloudinary(self) -> None:
        if not settings.DRIVER_EVENT_CLOUDINARY_ENABLED:
            return
        if importlib.util.find_spec("cloudinary") is None:
            logger.warning(
                "Cloudinary SDK not installed; evidence upload disabled"
            )
            return
        try:
            import cloudinary  # type: ignore

            cloudinary.config(
                cloud_name=settings.DRIVER_EVENT_CLOUDINARY_CLOUD_NAME,
                api_key=settings.DRIVER_EVENT_CLOUDINARY_API_KEY,
                api_secret=settings.DRIVER_EVENT_CLOUDINARY_API_SECRET,
                secure=True,
            )
            self._cloudinary_ready = True
        except Exception as exc:
            logger.error("Failed to configure Cloudinary: %s", exc)

    # ------------------------------------------------------------------
    # Private: video encoding
    # ------------------------------------------------------------------

    def _encode_clip(self, frames: list[bytes]) -> pathlib.Path | None:
        """Encode a list of JPEG frames into an MP4 clip.

        Returns the path to the written file, or ``None`` on failure.
        """
        if not frames:
            return None

        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        first = _cv2.imdecode(_np.frombuffer(frames[0], dtype=_np.uint8), _cv2.IMREAD_COLOR)
        if first is None:
            return None

        h, w = first.shape[:2]
        clip_name = (
            f"{self._event_key}_"
            f"{time.strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid.uuid4().hex[:8]}.mp4"
        )
        clip_path = EVIDENCE_DIR / clip_name

        writer = _cv2.VideoWriter(
            str(clip_path),
            _cv2.VideoWriter_fourcc(*self._codec),
            float(self._fps),
            (w, h),
        )
        if not writer.isOpened():
            clip_path.unlink(missing_ok=True)
            return None

        try:
            for jpeg in frames:
                frame = _cv2.imdecode(
                    _np.frombuffer(jpeg, dtype=_np.uint8), _cv2.IMREAD_COLOR
                )
                if frame is None:
                    continue
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = _cv2.resize(frame, (w, h), interpolation=_cv2.INTER_LINEAR)
                writer.write(frame)
        finally:
            writer.release()

        return clip_path

    # ------------------------------------------------------------------
    # Private: Cloudinary upload
    # ------------------------------------------------------------------

    def _upload_cloudinary(
        self, clip_path: pathlib.Path, confidence: float
    ) -> str | None:
        """Upload clip to Cloudinary and return the secure URL, or ``None``."""
        if not self._cloudinary_ready:
            return None
        try:
            import cloudinary.uploader  # type: ignore

            public_id = (
                f"{self._event_key}/{time.strftime('%Y-%m-%d')}/{uuid.uuid4()}"
            )
            result = cloudinary.uploader.upload(  # type: ignore
                str(clip_path),
                resource_type="video",
                public_id=public_id,
                folder=settings.DRIVER_EVENT_CLOUDINARY_FOLDER,
                overwrite=False,
                format="mp4",
                context={
                    "event": self._event_key,
                    "confidence": f"{confidence:.4f}",
                },
            )
            if isinstance(result, dict):
                return result.get("secure_url")
        except Exception as exc:
            logger.error("Cloudinary upload failed: %s", exc, exc_info=True)
        return None

    # ------------------------------------------------------------------
    # Private: DB persistence
    # ------------------------------------------------------------------

    def _persist_alert(
        self, db: object, message: str, evidence_url: str | None
    ) -> dict | None:
        """Create an alert record through the application layer and return its
        serialised form."""
        from application.alert.commands.create_alert import CreateAlertCommand
        from application.alert.commands.create_alert_handler import CreateAlertHandler
        from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl

        repository = AlertRepositoryImpl(db)  # type: ignore[arg-type]
        handler = CreateAlertHandler(repository)
        alert = handler.handle(
            CreateAlertCommand(
                message=message,
                alert_type=self._alert_type,
                device_id=settings.DRIVER_EVENT_ALERT_DEVICE_ID,
                driver_id=settings.DRIVER_EVENT_ALERT_DRIVER_ID,
                vehicle_id=settings.DRIVER_EVENT_ALERT_VEHICLE_ID,
                evidence_url=evidence_url,
                latitude=None,
                longitude=None,
            )
        )
        return {
            "_id": str(alert._id) if alert._id else None,
            "message": alert.message,
            "alert_type": alert.alert_type.value,
            "device_id": str(alert.device_id),
            "driver_id": str(alert.driver_id) if alert.driver_id else None,
            "vehicle_id": str(alert.vehicle_id) if alert.vehicle_id else None,
            "evidence_url": alert.evidence_url,
            "latitude": alert.latitude,
            "longitude": alert.longitude,
            "user": None,
            "vehicle": None,
            "_created_at": alert._created_at.isoformat() if alert._created_at else None,
            "_updated_at": alert._updated_at.isoformat() if alert._updated_at else None,
            "_deleted_at": alert._deleted_at.isoformat() if alert._deleted_at else None,
        }


# ── Factory helper ────────────────────────────────────────────────────────────


def build_evidence_pipelines(
    session_factory: Callable,
) -> tuple[DriverEvidencePipeline, DriverEvidencePipeline, DriverEvidencePipeline]:
    """Construct the sleeping, phone and distracted evidence pipelines.

    Returns:
        ``(sleep_pipeline, phone_pipeline, distracted_pipeline)``
    """
    sleep_pipeline = DriverEvidencePipeline(
        event_key="sleeping",
        alert_type=AlertType.SLEEPING,
        session_factory=session_factory,
    )
    phone_pipeline = DriverEvidencePipeline(
        event_key="using_phone",
        alert_type=AlertType.USING_PHONE,
        session_factory=session_factory,
    )
    distracted_pipeline = DriverEvidencePipeline(
        event_key="distracted",
        alert_type=AlertType.DISTRACTED,
        session_factory=session_factory,
    )
    return sleep_pipeline, phone_pipeline, distracted_pipeline
