class ApiConstants {
  // Base URL
  static const String baseUrl = 'http://localhost:8080/api';

  // Auth endpoints
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String logout = '/auth/logout';
  static const String refreshToken = '/auth/refresh';

  // User endpoints
  static const String profile = '/user/profile';
  static const String updateProfile = '/user/update';

  // Timeout
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
