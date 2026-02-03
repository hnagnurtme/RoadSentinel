import 'package:flutter/foundation.dart';

class Logger {
  static void log(String message, {String tag = 'APP'}) {
    if (kDebugMode) {
      print('[$tag] ${DateTime.now()}: $message');
    }
  }

  static void error(
    String message, {
    String tag = 'ERROR',
    Object? error,
    StackTrace? stackTrace,
  }) {
    if (kDebugMode) {
      print('[$tag] ${DateTime.now()}: $message');
      if (error != null) print('Error: $error');
      if (stackTrace != null) print('StackTrace: $stackTrace');
    }
  }

  static void debug(String message, {String tag = 'DEBUG'}) {
    if (kDebugMode) {
      print('[$tag] ${DateTime.now()}: $message');
    }
  }

  static void info(String message, {String tag = 'INFO'}) {
    if (kDebugMode) {
      print('[$tag] ${DateTime.now()}: $message');
    }
  }

  static void warning(String message, {String tag = 'WARNING'}) {
    if (kDebugMode) {
      print('[$tag] ${DateTime.now()}: $message');
    }
  }
}
