import '../entities/user.dart';
import '../repositories/auth_repository.dart';

class LoginUseCase {
  final AuthRepository _repository;

  LoginUseCase(this._repository);

  Future<User> call(String email, String password) async {
    // Validate inputs
    if (email.isEmpty) {
      throw Exception('Email không được để trống');
    }

    if (password.isEmpty) {
      throw Exception('Mật khẩu không được để trống');
    }

    if (password.length < 6) {
      throw Exception('Mật khẩu phải có ít nhất 6 ký tự');
    }

    // Call repository
    return await _repository.login(email, password);
  }
}

class RegisterUseCase {
  final AuthRepository _repository;

  RegisterUseCase(this._repository);

  Future<User> call(String email, String password, String name) async {
    // Validate inputs
    if (email.isEmpty || password.isEmpty || name.isEmpty) {
      throw Exception('Vui lòng điền đầy đủ thông tin');
    }

    if (password.length < 6) {
      throw Exception('Mật khẩu phải có ít nhất 6 ký tự');
    }

    // Call repository
    return await _repository.register(email, password, name);
  }
}

class LogoutUseCase {
  final AuthRepository _repository;

  LogoutUseCase(this._repository);

  Future<void> call() async {
    await _repository.logout();
  }
}
