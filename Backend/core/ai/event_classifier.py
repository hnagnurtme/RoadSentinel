"""
core/ai/event_classifier.py
---------------------------
Stateful per-frame driver-event classifier with hysteresis.

Event taxonomy (what each YOLO label means)
--------------------------------------------
sleeping
  • ``sleeping``        — model explicitly detected sleeping posture
  • ``eyes closed``     — eyes are shut (direct physiological sign)
  These are DISTINCT from yawning — a yawn is fatigue, not sleep.

drowsy
  • ``yawning``         — single yawn ≠ sleeping; it is an early fatigue warning
  • ``drowsy``          — model-level drowsy classification
  • ``microsleep``      — very brief eye closure (short enough not to be "sleeping")
  After ``DROWSY_ESCALATION_SECONDS`` of continuous drowsy the caller should
  upgrade the urgency to sleeping level.

using_phone
  • ``cell phone`` / ``mobile`` / ``texting`` — phone in hand / visible
  • ``driver talking on phone``               — phone at ear
  These all mean the driver is physically interacting with a device.

distracted
  • ``distracted``              — model-level catch-all
  • ``driver looking away``     — head/gaze not facing forward
  • ``driver reaching behind``  — arm motion away from steering position
  IMPORTANT: looking away ≠ phone use. A driver can look away without a phone.

presence
  Labels used only to confirm the driver is in frame.
  If no presence label is seen for ``UNKNOWN_ENTER_FRAMES`` frames the state
  is ``"unknown"`` (camera may be covered or driver absent).
"""

from __future__ import annotations

from collections import deque
from typing import Final

from shared.config import settings

# ── Public constants ──────────────────────────────────────────────────────────

#: Events that are considered safety-critical and trigger alerts / evidence.
ALERT_EVENTS: Final[frozenset[str]] = frozenset(
    {"sleeping", "using_phone", "distracted", "drowsy"}
)


# ── Event Classifier ──────────────────────────────────────────────────────────


class DriverEventClassifier:
    """Stateful driver-behaviour classifier with per-event hysteresis counters.

    Algorithm per frame
    -------------------
    1. Build ``label → max_confidence`` from raw detections.
    2. For each event type check whether any of its *label set* meets the
       confidence threshold → ``has_evidence`` bool.
    3. Update the event's *score* counter (increment on evidence, decay on miss).
    4. Activate/deactivate the event based on enter/exit thresholds.
    5. Resolve the single *reported* event via a fixed priority, with an
       immediate fast-path for high-confidence **sleeping**.
    6. Track continuous drowsy duration so callers can escalate urgency.
    """

    # ── Label → event mapping ─────────────────────────────────────────────────
    # IMPORTANT: Only 6 labels exist in this model (real training distribution):
    #   Distracted, Drinking, Eyes Closed, Mobile, Seat Belt, Yawning
    #
    # sleeping  → "Eyes Closed"   — mắt nhắm = ngủ
    # drowsy    → "Yawning"        — ngáp = buồn ngủ (KHÁC với ngủ!)
    # using_phone → "Mobile"       — điện thoại
    # distracted  → "Distracted" + "Drinking" + "Seat Belt"
    #                               — mất tập trung (uống nước, không đai)

    _LABEL_SETS: Final[dict[str, frozenset[str]]] = {
        # Sleeping: eyes shut = direct physiological sign of sleeping.
        "sleeping": frozenset({"eyes closed"}),
        # Drowsy: fatigue warning.
        "drowsy": frozenset({"yawning"}),
        # Phone use: mobile label only.
        "using_phone": frozenset({"mobile"}),
        # Distracted: looking away, drinking while driving, no seat belt, reaching behind.
        # NOTE: model has NO 'distracted' class — real classes are mapped below.
        "distracted": frozenset({"looking away", "reaching behind", "drinking", "seat belt"}),
    }

    def __init__(self) -> None:
        self._no_presence_counter: int = 0

        self._event_scores: dict[str, float] = dict.fromkeys(self._LABEL_SETS, 0.0)
        self._event_miss_streaks: dict[str, int] = dict.fromkeys(self._LABEL_SETS, 0)
        self._event_active: dict[str, bool] = dict.fromkeys(self._LABEL_SETS, False)
        self._event_state: dict[str, str] = dict.fromkeys(self._LABEL_SETS, "idle")
        self._candidate_streaks: dict[str, int] = dict.fromkeys(self._LABEL_SETS, 0)
        self._release_streaks: dict[str, int] = dict.fromkeys(self._LABEL_SETS, 0)

        self._l1_window_frames = settings.DRIVER_EVENT_L1_WINDOW_FRAMES
        self._l2_window_frames = settings.DRIVER_EVENT_L2_WINDOW_FRAMES
        self._l3_window_frames = settings.DRIVER_EVENT_L3_WINDOW_FRAMES
        self._window_decay = settings.DRIVER_EVENT_WINDOW_DECAY
        self._score_weight_l1 = settings.DRIVER_EVENT_SCORE_WEIGHT_L1
        self._score_weight_l2 = settings.DRIVER_EVENT_SCORE_WEIGHT_L2
        self._score_weight_l3 = settings.DRIVER_EVENT_SCORE_WEIGHT_L3
        self._candidate_enter_frames = settings.DRIVER_EVENT_CANDIDATE_ENTER_FRAMES

        self._event_histories: dict[str, deque[float]] = {
            event: deque(maxlen=self._l3_window_frames) for event in self._LABEL_SETS
        }

        self._decay_miss_frames: dict[str, int] = {
            # Sleeping decays slowly — false negatives are dangerous.
            "sleeping": 3,
            "using_phone": settings.DRIVER_EVENT_PHONE_DECAY_MISS_FRAMES,
            # Distracted decays quickly — a quick glance back resets it.
            "distracted": 2,
            "drowsy": settings.DRIVER_EVENT_DROWSY_DECAY_MISS_FRAMES,
        }
        self._enter_thresholds: dict[str, int] = {
            "sleeping": settings.DRIVER_EVENT_SLEEP_ENTER_FRAMES,
            "using_phone": settings.DRIVER_EVENT_PHONE_ENTER_FRAMES,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_ENTER_FRAMES,
            "drowsy": settings.DRIVER_EVENT_DROWSY_ENTER_FRAMES,
        }
        self._exit_thresholds: dict[str, int] = {
            "sleeping": settings.DRIVER_EVENT_SLEEP_EXIT_FRAMES,
            "using_phone": settings.DRIVER_EVENT_PHONE_EXIT_FRAMES,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_EXIT_FRAMES,
            "drowsy": settings.DRIVER_EVENT_DROWSY_EXIT_FRAMES,
        }
        self._confidence_thresholds: dict[str, float] = {
            "sleeping": settings.DRIVER_EVENT_MIN_SLEEP_CONFIDENCE,
            "using_phone": settings.DRIVER_EVENT_MIN_PHONE_CONFIDENCE,
            "distracted": settings.DRIVER_EVENT_MIN_DISTRACTED_CONFIDENCE,
            "drowsy": settings.DRIVER_EVENT_MIN_DROWSY_CONFIDENCE,
        }
        self._fastpath_thresholds: dict[str, float] = {
            "using_phone": settings.DRIVER_EVENT_PHONE_FASTPATH_CONFIDENCE,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_FASTPATH_CONFIDENCE,
            "drowsy": settings.DRIVER_EVENT_DROWSY_FASTPATH_CONFIDENCE,
        }
        self._activate_thresholds: dict[str, float] = {
            "sleeping": settings.DRIVER_EVENT_SLEEPING_ACTIVATE_SCORE,
            "using_phone": settings.DRIVER_EVENT_PHONE_ACTIVATE_SCORE,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_ACTIVATE_SCORE,
            "drowsy": settings.DRIVER_EVENT_DROWSY_ACTIVATE_SCORE,
        }
        self._deactivate_thresholds: dict[str, float] = {
            "sleeping": settings.DRIVER_EVENT_SLEEPING_DEACTIVATE_SCORE,
            "using_phone": settings.DRIVER_EVENT_PHONE_DEACTIVATE_SCORE,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_DEACTIVATE_SCORE,
            "drowsy": settings.DRIVER_EVENT_DROWSY_DEACTIVATE_SCORE,
        }
        self._hold_frames: dict[str, int] = {
            "sleeping": settings.DRIVER_EVENT_SLEEP_HOLD_FRAMES,
            "using_phone": settings.DRIVER_EVENT_PHONE_HOLD_FRAMES,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_HOLD_FRAMES,
            "drowsy": settings.DRIVER_EVENT_DROWSY_HOLD_FRAMES,
        }
        self._presence_labels: frozenset[str] = frozenset(
            label.strip().lower() for label in settings.DRIVER_EVENT_PRESENCE_LABELS
        )
        # Event priority for frame-by-frame resolution (highest danger first).
        # sleeping is listed first: if both sleeping AND phone detected,
        # sleeping wins because it is more immediately dangerous.
        self._event_priority: tuple[str, ...] = tuple(
            event.strip().lower() for event in settings.DRIVER_EVENT_PRIORITY
        )
        self._unknown_enter_frames: int = settings.DRIVER_EVENT_UNKNOWN_ENTER_FRAMES
        self._drowsy_escalation_seconds: float = (
            settings.DRIVER_EVENT_DROWSY_ESCALATION_SECONDS
        )

        # Event-active start times (wall-clock monotonic)
        self._event_active_since: dict[str, float | None] = dict.fromkeys(
            self._LABEL_SETS, None
        )
        self._drowsy_active_since: float | None = None  # Legacy, kept for compatibility

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _max_conf_by_label(detections: list[dict]) -> dict[str, float]:
        """Return ``{label: max_confidence}`` from a raw detection list."""
        out: dict[str, float] = {}
        for det in detections:
            label = str(det.get("label", "")).lower()
            conf = float(det.get("conf", det.get("confidence", 0.0)))
            if conf > out.get(label, 0.0):
                out[label] = conf
        return out

    def _update_event_state(self, event: str, has_evidence: bool) -> None:
        """Advance the hysteresis counter for a single event."""
        score = self._event_scores[event]
        enter = self._enter_thresholds[event]
        exit_ = self._exit_thresholds[event]

        if has_evidence:
            score = min(enter, score + 1)
            self._event_miss_streaks[event] = 0
        else:
            miss_streak = self._event_miss_streaks[event] + 1
            self._event_miss_streaks[event] = miss_streak
            if miss_streak >= self._decay_miss_frames[event]:
                score = max(0, score - 1)
                self._event_miss_streaks[event] = 0

        active = self._event_active[event]
        if active and score < exit_:
            active = False
        elif (not active) and score >= enter:
            active = True

        self._event_scores[event] = score
        self._event_active[event] = active

    def _window_score(self, event: str, window_frames: int) -> float:
        """Return a decayed confidence score over the latest N frames."""
        history = self._event_histories[event]
        if not history:
            return 0.0

        floor = max(self._confidence_thresholds[event], 1e-6)
        frames = list(history)[-window_frames:]
        numerator = 0.0
        denominator = 0.0

        for age, conf in enumerate(reversed(frames)):
            weight = self._window_decay**age
            normalized = min(1.0, max(0.0, conf) / floor)
            numerator += normalized * weight
            denominator += weight

        if denominator <= 0.0:
            return 0.0
        return numerator / denominator

    def _composite_score(self, event: str) -> float:
        """Combine L1/L2/L3 windows into a single smooth score in [0, 1]."""
        l1 = self._window_score(event, self._l1_window_frames)
        l2 = self._window_score(event, self._l2_window_frames)
        l3 = self._window_score(event, self._l3_window_frames)

        combined = (
            self._score_weight_l1 * l1
            + self._score_weight_l2 * l2
            + self._score_weight_l3 * l3
        )
        return min(1.0, max(0.0, combined))

    def _advance_event_state(self, event: str, evidence_conf: float) -> float:
        """Advance one event through idle/candidate/confirmed/held/releasing."""
        self._event_histories[event].append(max(0.0, evidence_conf))
        score = self._composite_score(event)

        activate = self._activate_thresholds[event]
        deactivate = self._deactivate_thresholds[event]
        hold_frames = self._hold_frames[event]
        state = self._event_state[event]

        if score >= activate:
            self._candidate_streaks[event] += 1
            self._release_streaks[event] = 0
        elif score <= deactivate:
            self._candidate_streaks[event] = 0
            self._release_streaks[event] += 1
        else:
            # In hysteresis gap: keep ongoing candidate/release trends stable.
            self._candidate_streaks[event] = max(0, self._candidate_streaks[event] - 1)
            self._release_streaks[event] = max(0, self._release_streaks[event] - 1)

        if state in {"idle", "releasing"}:
            if self._candidate_streaks[event] >= self._candidate_enter_frames:
                state = "confirmed"
            elif score >= activate:
                state = "candidate"
            else:
                state = "idle"
        elif state == "candidate":
            if self._candidate_streaks[event] >= self._candidate_enter_frames:
                state = "confirmed"
            elif score <= deactivate:
                state = "idle"
        elif state in {"confirmed", "held"}:
            if score <= deactivate:
                state = (
                    "held"
                    if self._release_streaks[event] < hold_frames
                    else "releasing"
                )
            else:
                state = "confirmed"

        self._event_state[event] = state
        self._event_active[event] = state in {"confirmed", "held"}
        self._event_scores[event] = score
        return score

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(
        self, detections: list[dict], now: float | None = None
    ) -> tuple[str, float]:
        """Classify the current frame's detections into a driver event.

        Args:
            detections: Raw YOLO detection dicts ``{label, conf, bbox}``.
            now: Current ``time.monotonic()`` value.  Passing this enables
                 drowsy-escalation duration tracking.

        Returns:
            ``(event_name, confidence)`` where ``event_name`` is one of:
            ``"sleeping"``, ``"using_phone"``, ``"distracted"``,
            ``"drowsy"``, ``"normal"``, ``"unknown"``.
        """
        label_conf = self._max_conf_by_label(detections)

        # ── Presence tracking ─────────────────────────────────────────────
        # The model has NO dedicated face/person/presence labels.
        # So we treat ANY detection as a presence signal.
        # If the buffer is completely empty → driver may be absent or camera covered.
        has_presence = bool(label_conf)
        self._no_presence_counter = 0 if has_presence else self._no_presence_counter + 1

        # ── Per-event hysteresis update ───────────────────────────────────
        event_confidence: dict[str, float] = {}
        raw_event_confidence: dict[str, float] = {}
        for event, label_set in self._LABEL_SETS.items():
            evidence_conf = max(
                (conf for label, conf in label_conf.items() if label in label_set),
                default=0.0,
            )
            raw_event_confidence[event] = evidence_conf
            event_confidence[event] = self._advance_event_state(event, evidence_conf)

        # ── Sleeping fast-path ────────────────────────────────────────────
        # "Eyes Closed" with sufficient confidence immediately activates sleeping.
        # This is intentional: a single frame of closed eyes is strong evidence.
        # "Yawning" does NOT trigger this path — it goes to drowsy only.
        explicit_sleeping_conf = label_conf.get("eyes closed", 0.0)
        if explicit_sleeping_conf >= self._confidence_thresholds["sleeping"]:
            self._event_histories["sleeping"].append(explicit_sleeping_conf)
            self._event_scores["sleeping"] = 1.0
            self._event_miss_streaks["sleeping"] = 0
            self._event_active["sleeping"] = True
            self._event_state["sleeping"] = "confirmed"
            self._candidate_streaks["sleeping"] = self._candidate_enter_frames
            self._release_streaks["sleeping"] = 0
            self._update_drowsy_timing(is_drowsy=False, now=now)
            all_active = ["sleeping"]
            if self._event_active_since["sleeping"] is None and now is not None:
                self._event_active_since["sleeping"] = now
            return "sleeping", explicit_sleeping_conf, all_active

        # ── Fast-path for non-sleeping critical labels ───────────────────
        # Similar to the eyes-closed fast path, this gives one-frame promotion
        # when confidence is very high so phone/distracted/drowsy feel less laggy.
        for event in ("using_phone", "distracted", "drowsy"):
            threshold = self._fastpath_thresholds[event]
            if raw_event_confidence.get(event, 0.0) >= threshold:
                self._event_histories[event].append(raw_event_confidence[event])
                self._event_scores[event] = 1.0
                self._event_miss_streaks[event] = 0
                self._event_active[event] = True
                self._event_state[event] = "confirmed"
                self._candidate_streaks[event] = self._candidate_enter_frames
                self._release_streaks[event] = 0

        # ── Priority resolution ───────────────────────────────────────────
        # Walk the configured priority list. sleeping is expected to be first
        # since it is the most immediately dangerous state.
        resolved_event: str | None = None
        resolved_conf: float = 0.0

        for event in self._event_priority:
            if self._event_active.get(event, False):
                resolved_event = event
                resolved_conf = event_confidence.get(event, 0.0)
                break

        if not resolved_event and self._event_active.get("drowsy", False):
            resolved_event = "drowsy"
            resolved_conf = event_confidence.get("drowsy", 0.0)

        # ── Update start times and handle resolution ──────────────────────
        all_active: list[str] = []
        for event in self._LABEL_SETS:
            is_active = (event == resolved_event)
            if self._event_active.get(event, False):
                all_active.append(event)
                if self._event_active_since[event] is None and now is not None:
                    self._event_active_since[event] = now
            else:
                self._event_active_since[event] = None

        # Sort all_active by priority for consistent display
        all_active.sort(key=lambda e: self._event_priority.index(e) if e in self._event_priority else 99)

        # Sync legacy drowsy timer
        self._drowsy_active_since = self._event_active_since.get("drowsy")

        if resolved_event:
            return resolved_event, resolved_conf, all_active

        # ── Unknown / normal ──────────────────────────────────────────────
        self._update_drowsy_timing(is_drowsy=False, now=now)

        if self._no_presence_counter >= self._unknown_enter_frames:
            return "unknown", 0.0, []
        return "normal", 0.0, []

    def get_event_duration(self, event: str, now: float) -> float:
        """Return how long the given event has been *continuously* active (seconds)."""
        started_at = self._event_active_since.get(event)
        if started_at is None:
            return 0.0
        return max(0.0, now - started_at)

    def get_drowsy_duration(self, now: float) -> float:
        """Return how long the driver has been *continuously* drowsy (seconds)."""
        return self.get_event_duration("drowsy", now)

    @property
    def drowsy_escalated(self) -> bool:
        """``True`` when drowsy has lasted >= DROWSY_ESCALATION_SECONDS.

        Callers should treat this as sleeping-level urgency even though the
        YOLO label is still "drowsy" (no eyes-closed label was detected).

        DEPRECATED: This property is not implemented. Use get_drowsy_duration(now)
        instead and compare with DROWSY_ESCALATION_SECONDS.
        """
        raise NotImplementedError(
            "drowsy_escalated property is not implemented. "
            "Use get_drowsy_duration(now) and compare with DROWSY_ESCALATION_SECONDS."
        )

    def reset(self) -> None:
        """Reset all internal state (call on ESP32 disconnect)."""
        self._no_presence_counter = 0
        self._drowsy_active_since = None
        for event in self._event_scores:
            self._event_scores[event] = 0.0
            self._event_miss_streaks[event] = 0
            self._event_active[event] = False
            self._event_state[event] = "idle"
            self._candidate_streaks[event] = 0
            self._release_streaks[event] = 0
            self._event_histories[event].clear()
            self._event_active_since[event] = None

    # ------------------------------------------------------------------
    # Private: drowsy timing
    # ------------------------------------------------------------------

    def _update_drowsy_timing(self, *, is_drowsy: bool, now: float | None) -> None:
        if now is None:
            return
        if is_drowsy:
            if self._drowsy_active_since is None:
                self._drowsy_active_since = now
        else:
            self._drowsy_active_since = None


# ── Window / Latch Trigger ────────────────────────────────────────────────────


class WindowTrigger:
    """Fire exactly once when a boolean signal's occupancy over a rolling
    window meets or exceeds ``occupancy_threshold``.

    Re-arms itself automatically when the signal drops to zero for the full
    window (i.e. the event is truly over).

    Args:
        fps: Frames per second used to convert ``window_seconds`` to frames.
        window_seconds: Length of the observation window in seconds.
        occupancy_threshold: Fraction ``[0.0, 1.0]`` of positive frames
            required to fire.  ``1.0`` means *every* frame must be positive.
    """

    def __init__(
        self, fps: int, window_seconds: int, occupancy_threshold: float
    ) -> None:
        self._window_frames: int = max(1, int(fps) * int(window_seconds))
        self._occupancy_threshold: float = occupancy_threshold
        self._window: deque[bool] = deque(maxlen=self._window_frames)
        self._latched: bool = False

    def update(self, signal: bool) -> bool:
        """Push a new sample and return ``True`` if the trigger fires this frame."""
        self._window.append(signal)

        if len(self._window) < self._window_frames:
            return False

        positive_count = sum(self._window)

        # Re-arm when the window is entirely negative.
        if positive_count == 0:
            self._latched = False

        occupancy = positive_count / len(self._window)
        if occupancy >= self._occupancy_threshold and not self._latched:
            self._latched = True
            return True

        return False
