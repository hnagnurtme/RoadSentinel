import 'package:flutter/material.dart';
import '../../features/auth/presentation/pages/login_page.dart';

class AppRoutes {
  // Route names
  static const String login = '/login';
  static const String register = '/register';
  static const String home = '/home';
  static const String profile = '/profile';

  // Initial route
  static const String initial = login;

  // Route generator
  static Route<dynamic> generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case login:
        return MaterialPageRoute(builder: (_) => const LoginPage());

      // case register:
      //   return MaterialPageRoute(builder: (_) => const RegisterPage());

      // case home:
      //   return MaterialPageRoute(builder: (_) => const HomePage());

      // case profile:
      //   return MaterialPageRoute(builder: (_) => const ProfilePage());

      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Center(child: Text('No route defined for ${settings.name}')),
          ),
        );
    }
  }

  // Named routes map
  static Map<String, WidgetBuilder> get routes => {
    login: (context) => const LoginPage(),
    // register: (context) => const RegisterPage(),
    // home: (context) => const HomePage(),
    // profile: (context) => const ProfilePage(),
  };
}
