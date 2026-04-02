import 'dart:async';
import 'dart:typed_data';

import '../models/app_config.dart';
import '../models/detection.dart';
import '../models/pipeline_status.dart';
import 'cloudinary_service.dart';
import 'event_logic_service.dart';
import 'evidence_service.dart';
import 'inference_service.dart';
import 'mjpeg_stream_service.dart';
import 'sender_service.dart';
import 'sleep_window_trigger.dart';

class PipelineService {
  PipelineService(this._config)
      : _eventLogic = EventLogicService(_config),
        _inference = InferenceService(_config),
        _cloudinary = CloudinaryService(_config),
        _sender = SenderService(_config),
        _trigger = SleepWindowTrigger(
          fps: _config.targetFps,
          windowSeconds: _config.sleepEvidenceSeconds,
          occupancyThreshold: _config.sleepTriggerRatio,
        ) {
    _evidence = EvidenceService(config: _config, cloudinary: _cloudinary);
  }

  final AppConfig _config;
  final EventLogicService _eventLogic;
  final InferenceService _inference;
  final MjpegStreamService _stream = MjpegStreamService();
  final CloudinaryService _cloudinary;
  late final EvidenceService _evidence;
  final SenderService _sender;
  final SleepWindowTrigger _trigger;

  final StreamController<PipelineStatus> _statusController =
      StreamController<PipelineStatus>.broadcast();

  Stream<PipelineStatus> get statusStream => _statusController.stream;

  PipelineStatus _status = PipelineStatus.idle();
  DateTime _lastProcessed = DateTime.fromMillisecondsSinceEpoch(0);
  bool _processing = false;
  bool _running = false;

  Future<void> start() async {
    if (_running) {
      return;
    }

    _running = true;
    _emit(_status.copyWith(running: true, lastError: null));

    try {
      await _inference.load();
      await _sender.start();
      await _stream.start(
        url: _config.webcamServerUrl,
        onFrame: _onFrame,
        onError: (error) {
          _emit(_status.copyWith(lastError: error.toString()));
        },
      );
    } catch (error) {
      _emit(_status.copyWith(running: false, lastError: error.toString()));
      _running = false;
    }
  }

  Future<void> stop() async {
    _running = false;
    await _stream.stop();
    _stream.dispose();
    await _sender.stop();
    _inference.dispose();
    _eventLogic.reset();
    _emit(_status.copyWith(running: false));
  }

  Future<void> dispose() async {
    await stop();
    await _statusController.close();
  }

  void _onFrame(Uint8List frameBytes) {
    if (!_running || _processing) {
      return;
    }

    final frameIntervalMs = (1000 / _config.targetFps).round();
    final now = DateTime.now();
    if (now.difference(_lastProcessed).inMilliseconds < frameIntervalMs) {
      return;
    }

    _lastProcessed = now;
    _processing = true;

    _processFrame(frameBytes).whenComplete(() {
      _processing = false;
    });
  }

  Future<void> _processFrame(Uint8List frameBytes) async {
    try {
      _evidence.pushFrame(frameBytes);

      final detections = await _inference.infer(frameBytes);
      final filtered = _filterDetections(detections);

      final maxConf = filtered.isEmpty
          ? 0.0
          : filtered.map((e) => e.confidence).reduce((a, b) => a > b ? a : b);

      final event = _eventLogic.classify(filtered);

      final sleepEvidencePresent = _resolveSleepEvidence(filtered);
      String? evidenceUrl;

      // Upload for test if enabled and any detection found
      if (_config.cloudinaryEnabled && filtered.isNotEmpty) {
        // Upload every 10th detection frame (to avoid spamming)
        if (DateTime.now().second % 10 == 0) {
           _cloudinary.upload(frameBytes);
        }
      }

      if (_trigger.update(sleepEvidencePresent)) {
        evidenceUrl = await _evidence.saveSleepingEvidence(event.confidence);
      }

      await _sender.send(
        {
          'device_id': _config.deviceId,
          'event': event.event,
          'confidence': double.parse(event.confidence.toStringAsFixed(4)),
          'max_detection_conf': maxConf,
        },
      );

      _emit(
        _status.copyWith(
          running: true,
          event: event.event,
          confidence: event.confidence,
          maxDetectionConfidence: maxConf,
          detectionCount: filtered.length,
          lastUpdated: DateTime.now(),
          lastEvidenceUrl: evidenceUrl ?? _status.lastEvidenceUrl,
          lastError: null,
        ),
      );
    } catch (error) {
      _emit(_status.copyWith(lastError: error.toString()));
    }
  }

  List<Detection> _filterDetections(List<Detection> detections) {
    const relevant = {
      'cell phone',
      'mobile',
      'texting',
      'driver talking on phone',
      'person',
      'driver',
      'face',
      'eye',
      'eyes open',
      'sleeping',
      'eyes closed',
      'yawning',
      'drowsy',
      'distracted',
      'driver looking away',
      'driver reaching behind',
    };

    final out = detections
        .where((d) => relevant.contains(d.label.toLowerCase()))
        .toList(growable: false)
      ..sort((a, b) => b.confidence.compareTo(a.confidence));

    return out;
  }

  bool _resolveSleepEvidence(List<Detection> detections) {
    final sleepLabels = _config.sleepLabels.map((e) => e.toLowerCase()).toSet();
    final presenceLabels = _config.presenceLabels.map((e) => e.toLowerCase()).toSet();
    const eyesOpenLabels = {'eyes open', 'eye'};

    var sleepEvidencePresent = detections.any(
      (d) =>
          sleepLabels.contains(d.label.toLowerCase()) &&
          d.confidence >= _config.minSleepConfidence,
    );

    if (_config.useSleepProxy && !sleepEvidencePresent) {
      final hasPresence = detections.any(
        (d) =>
            presenceLabels.contains(d.label.toLowerCase()) &&
            d.confidence >= _config.minPresenceConfidence,
      );
      final hasEyesOpen = detections.any(
        (d) =>
            eyesOpenLabels.contains(d.label.toLowerCase()) &&
            d.confidence >= _config.minEyesOpenConfidence,
      );
      sleepEvidencePresent = hasPresence && !hasEyesOpen;
    }

    return sleepEvidencePresent;
  }

  void _emit(PipelineStatus next) {
    _status = next;
    if (!_statusController.isClosed) {
      _statusController.add(_status);
    }
  }
}
