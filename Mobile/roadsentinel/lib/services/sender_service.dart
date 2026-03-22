import 'dart:async';
import 'dart:collection';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/app_config.dart';

class SenderService {
  SenderService(this._config);

  final AppConfig _config;
  final ListQueue<Map<String, dynamic>> _queue = ListQueue<Map<String, dynamic>>();

  final http.Client _http = http.Client();
  WebSocketChannel? _channel;
  Timer? _reconnectTimer;

  bool _running = false;

  Future<void> start() async {
    if (_running) {
      return;
    }

    _running = true;
    await _connectWs();
  }

  Future<void> stop() async {
    _running = false;
    _reconnectTimer?.cancel();
    await _channel?.sink.close();
    _channel = null;
    _http.close();
  }

  Future<void> send(Map<String, dynamic> payload) async {
    if (_queue.length >= _config.queueMaxsize) {
      _queue.removeFirst();
    }
    _queue.addLast(payload);
    await _flush();
  }

  Future<void> _connectWs() async {
    if (!_running) {
      return;
    }

    try {
      _channel = WebSocketChannel.connect(Uri.parse(_config.wsUrl));
      _channel!.stream.listen(
        (_) {},
        onDone: _scheduleReconnect,
        onError: (_) => _scheduleReconnect(),
      );
      await _flush();
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (!_running) {
      return;
    }

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(
      Duration(seconds: _config.reconnectDelaySeconds),
      _connectWs,
    );
  }

  Future<void> _flush() async {
    while (_queue.isNotEmpty) {
      final payload = _queue.first;
      final sentWs = await _trySendWs(payload);
      if (sentWs) {
        _queue.removeFirst();
        continue;
      }

      final sentHttp = await _trySendHttp(payload);
      if (sentHttp) {
        _queue.removeFirst();
      } else {
        break;
      }
    }
  }

  Future<bool> _trySendWs(Map<String, dynamic> payload) async {
    final channel = _channel;
    if (channel == null) {
      return false;
    }

    try {
      channel.sink.add(jsonEncode(payload));
      return true;
    } catch (_) {
      _scheduleReconnect();
      return false;
    }
  }

  Future<bool> _trySendHttp(Map<String, dynamic> payload) async {
    try {
      final response = await _http.post(
        Uri.parse(_config.httpUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (_) {
      return false;
    }
  }
}
