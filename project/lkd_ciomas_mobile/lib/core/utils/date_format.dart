import 'package:intl/intl.dart';

extension DateFormatExt on DateTime {
  String get toDateString => DateFormat('dd MMM yyyy', 'id').format(this);
  String get toDateTimeString =>
      DateFormat('dd MMM yyyy HH:mm', 'id').format(this);
  String get toApiDate => DateFormat('yyyy-MM-dd').format(this);
}

String formatDateApi(String? dateStr) {
  if (dateStr == null || dateStr.isEmpty) return '-';
  try {
    final dt = DateTime.parse(dateStr);
    return DateFormat('dd MMM yyyy', 'id').format(dt);
  } catch (_) {
    return dateStr;
  }
}

String formatDateTime(String? dateStr) {
  if (dateStr == null || dateStr.isEmpty) return '-';
  try {
    final dt = DateTime.parse(dateStr);
    return DateFormat('dd MMM yyyy HH:mm', 'id').format(dt);
  } catch (_) {
    return dateStr;
  }
}
