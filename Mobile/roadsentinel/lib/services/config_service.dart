import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/app_config.dart';

class ConfigService {
  static const _key = 'gateway_mobile_config_v1';

  Future<AppConfig> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) {
      return AppConfig.defaults();
    }

    try {
      final json = jsonDecode(raw) as Map<String, dynamic>;
      return AppConfig.fromJson(json);
    } catch (_) {
      return AppConfig.defaults();
    }
  }

  Future<void> save(AppConfig config) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(config.toJson()));
  }
}
