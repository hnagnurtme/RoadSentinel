import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class AppTextField extends StatelessWidget {
  final TextEditingController? controller;
  final String? labelText;
  final String? hintText;
  final String? errorText;
  final bool obscureText;
  final TextInputType? keyboardType;
  final String? Function(String?)? validator;
  final void Function(String)? onChanged;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final int maxLines;
  final bool enabled;

  const AppTextField({
    super.key,
    this.controller,
    this.labelText,
    this.hintText,
    this.errorText,
    this.obscureText = false,
    this.keyboardType,
    this.validator,
    this.onChanged,
    this.prefixIcon,
    this.suffixIcon,
    this.maxLines = 1,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      validator: validator,
      onChanged: onChanged,
      maxLines: obscureText ? 1 : maxLines,
      enabled: enabled,
      decoration: InputDecoration(
        labelText: labelText,
        hintText: hintText,
        errorText: errorText,
        prefixIcon: prefixIcon,
        suffixIcon: suffixIcon,
        filled: true,
        fillColor: enabled ? Colors.white : Colors.grey[100],
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8.0),
          borderSide: const BorderSide(color: AppColors.textHint),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8.0),
          borderSide: const BorderSide(color: AppColors.textHint),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8.0),
          borderSide: const BorderSide(color: AppColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8.0),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8.0),
          borderSide: const BorderSide(color: AppColors.error, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
      ),
    );
  }
}

class AppPasswordField extends StatefulWidget {
  final TextEditingController? controller;
  final String? labelText;
  final String? hintText;
  final String? Function(String?)? validator;
  final void Function(String)? onChanged;

  const AppPasswordField({
    super.key,
    this.controller,
    this.labelText,
    this.hintText,
    this.validator,
    this.onChanged,
  });

  @override
  State<AppPasswordField> createState() => _AppPasswordFieldState();
}

class _AppPasswordFieldState extends State<AppPasswordField> {
  bool _obscureText = true;

  @override
  Widget build(BuildContext context) {
    return AppTextField(
      controller: widget.controller,
      labelText: widget.labelText,
      hintText: widget.hintText,
      obscureText: _obscureText,
      validator: widget.validator,
      onChanged: widget.onChanged,
      suffixIcon: IconButton(
        icon: Icon(
          _obscureText ? Icons.visibility_off : Icons.visibility,
          color: AppColors.textSecondary,
        ),
        onPressed: () {
          setState(() {
            _obscureText = !_obscureText;
          });
        },
      ),
    );
  }
}
