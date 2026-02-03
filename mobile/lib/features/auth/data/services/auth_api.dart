import '../../../../core/network/api_client.dart';
import '../../../../core/constants/api_constants.dart';
import '../models/login_request.dart';

class AuthApi {
  final ApiClient _apiClient = ApiClient();

  // Login
  Future<LoginResponse> login(LoginRequest request) async {
    try {
      final response = await _apiClient.post(
        ApiConstants.login,
        data: request.toJson(),
      );

      return LoginResponse.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  // Register
  Future<LoginResponse> register(Map<String, dynamic> data) async {
    try {
      final response = await _apiClient.post(ApiConstants.register, data: data);

      return LoginResponse.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  // Logout
  Future<void> logout() async {
    try {
      await _apiClient.post(ApiConstants.logout);
    } catch (e) {
      rethrow;
    }
  }

  // Refresh token
  Future<LoginResponse> refreshToken(String refreshToken) async {
    try {
      final response = await _apiClient.post(
        ApiConstants.refreshToken,
        data: {'refreshToken': refreshToken},
      );

      return LoginResponse.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }
}
