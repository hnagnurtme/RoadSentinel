"""
core/ai/frame_processing_pipeline.py
------------------------------------
Integrated frame processing pipeline combining all AI components.

This replaces the scattered logic in camera_websocket with a clean,
testable pipeline that follows the redesign architecture.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .alert_decision_engine import (
    AlertConfig,
    AlertDecision,
    AlertDecisionEngine,
    SessionContext,
)
from .detection_normaliser import (
    apply_confidence_gates,
    best_confidence_per_event,
    normalise,
)
from .driver_state_machine import (
    DriverStateMachine,
    DriverStateSnapshot,
    StateMachineConfig,
)
from .engine import SKIP_FRAMES, inference_engine
from .evidence_buffer import (
    EvidenceClipProcessor,
    EvidenceConfig,
    RollingEvidenceBuffer,
)
from .temporal_reasoning import TemporalConfig, TemporalReasoningEngine


@dataclass
class FrameResult:
    """Result of processing a single frame through the pipeline."""

    snapshot: DriverStateSnapshot
    alert_decision: AlertDecision
    raw_detections: List[Dict[str, Any]]  # For evidence and debugging
    should_broadcast: bool
    evidence_ready: bool  # True when evidence clip is ready for processing


@dataclass
class PipelineConfig:
    """Complete configuration for the frame processing pipeline."""

    temporal: TemporalConfig
    state_machine: StateMachineConfig
    alert: AlertConfig
    evidence: EvidenceConfig


class FrameProcessingPipeline:
    """
    Main pipeline that processes frames through all AI components.

    Pipeline flow:
      1. YOLO inference (if due)
      2. Detection normalisation
      3. Confidence gating
      4. Temporal reasoning (EWMA + dropout compensation)
      5. State machine evaluation
      6. Alert decision
      7. Evidence buffer management
    """

    def __init__(
        self,
        config: PipelineConfig,
        session: SessionContext,
        evidence_processor: Optional[EvidenceClipProcessor] = None,
    ) -> None:
        self._cfg = config
        self._session = session

        # Initialize pipeline components
        self._temporal_engine = TemporalReasoningEngine(config.temporal)
        self._state_machine = DriverStateMachine(config.state_machine)
        self._alert_engine = AlertDecisionEngine(config.alert, session)
        self._evidence_buffer = RollingEvidenceBuffer(config.evidence)
        self._evidence_processor = evidence_processor or EvidenceClipProcessor(
            config.evidence
        )

        # Frame tracking
        self._frame_idx = 0
        self._last_inference_frame = -1
        self._last_detections: List[Dict[str, Any]] = []

    def process_frame(self, jpeg_bytes: bytes, now: float) -> FrameResult:
        """
        Process a single frame through the complete pipeline.

        Args:
            jpeg_bytes: Raw JPEG frame data from ESP32-CAM
            now: Current timestamp for timing calculations

        Returns:
            FrameResult with all processing outcomes
        """
        self._frame_idx += 1

        # Step 1: YOLO inference (only on certain frames)
        raw_detections = self._run_inference_if_needed(jpeg_bytes, now)

        # Step 2: Detection normalisation
        normalised_detections = normalise(raw_detections)

        # Step 3: Best confidence per event
        event_conf = best_confidence_per_event(normalised_detections)

        # Step 4: Apply confidence gates
        gated_conf = apply_confidence_gates(
            event_conf, self._cfg.temporal.confidence_gates
        )

        # Step 5: Temporal reasoning (EWMA + dropout compensation)
        temporal_scores = self._temporal_engine.tick(gated_conf, now)

        # Step 6: State machine evaluation
        snapshot = self._state_machine.tick(temporal_scores, now)

        # Step 7: Alert decision
        alert_decision = self._alert_engine.evaluate(snapshot, now)

        # Step 8: Evidence buffer management
        evidence_ready = self._manage_evidence(
            jpeg_bytes, raw_detections, snapshot, alert_decision, now
        )

        return FrameResult(
            snapshot=snapshot,
            alert_decision=alert_decision,
            raw_detections=raw_detections,
            should_broadcast=alert_decision.should_alert,
            evidence_ready=evidence_ready,
        )

    def _run_inference_if_needed(
        self, jpeg_bytes: bytes, now: float
    ) -> List[Dict[str, Any]]:
        """Run YOLO inference only on frames that meet SKIP_FRAMES criteria."""
        if self._frame_idx % (SKIP_FRAMES + 1) != 0:
            return self._last_detections  # Use last known detections

        try:
            detections = inference_engine.run_inference(jpeg_bytes)
            self._last_detections = detections
            self._last_inference_frame = self._frame_idx
            return detections
        except Exception as e:
            # Inference failed - return empty to trigger safe state
            print(f"Inference failed on frame {self._frame_idx}: {e}")
            return []

    def _manage_evidence(
        self,
        jpeg_bytes: bytes,
        raw_detections: List[Dict[str, Any]],
        snapshot: DriverStateSnapshot,
        alert_decision: AlertDecision,
        now: float,
    ) -> bool:
        """Manage evidence buffer based on alert decisions."""

        # Always push frame to buffer (pre-event capture)
        self._evidence_buffer.push(
            jpeg_bytes=jpeg_bytes,
            detections=raw_detections,
            event=snapshot.dominant_event,
            confidence=snapshot.dominant_score,
        )

        # Trigger evidence collection if alert requires it
        if alert_decision.should_alert and alert_decision.should_save_evidence:
            if not self._evidence_buffer._triggered:  # Only trigger once per alert
                self._evidence_buffer.trigger()

        # Process evidence clip when ready
        if self._evidence_buffer.is_ready():
            # TODO: Process evidence asynchronously
            # frames = self._evidence_buffer.get_clip_frames()
            # evidence_url = self._evidence_processor.process_clip(
            #     frames, alert_id, snapshot.dominant_event
            # )
            self._evidence_buffer.reset()
            return True

        return False

    def reset(self) -> None:
        """Reset all pipeline state (call on session disconnect)."""
        self._temporal_engine.reset()
        self._state_machine.reset()
        self._alert_engine.reset()
        self._evidence_buffer.reset()
        self._frame_idx = 0
        self._last_inference_frame = -1
        self._last_detections.clear()

    @property
    def frame_idx(self) -> int:
        """Current frame index for debugging."""
        return self._frame_idx

    @property
    def current_state(self) -> str:
        """Current driver safety state for monitoring."""
        return self._state_machine._state.value


def create_pipeline_config(settings: Any) -> PipelineConfig:
    """Create pipeline configuration from settings object."""
    driver_event_cfg = settings.DRIVER_EVENT

    # Temporal config
    temporal = TemporalConfig(
        tracked_events=driver_event_cfg.temporal.tracked_events,
        confidence_gates=driver_event_cfg.temporal.confidence_gates,
        alpha_rise=driver_event_cfg.temporal.alpha_rise,
        alpha_fall=driver_event_cfg.temporal.alpha_fall,
    )

    # State machine config
    state_machine = StateMachineConfig(
        unknown_enter_seconds=driver_event_cfg.state_machine.unknown_enter_seconds,
        exit_hold_seconds=driver_event_cfg.state_machine.exit_hold_seconds,
        priority_order=driver_event_cfg.state_machine.priority_order,
        event_enter_thresholds=driver_event_cfg.state_machine.event_enter_thresholds,
        event_exit_thresholds=driver_event_cfg.state_machine.event_exit_thresholds,
        critical_duration_seconds=driver_event_cfg.state_machine.critical_duration_seconds,
        drowsy_escalation_seconds=driver_event_cfg.state_machine.drowsy_escalation_seconds,
    )

    # Alert config
    alert = AlertConfig(
        require_identified_driver=driver_event_cfg.alert.require_identified_driver,
        min_stable_seconds=driver_event_cfg.alert.min_stable_seconds,
        cooldown_seconds=driver_event_cfg.alert.cooldown_seconds,
    )

    # Evidence config
    evidence = EvidenceConfig(
        enabled=driver_event_cfg.evidence.enabled,
        fps=driver_event_cfg.evidence.fps,
        pre_event_seconds=driver_event_cfg.evidence.pre_event_seconds,
        post_event_seconds=driver_event_cfg.evidence.post_event_seconds,
        codec=driver_event_cfg.evidence.codec,
        codec_candidates=driver_event_cfg.evidence.codec_candidates,
        keep_local_after_upload=driver_event_cfg.evidence.keep_local_after_upload,
        min_severity_for_evidence=driver_event_cfg.evidence.min_severity_for_evidence,
    )

    return PipelineConfig(
        temporal=temporal,
        state_machine=state_machine,
        alert=alert,
        evidence=evidence,
    )
