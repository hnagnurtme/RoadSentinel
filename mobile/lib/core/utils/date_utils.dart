import 'package:intl/intl.dart';

class AppDateUtils {
  static const String defaultDateFormat = 'dd/MM/yyyy';
  static const String defaultDateTimeFormat = 'dd/MM/yyyy HH:mm';
  static const String apiDateFormat = 'yyyy-MM-dd';
  static const String apiDateTimeFormat = 'yyyy-MM-ddTHH:mm:ss';

  // Format DateTime to String
  static String formatDate(DateTime? date, {String? format}) {
    if (date == null) return '';
    return DateFormat(format ?? defaultDateFormat).format(date);
  }

  static String formatDateTime(DateTime? date, {String? format}) {
    if (date == null) return '';
    return DateFormat(format ?? defaultDateTimeFormat).format(date);
  }

  // Parse String to DateTime
  static DateTime? parseDate(String? dateString, {String? format}) {
    if (dateString == null || dateString.isEmpty) return null;
    try {
      return DateFormat(format ?? defaultDateFormat).parse(dateString);
    } catch (e) {
      return null;
    }
  }

  // Get time ago (e.g., "2 giờ trước")
  static String timeAgo(DateTime? date) {
    if (date == null) return '';

    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inDays > 365) {
      return '${(difference.inDays / 365).floor()} năm trước';
    } else if (difference.inDays > 30) {
      return '${(difference.inDays / 30).floor()} tháng trước';
    } else if (difference.inDays > 0) {
      return '${difference.inDays} ngày trước';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} giờ trước';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} phút trước';
    } else {
      return 'Vừa xong';
    }
  }
}
