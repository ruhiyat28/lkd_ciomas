import 'package:flutter/material.dart';

/// Color palette — selaras dengan tema web desktop, dengan sentuhan
/// minimalis modern ala bank digital (BCA-style).
class AppColors {
  AppColors._();

  // Primary — biru korporat sama seperti web
  static const Color primary = Color(0xFF1A56DB);
  static const Color primaryDark = Color(0xFF1044B4);
  static const Color primaryDeep = Color(0xFF0B2E7A);
  static const Color primaryLight = Color(0xFF3B82F6);
  static const Color primarySoft = Color(0xFFE8EFFD);

  // Accent — kuning emas (BCA-style highlight)
  static const Color accent = Color(0xFFF5B400);
  static const Color accentLight = Color(0xFFFFE082);

  // Surfaces
  static const Color background = Color(0xFFF6F8FB);
  static const Color surface = Colors.white;
  static const Color card = Colors.white;
  static const Color surfaceMuted = Color(0xFFF1F5F9);

  // Text
  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF64748B);
  static const Color textHint = Color(0xFF94A3B8);
  static const Color border = Color(0xFFE5E9F0);

  // Semantic
  static const Color success = Color(0xFF16A34A);
  static const Color warning = Color(0xFFD97706);
  static const Color error = Color(0xFFDC2626);
  static const Color info = Color(0xFF1E88E5);

  static const Color statusWaiting = Color(0xFFD97706);
  static const Color statusApproved = Color(0xFF16A34A);
  static const Color statusRejected = Color(0xFFDC2626);
  static const Color statusPending = Color(0xFFFFF3E0);

  static const Color divider = Color(0xFFEDF1F6);
  static const Color disabled = Color(0xFF94A3B8);

  static const Color sidebarBg = Color(0xFF0F172A);
  static const Color sidebarText = Color(0xFF94A3B8);

  // Role colors
  static const Color roleNasabah = Color(0xFF1A56DB);
  static const Color rolePenagih = Color(0xFFE65100);
  static const Color roleVerifikator = Color(0xFF6A1B9A);
  static const Color roleKader = Color(0xFF00695C);
  static const Color roleAdmin = Color(0xFFB71C1C);

  // Gradient untuk kartu saldo (BCA-style biru gelap)
  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF1A56DB),
      Color(0xFF0B2E7A),
    ],
  );

  static const LinearGradient cardGradientSoft = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF3B82F6),
      Color(0xFF1A56DB),
    ],
  );
}
