import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../models/login_request.dart';
import '../services/auth_api.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthApi _authApi;

  AuthRepositoryImpl(this._authApi);

  @override
  Future<User> login(String email, String password) async {
    try {
      final request = LoginRequest(email: email, password: password);
      final response = await _authApi.login(request);

      // TODO: Save token to storage
      // await _saveToken(response.token, response.refreshToken);

      // Convert UserModel to User entity
      return User(
        id: response.user.id,
        email: response.user.email,
        name: response.user.name,
        avatar: response.user.avatar,
      );
    } catch (e) {
      rethrow;
    }
  }

  @override
  Future<User> register(String email, String password, String name) async {
    try {
      final response = await _authApi.register({
        'email': email,
        'password': password,
        'name': name,
      });

      // TODO: Save token to storage

      return User(
        id: response.user.id,
        email: response.user.email,
        name: response.user.name,
        avatar: response.user.avatar,
      );
    } catch (e) {
      rethrow;
    }
  }

  @override
  Future<void> logout() async {
    try {
      await _authApi.logout();
      // TODO: Clear token from storage
    } catch (e) {
      rethrow;
    }
  }

  @override
  Future<bool> isLoggedIn() async {
    // TODO: Check if token exists in storage
    return false;
  }

  @override
  Future<User?> getCurrentUser() async {
    // TODO: Get user from storage or API
    return null;
  }
}
