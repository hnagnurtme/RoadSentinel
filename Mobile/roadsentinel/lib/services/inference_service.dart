import 'dart:typed_data';

import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

import '../models/app_config.dart';
import '../models/detection.dart';

class _Candidate {
  _Candidate({
    required this.classId,
    required this.score,
    required this.x1,
    required this.y1,
    required this.x2,
    required this.y2,
  });

  final int classId;
  final double score;
  final double x1;
  final double y1;
  final double x2;
  final double y2;
}

class InferenceService {
  InferenceService(this._config);

  final AppConfig _config;
  Interpreter? _interpreter;

  bool get isReady => _interpreter != null;

  Future<void> load() async {
    if (_interpreter != null) {
      return;
    }

    final fullPath = _config.modelAssetPath;
    final relativePath = fullPath.replaceFirst(RegExp(r'^assets/'), '');

    try {
      // Try loading with the relative path (standard for tflite_flutter)
      _interpreter = await Interpreter.fromAsset(relativePath);
    } catch (e) {
      try {
        // Fallback to full path if relative fails
        _interpreter = await Interpreter.fromAsset(fullPath);
      } catch (e2) {
        throw Exception('Failed to load model from $fullPath (tried $relativePath and $fullPath): $e2');
      }
    }
  }

  void dispose() {
    _interpreter?.close();
    _interpreter = null;
  }

  Future<List<Detection>> infer(Uint8List jpegBytes) async {
    final interpreter = _interpreter;
    if (interpreter == null) return const [];

    final decoded = img.decodeJpg(jpegBytes);
    if (decoded == null) return const [];

    final inputTensor = interpreter.getInputTensor(0);
    final outputTensor = interpreter.getOutputTensor(0);

    final inputShape = inputTensor.shape;
    final outputShape = outputTensor.shape;

    // IMPORTANT: Sync resize with model's actual expected shape to avoid RangeError in getPixel
    final isNCHW = inputShape.length == 4 && inputShape[1] == 3;
    final modelH = inputShape[isNCHW ? 2 : 1];
    final modelW = inputShape[isNCHW ? 3 : 2];

    final resized = img.copyResize(
      decoded,
      width: modelW,
      height: modelH,
      interpolation: img.Interpolation.average,
    );

    // Use ByteData for maximum reliability and performance
    final input = _imageToByteData(resized, inputShape, inputTensor.type);
    final output = _allocateOutput(outputShape);

    try {
      interpreter.run(input, output);
    } catch (e, stack) {
      throw StateError(
          'TFLite run failed: $e\n'
          'Input: $inputShape (${inputTensor.type})\n'
          'Output: $outputShape (${outputTensor.type})\n'
          'Stack: $stack');
    }

    final detections = _decodeAndApplyNms(output, outputShape);
    detections.sort((a, b) => b.confidence.compareTo(a.confidence));

    if (detections.length <= _config.inferenceMaxDetections) {
      return detections;
    }
    return detections.take(_config.inferenceMaxDetections).toList(growable: false);
  }

  List _allocateOutput(List<int> shape) {
    if (shape.length == 4) {
      return List.generate(
        shape[0],
        (_) => List.generate(
          shape[1],
          (_) => List.generate(
            shape[2],
            (_) => List<double>.filled(shape[3], 0),
            growable: false,
          ),
          growable: false,
        ),
        growable: false,
      );
    }

    if (shape.length == 3) {
      return List.generate(
        shape[0],
        (_) => List.generate(
          shape[1],
          (_) => List<double>.filled(shape[2], 0),
          growable: false,
        ),
        growable: false,
      );
    }

    if (shape.length == 2) {
      return List.generate(
        shape[0],
        (_) => List<double>.filled(shape[1], 0),
        growable: false,
      );
    }

    throw StateError('Unsupported output tensor shape: $shape');
  }

  Uint8List _imageToByteData(img.Image image, List<int> shape, TensorType type) {
    final isNCHW = shape.length == 4 && shape[1] == 3;
    final h = shape[isNCHW ? 2 : 1];
    final w = shape[isNCHW ? 3 : 2];

    final elementSize = type == TensorType.uint8 ? 1 : 4;
    final buffer = Uint8List(1 * h * w * 3 * elementSize);
    final byteData = ByteData.view(buffer.buffer);
    var offset = 0;

    if (isNCHW) {
      for (var c = 0; c < 3; c++) {
        for (var y = 0; y < h; y++) {
          for (var x = 0; x < w; x++) {
            final pixel = image.getPixel(x, y);
            final val = switch (c) {
              0 => pixel.r,
              1 => pixel.g,
              _ => pixel.b,
            };

            if (type == TensorType.uint8) {
              byteData.setUint8(offset, val.toInt());
              offset += 1;
            } else {
              byteData.setFloat32(offset, val / 255.0, Endian.little);
              offset += 4;
            }
          }
        }
      }
    } else {
      for (var y = 0; y < h; y++) {
        for (var x = 0; x < w; x++) {
          final pixel = image.getPixel(x, y);
          final channels = [pixel.r, pixel.g, pixel.b];
          for (final val in channels) {
            if (type == TensorType.uint8) {
              byteData.setUint8(offset, val.toInt());
              offset += 1;
            } else {
              byteData.setFloat32(offset, val / 255.0, Endian.little);
              offset += 4;
            }
          }
        }
      }
    }
    return buffer;
  }

  List<Detection> _decodeAndApplyNms(dynamic output, List<int> shape) {
    // Check for SSD style output: [1, 300, 6]
    if (shape.length == 3 && shape[1] > 1 && shape[2] == 6) {
      return _decodeSSD(output[0]);
    }

    final rows = _normalizeToRows(output, shape);
    if (rows.isEmpty || rows.first.length < 6) {
      return const [];
    }

    final hasObjectness = rows.first.length == (_config.labels.length + 5);
    final classStart = hasObjectness ? 5 : 4;
    final candidates = <_Candidate>[];

    for (final row in rows) {
      if (row.length <= classStart) {
        continue;
      }

      final cx = row[0];
      final cy = row[1];
      final w = row[2];
      final h = row[3];

      final objectness = hasObjectness ? row[4] : 1.0;
      var bestClass = -1;
      var bestClassProb = 0.0;
      for (var i = classStart; i < row.length; i++) {
        final prob = row[i];
        if (prob > bestClassProb) {
          bestClassProb = prob;
          bestClass = i - classStart;
        }
      }

      if (bestClass < 0) {
        continue;
      }

      final score = objectness * bestClassProb;
      if (score < _config.inferenceConfidenceThreshold) {
        continue;
      }

      final normalized = _isNormalizedBox(cx, cy, w, h);
      final scale = normalized ? _config.modelInputSize.toDouble() : 1.0;

      final x1 = (cx - (w / 2)) * scale;
      final y1 = (cy - (h / 2)) * scale;
      final x2 = (cx + (w / 2)) * scale;
      final y2 = (cy + (h / 2)) * scale;

      if (x2 <= x1 || y2 <= y1) {
        continue;
      }

      candidates.add(
        _Candidate(
          classId: bestClass,
          score: score,
          x1: x1,
          y1: y1,
          x2: x2,
          y2: y2,
        ),
      );
    }

    final kept = _classWiseNms(candidates, _config.inferenceIouThreshold);
    return kept
        .map(
          (c) => Detection(
            label: c.classId < _config.labels.length
                ? _config.labels[c.classId]
                : 'class_${c.classId}',
            classId: c.classId,
            confidence: c.score,
            bbox: [c.x1, c.y1, c.x2, c.y2],
          ),
        )
        .toList(growable: false);
  }

  List<Detection> _decodeSSD(List<List<double>> rows) {
    if (rows.isNotEmpty) {
      print('SSD First Row: ${rows.first}');
    }
    final candidates = <Detection>[];
    for (final row in rows) {
      if (row.length < 6) continue;

      // SSD Output formats can vary. Common patterns:
      // Pattern A: [ymin, xmin, ymax, xmax, score, class] (Most common)
      // Pattern B: [ymin, xmin, ymax, xmax, class, score]
      // Pattern C: [xmin, ymin, xmax, ymax, score, class]

      // Determine which column is class and which is score
      double score;
      int classId;

      if (row[4] > 1.0 && row[5] <= 1.0) {
        // row[4] is class, row[5] is score
        classId = row[4].toInt();
        score = row[5];
      } else {
        // row[4] is score, row[5] is class (Pattern A)
        score = row[4];
        classId = row[5].toInt();
      }

      if (score < _config.inferenceConfidenceThreshold) {
        continue;
      }

      // Detect if ymin/xmin are swapped
      var y1 = row[0];
      var x1 = row[1];
      var y2 = row[2];
      var x2 = row[3];

      // If x1 > x2 or y1 > y2, it might be swapped or different format
      // But we'll stick to Pattern A for now as it matches the standard

      final normalized = _isNormalizedBox(x1, y1, x2, y2);
      final scale = normalized ? _config.modelInputSize.toDouble() : 1.0;

      candidates.add(
        Detection(
          label: classId < _config.labels.length
              ? _config.labels[classId]
              : 'class_$classId',
          classId: classId,
          confidence: score,
          bbox: [
            x1 * scale,
            y1 * scale,
            x2 * scale,
            y2 * scale,
          ],
        ),
      );
    }
    return candidates;
  }

  List<List<double>> _normalizeToRows(dynamic output, List<int> shape) {
    if (shape.length == 3 && shape[0] == 1) {
      final tensor = output[0];
      if (tensor is! List || tensor.isEmpty || tensor.first is! List) {
        return const [];
      }

      final matrix = List<List<double>>.from(tensor);
      if (shape[1] > shape[2]) {
        return _transpose(matrix);
      }
      return matrix;
    }

    if (shape.length == 2 && output is List) {
      return output.cast<List<double>>();
    }

    return const [];
  }

  List<List<double>> _transpose(List<List<double>> matrix) {
    if (matrix.isEmpty) {
      return const [];
    }

    final rowCount = matrix.length;
    final colCount = matrix.first.length;
    return List.generate(
      colCount,
      (c) => List.generate(
        rowCount,
        (r) => matrix[r][c],
        growable: false,
      ),
      growable: false,
    );
  }

  bool _isNormalizedBox(double cx, double cy, double w, double h) {
    return cx >= 0 && cx <= 2 && cy >= 0 && cy <= 2 && w > 0 && w <= 2 && h > 0 && h <= 2;
  }

  List<_Candidate> _classWiseNms(List<_Candidate> candidates, double iouThreshold) {
    final byClass = <int, List<_Candidate>>{};
    for (final c in candidates) {
      byClass.putIfAbsent(c.classId, () => <_Candidate>[]).add(c);
    }

    final kept = <_Candidate>[];
    for (final clsCandidates in byClass.values) {
      clsCandidates.sort((a, b) => b.score.compareTo(a.score));

      while (clsCandidates.isNotEmpty) {
        final best = clsCandidates.removeAt(0);
        kept.add(best);

        clsCandidates.removeWhere(
          (other) => _iou(best, other) >= iouThreshold,
        );
      }
    }

    kept.sort((a, b) => b.score.compareTo(a.score));
    return kept;
  }

  double _iou(_Candidate a, _Candidate b) {
    final xLeft = a.x1 > b.x1 ? a.x1 : b.x1;
    final yTop = a.y1 > b.y1 ? a.y1 : b.y1;
    final xRight = a.x2 < b.x2 ? a.x2 : b.x2;
    final yBottom = a.y2 < b.y2 ? a.y2 : b.y2;

    final interW = (xRight - xLeft).clamp(0, double.infinity);
    final interH = (yBottom - yTop).clamp(0, double.infinity);
    final interArea = interW * interH;

    final areaA = (a.x2 - a.x1) * (a.y2 - a.y1);
    final areaB = (b.x2 - b.x1) * (b.y2 - b.y1);
    final union = areaA + areaB - interArea;

    if (union <= 0) {
      return 0.0;
    }
    return interArea / union;
  }
}
