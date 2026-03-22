import 'dart:collection';

class SleepWindowTrigger {
  SleepWindowTrigger({
    required int fps,
    required int windowSeconds,
    required double occupancyThreshold,
  })  : _windowFrames = (fps * windowSeconds).clamp(1, 100000),
        _occupancyThreshold = occupancyThreshold;

  final int _windowFrames;
  final double _occupancyThreshold;
  final ListQueue<bool> _window = ListQueue<bool>();
  bool _latched = false;

  bool update(bool isSleeping) {
    _window.addLast(isSleeping);
    if (_window.length > _windowFrames) {
      _window.removeFirst();
    }

    if (_window.length < _windowFrames) {
      return false;
    }

    final sleepingFrames = _window.where((v) => v).length;
    final occupancy = sleepingFrames / _window.length;

    if (sleepingFrames == 0) {
      _latched = false;
    }

    if (occupancy >= _occupancyThreshold && !_latched) {
      _latched = true;
      return true;
    }

    return false;
  }
}
