"""
core/ai/alert_decision_engine.py
-----------------------------------
Alert decision engine separating detection logic from alert business rules.

This replaces the current alert generation logic spread across the
websocket handler with a clean, testable decision engine.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict
import uuid

from .driver_state_machine import DriverStateSnapshot, DriverSafetyState


class AlertSeverity(str, Enum):
    """Alert severity levels matching business requirements."""
    INFO     = "INFO"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class AlertDecision:
    """Decision result for a single driver state snapshot."""
    should_alert: bool
    severity: Optional[AlertSeverity]
    should_save_evidence: bool
    should_send_device_command: bool   # e.g. buzzer on ESP32
    reason: str                        # human-readable, for logs


@dataclass
class AlertConfig:
    """Configuration for alert decision engine."""
    require_identified_driver: bool = False
    min_stable_seconds: Dict[str, float] = None
    cooldown_seconds: Dict[str, float] = None
    
    def __post_init__(self):
        if self.min_stable_seconds is None:
            self.min_stable_seconds = {
                "sleeping": 0.0,    # immediate
                "using_phone": 2.0,
                "distracted": 3.0,
                "drowsy": 5.0,
            }
        if self.cooldown_seconds is None:
            self.cooldown_seconds = {
                "sleeping": 60.0,
                "using_phone": 45.0,
                "distracted": 30.0,
                "drowsy": 120.0,
            }


@dataclass
class SessionContext:
    """Resolved session context for alert decisions."""
    device_id: uuid.UUID
    driver_id: Optional[uuid.UUID]    # None if driver not identified
    vehicle_id: Optional[uuid.UUID]
    trip_id: Optional[uuid.UUID]      # None if no active trip


class AlertDecisionEngine:
    """
    Decides whether a DriverStateSnapshot warrants an alert.

    Rules (in order):
    1. No alert if state is NORMAL or UNKNOWN.
    2. No alert if within cooldown for this event type.
    3. No alert if event has not been stable for min_stable_seconds.
    4. No alert if driver_id is None and require_identified_driver=True.
    5. Severity is determined by state + event type.
    6. Evidence is saved for WARNING and CRITICAL.
    7. Device command (buzzer) is sent for CRITICAL.
    """

    def __init__(self, config: AlertConfig, session: SessionContext) -> None:
        self._cfg = config
        self._session = session
        self._last_alert_at: Dict[str, float] = {}
        self._event_stable_since: Dict[str, float] = {}

    def evaluate(
        self,
        snapshot: DriverStateSnapshot,
        now: float,
    ) -> AlertDecision:

        state = snapshot.state

        # Rule 1: safe states
        if state in (DriverSafetyState.NORMAL, DriverSafetyState.UNKNOWN):
            self._event_stable_since.clear()
            return AlertDecision(
                should_alert=False,
                severity=None,
                should_save_evidence=False,
                should_send_device_command=False,
                reason="state is safe",
            )

        event = snapshot.dominant_event

        # Rule 2: cooldown
        last_sent = self._last_alert_at.get(event, 0.0)
        cooldown = self._cfg.cooldown_seconds.get(event, 30.0)
        if now - last_sent < cooldown:
            return AlertDecision(
                should_alert=False, severity=None,
                should_save_evidence=False, should_send_device_command=False,
                reason=f"cooldown active for {event} ({now - last_sent:.1f}s < {cooldown}s)",
            )

        # Rule 3: minimum stable duration
        if event not in self._event_stable_since:
            self._event_stable_since[event] = now

        stable_duration = now - self._event_stable_since[event]
        min_stable = self._cfg.min_stable_seconds.get(event, 0.0)
        if stable_duration < min_stable:
            return AlertDecision(
                should_alert=False, severity=None,
                should_save_evidence=False, should_send_device_command=False,
                reason=f"{event} not yet stable ({stable_duration:.1f}s < {min_stable}s)",
            )

        # Rule 4: require identified driver
        if self._cfg.require_identified_driver and self._session.driver_id is None:
            return AlertDecision(
                should_alert=False, severity=None,
                should_save_evidence=False, should_send_device_command=False,
                reason="driver not identified — alert suppressed",
            )

        # Rule 5: determine severity
        severity = self._map_severity(state, event)

        # Rule 6 & 7: evidence and device command
        save_evidence = severity in (AlertSeverity.WARNING, AlertSeverity.CRITICAL)
        send_command  = severity == AlertSeverity.CRITICAL

        self._last_alert_at[event] = now

        return AlertDecision(
            should_alert=True,
            severity=severity,
            should_save_evidence=save_evidence,
            should_send_device_command=send_command,
            reason=f"{event} in state {state} for {stable_duration:.1f}s",
        )

    def _map_severity(
        self, state: DriverSafetyState, event: str
    ) -> AlertSeverity:
        """Map state + event to alert severity."""
        if state == DriverSafetyState.CRITICAL:
            return AlertSeverity.CRITICAL
        if state == DriverSafetyState.DANGEROUS:
            # Sleeping is always CRITICAL regardless of state label
            if event == "sleeping":
                return AlertSeverity.CRITICAL
            return AlertSeverity.WARNING
        # DROWSY state
        return AlertSeverity.INFO

    def reset_event_stability(self, event: str) -> None:
        """Call when an event transitions out of active."""
        self._event_stable_since.pop(event, None)

    def reset(self) -> None:
        """Reset all alert state (call on session disconnect)."""
        self._last_alert_at.clear()
        self._event_stable_since.clear()
