from app.evidence.trigger import SleepWindowTrigger


def test_no_trigger_when_sleeping_only_8s_in_10s_window() -> None:
    trigger = SleepWindowTrigger(fps=1, window_seconds=10, occupancy_threshold=0.95)

    fired = False
    for _ in range(8):
        fired = fired or trigger.update(True)
    for _ in range(2):
        fired = fired or trigger.update(False)

    assert fired is False


def test_trigger_when_window_is_fully_sleeping() -> None:
    trigger = SleepWindowTrigger(fps=1, window_seconds=10, occupancy_threshold=0.95)

    fired = False
    for _ in range(10):
        fired = fired or trigger.update(True)

    assert fired is True


def test_trigger_latches_until_sleeping_breaks() -> None:
    trigger = SleepWindowTrigger(fps=1, window_seconds=10, occupancy_threshold=0.9)

    # First trigger
    for _ in range(10):
        trigger.update(True)
    assert trigger.update(True) is False

    # One non-sleep frame should not re-arm immediately.
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False
    assert trigger.update(False) is False

    # Re-arm and trigger again on a new episode
    fired = False
    for _ in range(10):
        fired = fired or trigger.update(True)
    assert fired is True
