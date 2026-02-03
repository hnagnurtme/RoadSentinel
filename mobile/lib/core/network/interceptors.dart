import 'package:dio/dio.dart';
import '../utils/logger.dart';

// Auth Interceptor - thêm token vào header
class AuthInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    // TODO: Lấy token từ storage và thêm vào header
    // final token = await _getToken();
    // if (token != null) {
    //   options.headers['Authorization'] = 'Bearer $token';
    // }

    super.onRequest(options, handler);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    // TODO: Handle token refresh nếu 401
    if (err.response?.statusCode == 401) {
      // Refresh token logic
      Logger.warning('Unauthorized - Token expired or invalid');
    }

    super.onError(err, handler);
  }
}

// Logging Interceptor - log requests/responses
class LoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    Logger.debug(
      'REQUEST[${options.method}] => PATH: ${options.path}\n'
      'Headers: ${options.headers}\n'
      'Data: ${options.data}',
      tag: 'API',
    );
    super.onRequest(options, handler);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    Logger.debug(
      'RESPONSE[${response.statusCode}] => PATH: ${response.requestOptions.path}\n'
      'Data: ${response.data}',
      tag: 'API',
    );
    super.onResponse(response, handler);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    Logger.error(
      'ERROR[${err.response?.statusCode}] => PATH: ${err.requestOptions.path}\n'
      'Message: ${err.message}\n'
      'Response: ${err.response?.data}',
      tag: 'API',
      error: err,
    );
    super.onError(err, handler);
  }
}
