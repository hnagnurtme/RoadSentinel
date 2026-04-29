"""
core/ai/temporal_reasoning.py
-----------------------------------
Temporal reasoning engine using EWMA scoring to replace brittle WindowTrigger.

Key improvements:
- Handles frame drops naturally via exponential decay
- Asymmetric alpha for fast rise/slow fall behavior
- Continuous scoring instead of binary latch
- Fully testable pure functions
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EWMAScorer:
    """
    Exponentially Weighted Moving Average scorer for a single event.

    score(t) = alpha * confidence(t) + (1 - alpha) * score(t-1)

    When a frame is missing (dropout), confidence(t) = 0 and the score
    decays naturally. The DropoutCompensator can inject held confidence
    before this scorer sees it, preventing decay during short gaps.

    alpha_rise: fast rise — used when confidence > current score (event appearing)
    alpha_fall: slow fall — used when confidence < current score (event fading)

    Asymmetric alpha is the key insight:
      - Critical events (sleeping) should rise fast and fall slow.
      - Noisy events (distracted) should rise slow and fall fast.
    """

    alpha_rise: float = 0.35
    alpha_fall: float = 0.15
    _score: float = field(default=0.0, init=False)

    def update(self, confidence: float) -> float:
        """Update EWMA score with new confidence value."""
        alpha = self.alpha_rise if confidence > self._score else self.alpha_fall
        self._score = alpha * confidence + (1.0 - alpha) * self._score
        self._score = max(0.0, min(1.0, self._score))
        return self._score

    @property
    def score(self) -> float:
        """Current EWMA score."""
        return self._score

    def reset(self) -> None:
        """Reset score to zero."""
        self._score = 0.0


# Recommended alpha pairs per event type:
#
# sleeping:    rise=0.50, fall=0.10  → fast to activate, very slow to release
#              Rationale: missing a sleeping frame is dangerous; hold the state.
#
# using_phone: rise=0.40, fall=0.15  → fast rise, moderate fall
#              Rationale: phone use is persistent; brief occlusion shouldn't reset.
#
# distracted:  rise=0.25, fall=0.30  → slow rise, fast fall
#              Rationale: brief glances away are normal; only sustained counts.
#
# drowsy:      rise=0.30, fall=0.12  → moderate rise, slow fall
#              Rationale: yawning is brief but fatigue accumulates.


class DropoutCompensator:
    """
    When frames are missing (network drop, SKIP_FRAMES), hold the last
    known confidence for up to MAX_HOLD_SECONDS before decaying.

    This prevents a 200ms network hiccup from resetting a 9-second
    sleeping detection.
    """

    MAX_HOLD_SECONDS: float = 1.5  # hold without decay
    DECAY_HALF_LIFE: float = 2.0  # exponential decay after hold period

    def __init__(self) -> None:
        self._last_seen: Dict[str, float] = {}  # event → wall time
        self._held_conf: Dict[str, float] = {}  # event → last confidence

    def update(
        self,
        event_conf: Dict[str, float],
        now: float,
    ) -> Dict[str, float]:
        """
        Merge live detections with held values.
        Returns the effective confidence per event for this tick.
        """
        # Update held values for events that ARE detected this tick.
        for event, conf in event_conf.items():
            self._last_seen[event] = now
            self._held_conf[event] = conf

        result: Dict[str, float] = dict(event_conf)

        # Inject held confidence for events NOT detected this tick.
        for event, last_time in self._last_seen.items():
            if event in result:
                continue  # already have a live detection
            age = now - last_time
            if age <= self.MAX_HOLD_SECONDS:
                result[event] = self._held_conf[event]
            elif age <= self.MAX_HOLD_SECONDS + self.DECAY_HALF_LIFE * 4:
                # Exponential decay after hold period
                decay_age = age - self.MAX_HOLD_SECONDS
                factor = 0.5 ** (decay_age / self.DECAY_HALF_LIFE)
                result[event] = self._held_conf[event] * factor

        return result

    def reset(self) -> None:
        """Reset all state."""
        self._last_seen.clear()
        self._held_conf.clear()


class TemporalReasoningEngine:
    """
    Converts per-frame raw confidences into smooth temporal scores.

    Pipeline per tick:
      1. Apply confidence gates (already done in detection_normaliser)
      2. Apply dropout compensation (hold/decay during frame gaps)
      3. Update EWMA scorers
      4. Return {event: smooth_score}
    """

    def __init__(self, config: "TemporalConfig") -> None:
        self._cfg = config
        self._scorers: Dict[str, EWMAScorer] = {
            event: EWMAScorer(
                alpha_rise=config.alpha_rise[event],
                alpha_fall=config.alpha_fall[event],
            )
            for event in config.tracked_events
        }
        self._dropout = DropoutCompensator()
        self._last_tick_time: Optional[float] = None

    def tick(
        self,
        event_conf: Dict[str, float],  # from best_confidence_per_event()
        now: float,
    ) -> Dict[str, float]:
        """
        Process one frame tick. Returns {event: smooth_score_0_to_1}.
        event_conf may be empty if the frame was skipped or AI unavailable.
        """
        # Compensate for frame drops
        compensated = self._dropout.update(event_conf, now)

        # Update EWMA scorers — events not in compensated get 0.0
        scores: Dict[str, float] = {}
        for event, scorer in self._scorers.items():
            conf = compensated.get(event, 0.0)
            scores[event] = scorer.update(conf)

        self._last_tick_time = now
        return scores

    def reset(self) -> None:
        """Reset all temporal state."""
        for scorer in self._scorers.values():
            scorer.reset()
        self._dropout.reset()
        self._last_tick_time = None


@dataclass
class TemporalConfig:
    """Configuration for temporal reasoning engine."""

    tracked_events: List[str]
    confidence_gates: Dict[str, float]
    alpha_rise: Dict[str, float]
    alpha_fall: Dict[str, float]
    dropout_max_hold_seconds: float = 1.5
    dropout_decay_half_life: float = 2.0
