import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:shared_preferences/shared_preferences.dart';

// ── Shared Preferences provider ───────────────────────────────────────────────

/// Must be overridden in `main.dart` after `SharedPreferences.getInstance()`.
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});

// ── Token Manager ─────────────────────────────────────────────────────────────

/// Single source of truth for JWT token storage. (H-3 + C-1 fix)
///
/// Storage strategy:
/// - **Native** (Android/iOS/Windows/macOS/Linux): `flutter_secure_storage`
///   → Android EncryptedSharedPreferences (AES-256) / iOS Keychain /
///     Windows DPAPI / macOS Keychain / libsecret on Linux.
/// - **Web**: `SharedPreferences` (localStorage) — no secure enclave on web.
///   Documented risk; for production web use HttpOnly cookies instead.
class TokenManager {
  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';

  // Native secure storage configuration
  static const _secure = FlutterSecureStorage(
    // Android: use EncryptedSharedPreferences (AES-256 via Android Keystore)
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    // iOS/macOS: accessible after first unlock (survives reboot without user)
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
    // Windows: DPAPI (Data Protection API) — tied to Windows user account
    wOptions: WindowsOptions(),
    // Linux: libsecret / gnome-keyring
    lOptions: LinuxOptions(),
    // macOS: Keychain
    mOptions: MacOsOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
  );

  // Web fallback
  final SharedPreferences? _prefs;

  const TokenManager({SharedPreferences? prefs}) : _prefs = prefs;

  // ── Read ──────────────────────────────────────────────────────────────

  Future<String?> getAccessToken() => _read(_accessKey);
  Future<String?> getRefreshToken() => _read(_refreshKey);

  // ── Write ─────────────────────────────────────────────────────────────

  Future<void> saveTokens(String access, String refresh) async {
    await _write(_accessKey, access);
    await _write(_refreshKey, refresh);
  }

  // ── Clear ─────────────────────────────────────────────────────────────

  Future<void> clearTokens() async {
    await _delete(_accessKey);
    await _delete(_refreshKey);
  }

  // ── Existence check ───────────────────────────────────────────────────

  Future<bool> hasToken() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }

  // ── Private helpers ───────────────────────────────────────────────────

  Future<String?> _read(String key) async {
    if (kIsWeb) return _prefs?.getString(key);
    return _secure.read(key: key);
  }

  Future<void> _write(String key, String value) async {
    if (kIsWeb) {
      await _prefs?.setString(key, value);
    } else {
      await _secure.write(key: key, value: value);
    }
  }

  Future<void> _delete(String key) async {
    if (kIsWeb) {
      await _prefs?.remove(key);
    } else {
      await _secure.delete(key: key);
    }
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

/// Riverpod provider for [TokenManager].
/// Consumed by ApiClient and AuthRepository — single token authority.
final tokenManagerProvider = Provider<TokenManager>((ref) {
  if (kIsWeb) {
    // Web needs SharedPreferences as localStorage fallback
    return TokenManager(prefs: ref.watch(sharedPreferencesProvider));
  }
  // Native: flutter_secure_storage handles everything, no SharedPreferences needed
  return const TokenManager();
});
