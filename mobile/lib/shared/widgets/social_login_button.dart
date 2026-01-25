import 'package:flutter/material.dart';

class SocialLoginButton extends StatelessWidget {
  final Widget icon;
  final VoidCallback onPressed;
  final double size;

  const SocialLoginButton({
    super.key,
    required this.icon,
    required this.onPressed,
    this.size = 56,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onPressed,
      borderRadius: BorderRadius.circular(size / 2),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.grey.shade100, width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Center(child: icon),
      ),
    );
  }
}

class FacebookIcon extends StatelessWidget {
  final double size;

  const FacebookIcon({super.key, this.size = 24});

  @override
  Widget build(BuildContext context) {
    return Icon(Icons.facebook, size: size, color: const Color(0xFF1877F2));
  }
}

class GoogleIcon extends StatelessWidget {
  final double size;

  const GoogleIcon({super.key, this.size = 24});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(borderRadius: BorderRadius.circular(size / 2)),
      child: const Text(
        'G',
        style: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: Color(0xFF4285F4),
        ),
      ),
    );
  }
}

class AppleIcon extends StatelessWidget {
  final double size;

  const AppleIcon({super.key, this.size = 24});

  @override
  Widget build(BuildContext context) {
    return Icon(Icons.apple, size: size, color: Colors.black);
  }
}
