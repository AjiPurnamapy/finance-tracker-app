import 'package:flutter/painting.dart';

/// Centralized design tokens for FinanceFamily app.
/// Use these constants instead of raw Color hex values throughout the UI.
abstract final class AppColors {
  // ── Background surfaces ──────────────────────────────────────────────
  static const background = Color(0xFF0D1117);   // Main screen background
  static const surface    = Color(0xFF1A1F2E);   // Card / container background
  static const elevated   = Color(0xFF111620);   // Nav bar / elevated surface

  // ── Brand / Primary ──────────────────────────────────────────────────
  static const primary     = Color(0xFF137FEC);  // Blue — CTA, active states
  static const primaryDark = Color(0xFF0A5AB5);  // Darker blue for gradients

  // ── Semantic ─────────────────────────────────────────────────────────
  static const success     = Color(0xFF10B981);  // Green — income, complete
  static const successDark = Color(0xFF059669);  // Darker green
  static const error       = Color(0xFFEF4444);  // Red — debt, delete
  static const errorSurface = Color(0xFF2A1A1A); // Snackbar / error container bg
  static const errorText   = Color(0xFFFC8181);  // Form validation error text
  static const warning     = Color(0xFFF59E0B);  // Amber — points, alerts

  // ── Borders / Dividers ───────────────────────────────────────────────
  static const border      = Color(0xFF2A2F3E);  // Default card border

  // ── Text ─────────────────────────────────────────────────────────────
  static const textPrimary   = Color(0xFFFFFFFF);
  static const textSecondary = Color(0x99FFFFFF); // ~60% white
  static const textMuted     = Color(0x66FFFFFF); // ~40% white

  // ── State / Icon ─────────────────────────────────────────────────────
  static const disabledIcon = Color(0xFF4A5060);  // Empty state / offline icons
}
