import 'dart:collection';
import 'dart:io';
import 'dart:typed_data';

import 'package:ffmpeg_kit_flutter_new_min_gpl/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_min_gpl/return_code.dart';
import 'package:path_provider/path_provider.dart';

import '../models/app_config.dart';
import 'cloudinary_service.dart';

class EvidenceService {
  EvidenceService({
    required AppConfig config,
    required CloudinaryService cloudinary,
  })  : _config = config,
        _cloudinary = cloudinary,
        _maxFrames = (config.targetFps * config.sleepEvidenceSeconds).clamp(1, 100000);

  final AppConfig _config;
  final CloudinaryService _cloudinary;
  final int _maxFrames;
  final ListQueue<Uint8List> _buffer = ListQueue<Uint8List>();
  bool _uploadInFlight = false;

  bool get _isIosSimulator {
    return Platform.isIOS &&
        Platform.environment.containsKey('SIMULATOR_DEVICE_NAME');
  }

  void pushFrame(Uint8List frameBytes) {
    _buffer.addLast(frameBytes);
    if (_buffer.length > _maxFrames) {
      _buffer.removeFirst();
    }
  }

  Future<String?> saveSleepingEvidence(double confidence) async {
    if (_isIosSimulator) {
      return _uploadSimulatorImageEvidence(confidence);
    }

    if (!_cloudinary.enabled || _uploadInFlight || _buffer.isEmpty) {
      return null;
    }

    _uploadInFlight = true;
    Directory? clipDir;
    File? outputMp4;

    try {
      final dir = await getTemporaryDirectory();
      final now = DateTime.now();
      final stamp =
          '${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}';
      final stem =
          'sleeping_${stamp}_${_config.sleepEvidenceSeconds}s_conf${confidence.toStringAsFixed(2)}';

      clipDir = Directory('${dir.path}/$stem');
      await clipDir.create(recursive: true);

      final frames = _buffer.toList(growable: false);
      for (var i = 0; i < frames.length; i++) {
        final frameFile = File(
          '${clipDir.path}/frame_${i.toString().padLeft(5, '0')}.jpg',
        );
        await frameFile.writeAsBytes(frames[i], flush: false);
      }

      outputMp4 = File('${clipDir.path}/$stem.mp4');
      final framePattern = _escapePath('${clipDir.path}/frame_%05d.jpg');
      final outputPath = _escapePath(outputMp4.path);
      final command =
          '-y -framerate ${_config.targetFps} -i $framePattern -c:v libx264 -pix_fmt yuv420p -movflags +faststart $outputPath';
      final session = await FFmpegKit.execute(command);
      final returnCode = await session.getReturnCode();
      if (!ReturnCode.isSuccess(returnCode) || !await outputMp4.exists()) {
        throw Exception('Failed to encode MP4 evidence clip.');
      }

      final url = await _cloudinary.uploadVideo(
        file: outputMp4,
        publicId: '${DateTime.now().toIso8601String()}_${_config.deviceId}_$stem',
        context: {
          'device_id': _config.deviceId,
          'event': 'sleeping',
          'confidence': confidence.toStringAsFixed(4),
          'frame_count': _buffer.length.toString(),
          'clip_seconds': (_buffer.length / _config.targetFps).toStringAsFixed(2),
        },
      );
      return url;
    } finally {
      if (outputMp4 != null && await outputMp4.exists()) {
        try {
          await outputMp4.delete();
        } catch (_) {
          // Best-effort cleanup.
        }
      }
      if (clipDir != null && await clipDir.exists()) {
        try {
          await clipDir.delete(recursive: true);
        } catch (_) {
          // Best-effort cleanup.
        }
      }
      _uploadInFlight = false;
    }
  }

  String _escapePath(String path) {
    return "'${path.replaceAll("'", "'\\''")}'";
  }

  Future<String?> _uploadSimulatorImageEvidence(double confidence) async {
    if (!_cloudinary.enabled || _uploadInFlight || _buffer.isEmpty) {
      return null;
    }

    _uploadInFlight = true;
    File? frameFile;
    try {
      final dir = await getTemporaryDirectory();
      final now = DateTime.now();
      final stamp =
          '${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}';
      final stem =
          'sleeping_sim_${stamp}_conf${confidence.toStringAsFixed(2)}';

      frameFile = File('${dir.path}/$stem.jpg');
      await frameFile.writeAsBytes(_buffer.last, flush: true);

      final url = await _cloudinary.uploadImage(
        file: frameFile,
        publicId: '${DateTime.now().toIso8601String()}_${_config.deviceId}_$stem',
        context: {
          'device_id': _config.deviceId,
          'event': 'sleeping',
          'confidence': confidence.toStringAsFixed(4),
          'frame_count': _buffer.length.toString(),
          'clip_seconds': (_buffer.length / _config.targetFps).toStringAsFixed(2),
          'evidence_mode': 'ios_simulator_single_frame',
        },
      );
      return url;
    } finally {
      if (frameFile != null && await frameFile.exists()) {
        try {
          await frameFile.delete();
        } catch (_) {
          // Best-effort cleanup.
        }
      }
      _uploadInFlight = false;
    }
  }
}
