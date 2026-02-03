class Validators {
  // Email validator
  static String? email(String? value) {
    if (value == null || value.isEmpty) {
      return 'Vui lòng nhập email';
    }

    final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    if (!emailRegex.hasMatch(value)) {
      return 'Email không hợp lệ';
    }

    return null;
  }

  // Password validator
  static String? password(String? value) {
    if (value == null || value.isEmpty) {
      return 'Vui lòng nhập mật khẩu';
    }

    if (value.length < 6) {
      return 'Mật khẩu phải có ít nhất 6 ký tự';
    }

    return null;
  }

  // Required field validator
  static String? required(String? value, {String? fieldName}) {
    if (value == null || value.isEmpty) {
      return 'Vui lòng nhập ${fieldName ?? 'trường này'}';
    }
    return null;
  }

  // Phone validator
  static String? phone(String? value) {
    if (value == null || value.isEmpty) {
      return 'Vui lòng nhập số điện thoại';
    }

    final phoneRegex = RegExp(r'^(0|\+84)[3|5|7|8|9][0-9]{8}$');
    if (!phoneRegex.hasMatch(value)) {
      return 'Số điện thoại không hợp lệ';
    }

    return null;
  }

  // Confirm password validator
  static String? confirmPassword(String? value, String? password) {
    if (value == null || value.isEmpty) {
      return 'Vui lòng xác nhận mật khẩu';
    }

    if (value != password) {
      return 'Mật khẩu không khớp';
    }

    return null;
  }
}
