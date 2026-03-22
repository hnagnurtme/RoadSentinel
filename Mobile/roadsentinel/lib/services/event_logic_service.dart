import '../models/app_config.dart';
import '../models/detection.dart';
import '../models/event_result.dart';

class EventLogicService {
  EventLogicService(this._cfg)
      : _enterThresholds = {
          'sleeping': _cfg.sleepEnterFrames,
          'using_phone': _cfg.phoneEnterFrames,
          'distracted': _cfg.distractedEnterFrames,
        },
        _exitThresholds = {
          'sleeping': _cfg.sleepExitFrames,
          'using_phone': _cfg.phoneExitFrames,
          'distracted': _cfg.distractedExitFrames,
        },
        _labelSets = {
          'sleeping': _cfg.sleepLabels.map((e) => e.toLowerCase()).toSet(),
          'using_phone': _cfg.phoneLabels.map((e) => e.toLowerCase()).toSet(),
          'distracted': _cfg.distractedLabels.map((e) => e.toLowerCase()).toSet(),
        },
        _confidenceThresholds = {
          'sleeping': _cfg.minSleepConfidence,
          'using_phone': _cfg.minPhoneConfidence,
          'distracted': _cfg.minDistractedConfidence,
        },
        _presenceLabels = _cfg.presenceLabels.map((e) => e.toLowerCase()).toSet();

  final AppConfig _cfg;
  int _noPresenceCounter = 0;

  final Map<String, int> _eventScores = {
    'sleeping': 0,
    'using_phone': 0,
    'distracted': 0,
  };

  final Map<String, bool> _eventActive = {
    'sleeping': false,
    'using_phone': false,
    'distracted': false,
  };

  final Map<String, int> _enterThresholds;
  final Map<String, int> _exitThresholds;
  final Map<String, Set<String>> _labelSets;
  final Map<String, double> _confidenceThresholds;
  final Set<String> _presenceLabels;

  EventResult classify(List<Detection> detections) {
    final labelConf = _maxConfByLabel(detections);

    final hasPresence = labelConf.keys.any(_presenceLabels.contains);
    if (hasPresence) {
      _noPresenceCounter = 0;
    } else {
      _noPresenceCounter += 1;
    }

    final eventConfidence = <String, double>{};

    for (final event in _eventScores.keys) {
      final labels = _labelSets[event] ?? const <String>{};
      var evidenceConf = 0.0;
      for (final entry in labelConf.entries) {
        if (labels.contains(entry.key) && entry.value > evidenceConf) {
          evidenceConf = entry.value;
        }
      }
      eventConfidence[event] = evidenceConf;
      final minConf = _confidenceThresholds[event] ?? 0.0;
      _updateEventState(event, evidenceConf >= minConf);
    }

    for (final event in _cfg.eventPriority) {
      if (_eventActive[event] == true) {
        return EventResult(event: event, confidence: eventConfidence[event] ?? 0.0);
      }
    }

    if (_noPresenceCounter >= _cfg.unknownEnterFrames) {
      return EventResult(event: 'unknown', confidence: 0.0);
    }

    return EventResult(event: 'normal', confidence: 0.0);
  }

  void reset() {
    _noPresenceCounter = 0;
    for (final k in _eventScores.keys) {
      _eventScores[k] = 0;
      _eventActive[k] = false;
    }
  }

  Map<String, double> _maxConfByLabel(List<Detection> detections) {
    final out = <String, double>{};
    for (final det in detections) {
      final label = det.label.toLowerCase();
      final current = out[label] ?? 0.0;
      if (det.confidence > current) {
        out[label] = det.confidence;
      }
    }
    return out;
  }

  void _updateEventState(String event, bool hasEvidence) {
    var score = _eventScores[event] ?? 0;
    final enter = _enterThresholds[event] ?? 1;
    final exit = _exitThresholds[event] ?? 1;

    if (hasEvidence) {
      score = (score + 1).clamp(0, enter);
    } else {
      score = (score - 1).clamp(0, enter);
    }

    var active = _eventActive[event] ?? false;
    if (active && score < exit) {
      active = false;
    } else if (!active && score >= enter) {
      active = true;
    }

    _eventScores[event] = score;
    _eventActive[event] = active;
  }
}
