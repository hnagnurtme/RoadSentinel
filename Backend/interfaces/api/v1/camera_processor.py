"""
interfaces/api/v1/camera_processor.py
-----------------------------------
CameraFrameProcessor class encapsulates per-frame AI processing state and logic.

Extracted from camera_websocket to improve testability and follow Single Responsibility Principle.
"""

from __future__ import annotations

from typing import NamedTuple

from core.ai.engine import SKIP_FRAMES, filter_detections, inference_engine
from core.ai.event_classifier import DriverEventClassifier, WindowTrigger
from core.ai.evidence_pipeline import build_evidence_pipelines
from infrastructure.db.session import SessionLocal
from shared.config import settings


class _GraceTracker(NamedTuple):
    """Simple grace period tracker for event state transitions."""

    expires_at: float
    active_event: str | None = None


class FrameResult(NamedTuple):
    """Result of processing a single frame."""

    event: str | None
    confidence: float
    escalated: bool
    detections: list[dict]
    should_broadcast: bool
    should_save_evidence: bool


class CameraFrameProcessor:
    """Encapsulates per-frame AI processing state and logic.

    This class manages:
    - Event classification logic
    - Evidence pipeline state
    - Grace period tracking
    - Window trigger evaluation
    - Alert generation
    """

    def __init__(self) -> None:
        # Core AI components
        self.event_logic = DriverEventClassifier()

        # Evidence pipelines with injected save_alert functions
        self._setup_evidence_pipelines()

        # Window triggers for evidence collection
        self.sleep_trigger = WindowTrigger(
            fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
            window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
            occupancy_threshold=0.9,  # Lowered from 1.0 to prevent single missed frames from resetting trigger
        )
        self.phone_trigger = WindowTrigger(
            fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
            window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
            occupancy_threshold=0.9,  # Lowered from 1.0 to prevent single missed frames from resetting trigger
        )
        self.distracted_trigger = WindowTrigger(
            fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
            window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
            occupancy_threshold=0.7,
        )

        # Grace period trackers to prevent flickering
        self.sleep_grace = _GraceTracker(
            settings.DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS
        )
        self.phone_grace = _GraceTracker(
            settings.DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS
        )
        self.distracted_grace = _GraceTracker(
            settings.DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS
        )

        # State tracking
        self.last_event: str | None = None
        self.last_broadcast_time: float = 0.0
        self.evidence_buffers: dict[str, list] = {
            "sleeping": [],
            "using_phone": [],
            "distracted": [],
        }

    def _setup_evidence_pipelines(self) -> None:
        """Initialize evidence pipelines with proper save_alert functions."""
        from interfaces.api.v1.websocket import create_save_alert_function

        sleep_save_alert = create_save_alert_function("sleeping")
        phone_save_alert = create_save_alert_function("using_phone")
        distracted_save_alert = create_save_alert_function("distracted")

        self.sleep_pipeline, self.phone_pipeline, self.distracted_pipeline = (
            build_evidence_pipelines(SessionLocal, save_alert=None)
        )

        # Inject individual save_alert functions
        self.sleep_pipeline._save_alert = sleep_save_alert
        self.phone_pipeline._save_alert = phone_save_alert
        self.distracted_pipeline._save_alert = distracted_save_alert

    def process_frame(
        self, jpeg_bytes: bytes, frame_idx: int, now: float
    ) -> FrameResult:
        """Process a single frame and return the result.

        Args:
            jpeg_bytes: Raw JPEG frame data from ESP32-CAM
            frame_idx: Current frame index for debugging/logging
            now: Current timestamp for cooldown calculations

        Returns:
            FrameResult containing processing outcomes
        """
        # Skip frames for performance
        if frame_idx % (SKIP_FRAMES + 1) != 0:
            return FrameResult(
                event=None,
                confidence=0.0,
                escalated=False,
                detections=[],
                should_broadcast=False,
                should_save_evidence=False,
            )

        # Run AI inference
        detections = inference_engine(jpeg_bytes)
        filtered = filter_detections(detections)

        # Classify driver event
        event, confidence = self.event_logic.classify(filtered, now)

        # Check for drowsy escalation
        escalated = (
            event == "drowsy"
            and self.event_logic.get_drowsy_duration(now)
            >= settings.DRIVER_EVENT_DROWSY_ESCALATION_SECONDS
        )

        # Update evidence buffers and triggers
        should_save_evidence = self._update_evidence_pipelines(
            event, confidence, jpeg_bytes, filtered, now
        )

        # Determine if we should broadcast (cooldown logic)
        should_broadcast = self._should_broadcast_event(event, now)

        # Update grace period trackers
        self._update_grace_trackers(event, now)

        # Store last event for next iteration
        self.last_event = event
        if should_broadcast:
            self.last_broadcast_time = now

        return FrameResult(
            event=event,
            confidence=confidence,
            escalated=escalated,
            detections=filtered,
            should_broadcast=should_broadcast,
            should_save_evidence=should_save_evidence,
        )

    def _update_evidence_pipelines(
        self,
        event: str | None,
        confidence: float,
        jpeg_bytes: bytes,
        detections: list[dict],
        now: float,
    ) -> bool:
        """Update evidence pipelines and check if any should save evidence."""
        should_save = False

        # Update appropriate pipeline based on event
        if event == "sleeping":
            self.sleep_pipeline.add_frame(
                jpeg_bytes=jpeg_bytes,
                detections=detections,
                event=event,
                duration_ms=int(confidence * 1000),
                confidence=confidence,
            )
            should_save = self.sleep_trigger.tick(event, now)
            if should_save:
                self.sleep_pipeline.save_evidence(now)

        elif event == "using_phone":
            self.phone_pipeline.add_frame(
                jpeg_bytes=jpeg_bytes,
                detections=detections,
                event=event,
                duration_ms=int(confidence * 1000),
                confidence=confidence,
            )
            should_save = self.phone_trigger.tick(event, now)
            if should_save:
                self.phone_pipeline.save_evidence(now)

        elif event == "distracted":
            self.distracted_pipeline.add_frame(
                jpeg_bytes=jpeg_bytes,
                detections=detections,
                event=event,
                duration_ms=int(confidence * 1000),
                confidence=confidence,
            )
            should_save = self.distracted_trigger.tick(event, now)
            if should_save:
                self.distracted_pipeline.save_evidence(now)

        return should_save

    def _should_broadcast_event(self, event: str | None, now: float) -> bool:
        """Determine if event should be broadcast based on cooldown and grace periods."""
        if event is None:
            return False

        # Check cooldown
        time_since_broadcast = now - self.last_broadcast_time
        if time_since_broadcast < settings.DRIVER_EVENT_ALERT_COOLDOWN_SECONDS:
            return False

        # Check grace periods - higher priority events override lower priority grace
        if event == "sleeping":
            return True  # Highest priority, no grace check needed

        elif event == "using_phone":
            # Phone can't broadcast during sleeping grace
            if self.sleep_grace.active_event == "sleeping":
                return False
            return True

        elif event == "distracted":
            # Distracted can't broadcast during sleeping or phone grace
            if self.sleep_grace.active_event in {"sleeping", "using_phone"}:
                return False
            if self.phone_grace.active_event == "using_phone":
                return False
            return True

        elif event == "drowsy":
            # Drowsy can't broadcast during higher priority grace periods
            if (
                self.sleep_grace.active_event == "sleeping"
                or self.phone_grace.active_event == "using_phone"
                or self.distracted_grace.active_event == "distracted"
            ):
                return False
            return True

        return False

    def _update_grace_trackers(self, event: str | None, now: float) -> None:
        """Update grace period trackers based on current event."""
        # Update sleeping grace
        if event == "sleeping":
            self.sleep_grace = _GraceTracker(
                settings.DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS,
                active_event="sleeping",
            )
        elif self.sleep_grace.active_event and now >= self.sleep_grace.expires_at:
            self.sleep_grace = _GraceTracker(
                settings.DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS, active_event=None
            )

        # Update phone grace
        if event == "using_phone":
            self.phone_grace = _GraceTracker(
                settings.DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS,
                active_event="using_phone",
            )
        elif self.phone_grace.active_event and now >= self.phone_grace.expires_at:
            self.phone_grace = _GraceTracker(
                settings.DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS, active_event=None
            )

        # Update distracted grace
        if event == "distracted":
            self.distracted_grace = _GraceTracker(
                settings.DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS,
                active_event="distracted",
            )
        elif (
            self.distracted_grace.active_event
            and now >= self.distracted_grace.expires_at
        ):
            self.distracted_grace = _GraceTracker(
                settings.DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS,
                active_event=None,
            )

    def reset(self) -> None:
        """Reset all internal state (call on ESP32 disconnect)."""
        self.event_logic.reset()
        self.last_event = None
        self.last_broadcast_time = 0.0
        self.sleep_grace = _GraceTracker(
            settings.DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS
        )
        self.phone_grace = _GraceTracker(
            settings.DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS
        )
        self.distracted_grace = _GraceTracker(
            settings.DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS
        )

        # Clear evidence buffers
        self.evidence_buffers = {
            "sleeping": [],
            "using_phone": [],
            "distracted": [],
        }
