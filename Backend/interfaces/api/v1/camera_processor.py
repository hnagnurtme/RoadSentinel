"""Per-frame AI processing for the camera websocket."""

from __future__ import annotations

import logging
import time
from typing import NamedTuple

from core.ai.engine import filter_detections, inference_engine
from core.ai.event_classifier import DriverEventClassifier, WindowTrigger
from core.ai.evidence_pipeline import build_evidence_pipelines
from core.ai.performance_monitor import performance_monitor
from infrastructure.db.session import SessionLocal
from shared.config import settings

logger = logging.getLogger(__name__)


class _GraceTracker(NamedTuple):
    """Tracks a grace window for the last active event."""

    expires_at: float  # absolute monotonic deadline (0.0 = already expired)
    active_event: str | None = None


class FrameResult(NamedTuple):
    """Result of processing a single frame."""

    event: str | None
    confidence: float
    escalated: bool
    detections: list[dict]
    should_broadcast: bool
    should_save_evidence: bool
    all_events: list[str] = []


class CameraFrameProcessor:
    """Encapsulates the per-frame AI pipeline state."""

    def __init__(self) -> None:
        self.event_logic = DriverEventClassifier()

        self._setup_evidence_pipelines()

        self.sleep_trigger = WindowTrigger(
            fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
            window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
            occupancy_threshold=0.9,
        )
        self.phone_trigger = WindowTrigger(
            fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
            window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
            occupancy_threshold=0.9,
        )
        self.distracted_trigger = WindowTrigger(
            fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
            window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
            occupancy_threshold=0.7,
        )

        self.sleep_grace = _GraceTracker(expires_at=0.0)
        self.phone_grace = _GraceTracker(expires_at=0.0)
        self.distracted_grace = _GraceTracker(expires_at=0.0)

        self.last_event: str | None = None
        self.last_broadcast_time: float = 0.0

        self.pipelines = {
            "sleeping": self.sleep_pipeline,
            "using_phone": self.phone_pipeline,
            "distracted": self.distracted_pipeline,
        }

    def _setup_evidence_pipelines(self) -> None:
        from interfaces.api.v1.websocket import create_save_alert_function

        sleep_save_alert = create_save_alert_function("sleeping")
        phone_save_alert = create_save_alert_function("using_phone")
        distracted_save_alert = create_save_alert_function("distracted")

        self.sleep_pipeline, self.phone_pipeline, self.distracted_pipeline = (
            build_evidence_pipelines(SessionLocal, save_alert=None)
        )

        self.sleep_pipeline._save_alert = sleep_save_alert
        self.phone_pipeline._save_alert = phone_save_alert
        self.distracted_pipeline._save_alert = distracted_save_alert

    def process_frame(
        self, jpeg_bytes: bytes, frame_idx: int, now: float
    ) -> FrameResult:
        processing_start = time.time()
        frame_size = len(jpeg_bytes)

        skip_factor = self._get_adaptive_skip_factor(now)

        if frame_idx % (skip_factor + 1) != 0:
            processing_time = (time.time() - processing_start) * 1000
            performance_monitor.record_frame(
                processing_time_ms=processing_time,
                inference_time_ms=0.0,
                detection_count=0,
                frame_size_bytes=frame_size,
                skipped=True,
            )
            return FrameResult(
                event=None,
                confidence=0.0,
                escalated=False,
                detections=[],
                should_broadcast=False,
                should_save_evidence=False,
            )

        inference_start = time.time()
        try:
            detections = inference_engine.run_inference(jpeg_bytes)
            inference_time = (time.time() - inference_start) * 1000
        except Exception as e:
            inference_time = (time.time() - inference_start) * 1000
            performance_monitor.record_error()
            logger.error(f"AI inference failed: {e}")
            detections = []

        filtered = filter_detections(detections)

        event, confidence, all_active = self.event_logic.classify(filtered, now)

        escalated = (
            event == "drowsy"
            and self.event_logic.get_drowsy_duration(now)
            >= settings.DRIVER_EVENT_DROWSY_ESCALATION_SECONDS
        )

        should_save_evidence = self._update_evidence_pipelines(
            event, confidence, jpeg_bytes, filtered, now, all_active
        )

        should_broadcast = self._should_broadcast_event(event, now)

        self._update_grace_trackers(event, now)

        self.last_event = event
        if should_broadcast:
            self.last_broadcast_time = now

        processing_time = (time.time() - processing_start) * 1000
        performance_monitor.record_frame(
            processing_time_ms=processing_time,
            inference_time_ms=inference_time,
            detection_count=len(filtered),
            frame_size_bytes=frame_size,
            skipped=False,
        )

        return FrameResult(
            event=event,
            confidence=confidence,
            escalated=escalated,
            detections=filtered,
            should_broadcast=should_broadcast,
            should_save_evidence=should_save_evidence,
            all_events=all_active,
        )

    def _update_evidence_pipelines(
        self,
        event: str | None,
        confidence: float,
        jpeg_bytes: bytes,
        detections: list[dict],
        now: float,
        all_active: list[str] | None = None,
    ) -> bool:
        should_save = False

        display_event = event
        if all_active and len(all_active) > 1:
            display_event = " + ".join(all_active)

        for pipeline in self.pipelines.values():
            pipeline.push_frame(
                jpeg_bytes=jpeg_bytes,
                detections=detections,
                event=display_event,
                duration_ms=0,
                confidence=confidence,
            )

        if event == "sleeping":
            should_save = self.sleep_trigger.update(True)  # Event detected

        elif event == "using_phone":
            should_save = self.phone_trigger.update(True)  # Event detected

        elif event == "distracted":
            should_save = self.distracted_trigger.update(True)  # Event detected
        else:
            self.sleep_trigger.update(False)
            self.phone_trigger.update(False)
            self.distracted_trigger.update(False)

        return should_save

    def _should_broadcast_event(self, event: str | None, now: float) -> bool:
        if event is None:
            return False

        time_since_broadcast = now - self.last_broadcast_time
        if time_since_broadcast < settings.DRIVER_EVENT_ALERT_COOLDOWN_SECONDS:
            return False

        if event == "sleeping":
            return True

        elif event == "using_phone":
            if self.sleep_grace.active_event == "sleeping":
                return False
            return True

        elif event == "distracted":
            if self.sleep_grace.active_event in {"sleeping", "using_phone"}:
                return False
            if self.phone_grace.active_event == "using_phone":
                return False
            return True

        elif event == "drowsy":
            if (
                self.sleep_grace.active_event == "sleeping"
                or self.phone_grace.active_event == "using_phone"
                or self.distracted_grace.active_event == "distracted"
            ):
                return False
            return True

        return False

    def _update_grace_trackers(self, event: str | None, now: float) -> None:
        if event == "sleeping":
            self.sleep_grace = _GraceTracker(
                expires_at=now + settings.DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS,
                active_event="sleeping",
            )
        elif self.sleep_grace.active_event and now >= self.sleep_grace.expires_at:
            self.sleep_grace = _GraceTracker(expires_at=0.0, active_event=None)

        if event == "using_phone":
            self.phone_grace = _GraceTracker(
                expires_at=now + settings.DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS,
                active_event="using_phone",
            )
        elif self.phone_grace.active_event and now >= self.phone_grace.expires_at:
            self.phone_grace = _GraceTracker(expires_at=0.0, active_event=None)

        if event == "distracted":
            self.distracted_grace = _GraceTracker(
                expires_at=now + settings.DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS,
                active_event="distracted",
            )
        elif (
            self.distracted_grace.active_event
            and now >= self.distracted_grace.expires_at
        ):
            self.distracted_grace = _GraceTracker(expires_at=0.0, active_event=None)

    def _get_adaptive_skip_factor(self, now: float) -> int:
        base_skip = 2

        if now - self.last_broadcast_time > 10.0:  # 10 seconds without events
            return max(0, base_skip - 1)

        return base_skip

    def reset(self) -> None:
        self.event_logic.reset()
        self.last_event = None
        self.last_broadcast_time = 0.0
        self.sleep_grace = _GraceTracker(expires_at=0.0)
        self.phone_grace = _GraceTracker(expires_at=0.0)
        self.distracted_grace = _GraceTracker(expires_at=0.0)
