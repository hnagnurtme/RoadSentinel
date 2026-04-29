"""
core/ai/driver_state_machine.py
-----------------------------------
Driver state machine implementing NORMAL→DROWSY→DANGEROUS→CRITICAL transitions.

This replaces the current per-event grace period logic with a unified
state machine that provides explicit business rule alignment and
deterministic conflict resolution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class DriverSafetyState(str, Enum):
    """Driver safety levels representing immediate physical danger."""

    UNKNOWN = "UNKNOWN"
    NORMAL = "NORMAL"
    DROWSY = "DROWSY"
    DANGEROUS = "DANGEROUS"
    CRITICAL = "CRITICAL"


@dataclass
class ActiveEvent:
    """An event that is currently active with duration tracking."""

    name: str
    score: float
    started_at: float
    duration_seconds: float = 0.0


@dataclass
class DriverStateSnapshot:
    """Output of the state machine for one tick. Immutable after creation."""

    state: DriverSafetyState
    dominant_event: str  # e.g. "sleeping", "using_phone"
    dominant_score: float  # 0.0–1.0
    active_events: List[ActiveEvent]
    state_duration_seconds: float
    drowsy_duration_seconds: float
    escalated: bool  # True when DROWSY has lasted >= escalation threshold
    now: float


@dataclass
class StateMachineConfig:
    """Configuration for driver state machine."""

    unknown_enter_seconds: float = 5.0
    exit_hold_seconds: float = 3.0  # prevent rapid state drops
    priority_order: List[str] = field(
        default_factory=lambda: ["sleeping", "using_phone", "distracted", "drowsy"]
    )
    event_enter_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "sleeping": 0.55,
            "drowsy": 0.50,
            "using_phone": 0.52,
            "distracted": 0.48,
        }
    )
    event_exit_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "sleeping": 0.30,
            "drowsy": 0.28,
            "using_phone": 0.30,
            "distracted": 0.25,
        }
    )
    # Seconds in DANGEROUS state before escalating to CRITICAL
    critical_duration_seconds: Dict[str, float] = field(
        default_factory=lambda: {
            "sleeping": 5.0,  # 5 seconds sleeping = CRITICAL immediately
            "using_phone": 10.0,
            "distracted": 20.0,
        }
    )
    drowsy_escalation_seconds: float = 30.0


class DriverStateMachine:
    """Resolves per-event scores into a single driver safety state."""

    def __init__(self, config: StateMachineConfig) -> None:
        self._cfg = config
        self._state = DriverSafetyState.NORMAL
        self._state_entered_at: float = 0.0
        self._drowsy_started_at: Optional[float] = None
        self._no_presence_since: Optional[float] = None
        self._active_events: Dict[str, ActiveEvent] = {}

    def tick(
        self,
        scores: Dict[str, float],
        now: float,
    ) -> DriverStateSnapshot:
        has_presence = any(
            scores.get(e, 0.0) > 0.0
            for e in ("sleeping", "drowsy", "using_phone", "distracted", "normal")
        )
        if not has_presence:
            if self._no_presence_since is None:
                self._no_presence_since = now
            if now - self._no_presence_since >= self._cfg.unknown_enter_seconds:
                return self._transition(DriverSafetyState.UNKNOWN, scores, now)
        else:
            self._no_presence_since = None

        cfg = self._cfg
        for event, threshold in cfg.event_enter_thresholds.items():
            score = scores.get(event, 0.0)
            if score >= threshold:
                if event not in self._active_events:
                    self._active_events[event] = ActiveEvent(
                        name=event, score=score, started_at=now
                    )
                else:
                    ae = self._active_events[event]
                    ae.score = score
                    ae.duration_seconds = now - ae.started_at
            else:
                exit_threshold = cfg.event_exit_thresholds.get(event, threshold * 0.7)
                if score < exit_threshold:
                    self._active_events.pop(event, None)

        if "drowsy" in self._active_events:
            if self._drowsy_started_at is None:
                self._drowsy_started_at = now
        else:
            self._drowsy_started_at = None

        drowsy_duration = (
            now - self._drowsy_started_at
            if self._drowsy_started_at is not None
            else 0.0
        )
        escalated = drowsy_duration >= cfg.drowsy_escalation_seconds

        sleeping_active = "sleeping" in self._active_events
        phone_active = "using_phone" in self._active_events
        distracted_active = "distracted" in self._active_events
        drowsy_active = "drowsy" in self._active_events

        current_duration = now - self._state_entered_at

        if sleeping_active:
            if current_duration >= cfg.critical_duration_seconds.get("sleeping", 5.0):
                target = DriverSafetyState.CRITICAL
            else:
                target = DriverSafetyState.DANGEROUS

        elif phone_active:
            if current_duration >= cfg.critical_duration_seconds.get(
                "using_phone", 10.0
            ):
                target = DriverSafetyState.CRITICAL
            else:
                target = DriverSafetyState.DANGEROUS

        elif escalated:
            target = DriverSafetyState.DANGEROUS

        elif drowsy_active:
            target = DriverSafetyState.DROWSY

        elif distracted_active:
            if current_duration >= cfg.critical_duration_seconds.get(
                "distracted", 15.0
            ):
                target = DriverSafetyState.DANGEROUS
            else:
                target = DriverSafetyState.DROWSY

        else:
            target = DriverSafetyState.NORMAL

        if self._is_downgrade(self._state, target):
            if current_duration < cfg.exit_hold_seconds:
                target = self._state

        return self._transition(target, scores, now)

    def _is_downgrade(
        self, current: DriverSafetyState, target: DriverSafetyState
    ) -> bool:
        """Check if target state is lower priority than current state."""
        order = [
            DriverSafetyState.UNKNOWN,
            DriverSafetyState.NORMAL,
            DriverSafetyState.DROWSY,
            DriverSafetyState.DANGEROUS,
            DriverSafetyState.CRITICAL,
        ]
        return order.index(target) < order.index(current)

    def _transition(
        self,
        target: DriverSafetyState,
        scores: Dict[str, float],
        now: float,
    ) -> DriverStateSnapshot:
        """Execute state transition and return snapshot."""
        if target != self._state:
            self._state = target
            self._state_entered_at = now

        dominant_event, dominant_score = self._resolve_dominant(scores)

        drowsy_duration = (
            now - self._drowsy_started_at if self._drowsy_started_at else 0.0
        )
        escalated = drowsy_duration >= self._cfg.drowsy_escalation_seconds

        return DriverStateSnapshot(
            state=self._state,
            dominant_event=dominant_event,
            dominant_score=dominant_score,
            active_events=list(self._active_events.values()),
            state_duration_seconds=now - self._state_entered_at,
            drowsy_duration_seconds=drowsy_duration,
            escalated=escalated,
            now=now,
        )

    def _resolve_dominant(self, scores: Dict[str, float]) -> tuple[str, float]:
        """
        Return the highest-priority active event and its score.
        Priority order: sleeping > using_phone > distracted > drowsy
        """
        for event in self._cfg.priority_order:
            if event in self._active_events:
                return event, self._active_events[event].score
        if self._active_events:
            best = max(self._active_events.values(), key=lambda e: e.score)
            return best.name, best.score
        return "normal", 0.0

    def reset(self) -> None:
        """Reset all state (call on session disconnect)."""
        self._state = DriverSafetyState.NORMAL
        self._state_entered_at = 0.0
        self._drowsy_started_at = None
        self._no_presence_since = None
        self._active_events.clear()
