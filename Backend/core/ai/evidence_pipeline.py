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
from typing import Any, TypedDict

from core.ai.annotator import annotate_evidence_frame
from domain.alert.value_objects import AlertType
from shared.config import settings

logger = logging.getLogger(__name__)

EVIDENCE_DIR: pathlib.Path = (
    pathlib.Path(__file__).parents[3] / "evidence"
)


class EvidenceFramePacket(TypedDict):
    jpeg_bytes: bytes
    detections: list[dict]
    event: str
    duration_ms: int
    confidence: float


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
        self._codec_candidates: list[str] = [
            codec.strip()
            for codec in settings.DRIVER_EVENT_EVIDENCE_CODEC_CANDIDATES
            if isinstance(codec, str) and codec.strip()
        ]
        if self._codec not in self._codec_candidates:
            self._codec_candidates.append(self._codec)

        self._buffer: deque[EvidenceFramePacket] = deque(
            maxlen=self._fps * self._window_seconds
        )
        self._cloudinary_ready: bool = False

        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        self._configure_cloudinary()

    # ------------------------------------------------------------------
    # Frame buffer management
    # ------------------------------------------------------------------

    def push_frame(
        self,
        jpeg_bytes: bytes,
        *,
        detections: list[dict] | None = None,
        event: str | None = None,
        duration_ms: int = 0,
        confidence: float = 0.0,
    ) -> None:
        """Append a frame to the rolling evidence buffer.

        The hot streaming path can pass raw JPEG bytes only. When metadata is
        provided, clip encoding will add overlays (bbox + event banner).
        """
        if self._enabled:
            self._buffer.append(
                {
                    "jpeg_bytes": jpeg_bytes,
                    "detections": [dict(det) for det in (detections or [])],
                    "event": event or self._event_key,
                    "duration_ms": max(0, int(duration_ms)),
                    "confidence": float(confidence),
                }
            )

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

        packets = list(self._buffer)
        if not packets:
            return None

        # Encode clip from buffered JPEG frames.
        clip_path = self._encode_clip(packets)
        evidence_url: str | None = None
        if clip_path is not None:
            local_url = (
                f"{settings.APP_PUBLIC_BASE_URL}/evidence/{clip_path.name}"
            )
            uploaded_url = self._upload_cloudinary(clip_path, confidence)
            if uploaded_url:
                evidence_url = uploaded_url
                if not settings.DRIVER_EVENT_EVIDENCE_KEEP_LOCAL_AFTER_UPLOAD:
                    try:
                        clip_path.unlink(missing_ok=True)
                    except Exception:
                        logger.warning(
                            "Uploaded evidence to Cloudinary but failed to remove local file: %s",
                            clip_path,
                            exc_info=True,
                        )
            else:
                evidence_url = local_url

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

    def _encode_clip(self, packets: list[EvidenceFramePacket]) -> pathlib.Path | None:
        """Encode buffered frames into an MP4 clip.

        Each frame is annotated lazily at save-time so the real-time websocket
        loop is not blocked by cv2 drawing work.

        Returns the path to the written file, or ``None`` on failure.
        """
        if not packets:
            return None

        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        decoded_packets: list[tuple[EvidenceFramePacket, Any]] = []
        for packet in packets:
            frame = _cv2.imdecode(
                _np.frombuffer(packet["jpeg_bytes"], dtype=_np.uint8),
                _cv2.IMREAD_COLOR,
            )
            if frame is None:
                continue
            decoded_packets.append((packet, frame))

        if not decoded_packets:
            logger.warning("Evidence encode skipped: no decodable frames in buffer")
            return None

        first = decoded_packets[0][1]
        h, w = first.shape[:2]
        clip_name = (
            f"{self._event_key}_"
            f"{time.strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid.uuid4().hex[:8]}.mp4"
        )
        clip_path = EVIDENCE_DIR / clip_name

        writer, selected_codec = self._resolve_writer(_cv2, clip_path, w, h)
        if writer is None:
            clip_path.unlink(missing_ok=True)
            return None
        logger.info("Evidence encoder selected codec=%s", selected_codec)

        written_frames = 0
        try:
            for packet, frame in decoded_packets:
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = _cv2.resize(frame, (w, h), interpolation=_cv2.INTER_LINEAR)

                annotate_evidence_frame(
                    frame,
                    detections=packet["detections"],
                    event=packet["event"],
                    duration_ms=packet["duration_ms"],
                    confidence=packet["confidence"],
                )
                writer.write(frame)
                written_frames += 1
        finally:
            writer.release()

        if written_frames == 0:
            logger.warning("Evidence encode failed: writer opened but no frames were written")
            clip_path.unlink(missing_ok=True)
            return None

        return clip_path

    def _resolve_writer(
        self, cv2: object, clip_path: pathlib.Path, width: int, height: int
    ) -> tuple[Any | None, str | None]:
        """Try configured codecs in order and return the first working writer."""
        tried: list[str] = []
        for codec in self._codec_candidates:
            if len(codec) != 4:
                continue
            tried.append(codec)
            writer = cv2.VideoWriter(  # type: ignore[attr-defined]
                str(clip_path),
                cv2.VideoWriter_fourcc(*codec),  # type: ignore[attr-defined]
                float(self._fps),
                (width, height),
            )
            if writer.isOpened():
                return writer, codec
            writer.release()

        logger.warning(
            "No evidence codec available from candidates: %s. Install/enable FFmpeg or switch codec list.",
            ",".join(tried),
        )
        return None, None

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
