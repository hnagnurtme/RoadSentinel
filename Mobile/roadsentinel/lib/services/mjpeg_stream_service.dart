import 'dart:async';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

class MjpegStreamService {
  final http.Client _client = http.Client();

  StreamSubscription<List<int>>? _subscription;
  bool _running = false;

  static const List<int> _jpegStart = [0xFF, 0xD8];
  static const List<int> _jpegEnd = [0xFF, 0xD9];

  Future<void> start({
    required String url,
    required void Function(Uint8List frameBytes) onFrame,
    required void Function(Object error) onError,
  }) async {
    if (_running) {
      return;
    }

    _running = true;

    try {
      final request = http.Request('GET', Uri.parse(url));
      final response = await _client.send(request);

      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception('MJPEG stream status code: ${response.statusCode}');
      }

      final buffer = <int>[];

      _subscription = response.stream.listen(
        (chunk) {
          if (!_running) {
            return;
          }

          buffer.addAll(chunk);
          if (buffer.length > 2 * 1024 * 1024) {
            buffer.removeRange(0, buffer.length - 512 * 1024);
          }

          while (true) {
            final start = _indexOfBytes(buffer, _jpegStart);
            final end = _indexOfBytes(buffer, _jpegEnd, startIndex: start + 2);

            if (start == -1 || end == -1 || end <= start) {
              break;
            }

            final frame = Uint8List.fromList(buffer.sublist(start, end + 2));
            buffer.removeRange(0, end + 2);
            onFrame(frame);
          }
        },
        onError: onError,
        onDone: () {
          if (_running) {
            onError(Exception('MJPEG stream closed by server'));
          }
        },
        cancelOnError: true,
      );
    } catch (error) {
      _running = false;
      onError(error);
    }
  }

  Future<void> stop() async {
    _running = false;
    await _subscription?.cancel();
    _subscription = null;
  }

  void dispose() {
    _client.close();
  }

  int _indexOfBytes(List<int> source, List<int> pattern, {int startIndex = 0}) {
    if (pattern.isEmpty || source.length < pattern.length) {
      return -1;
    }

    for (var i = startIndex; i <= source.length - pattern.length; i++) {
      var matched = true;
      for (var j = 0; j < pattern.length; j++) {
        if (source[i + j] != pattern[j]) {
          matched = false;
          break;
        }
      }
      if (matched) {
        return i;
      }
    }

    return -1;
  }
}
