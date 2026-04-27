import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:shared_preferences/shared_preferences.dart';

import '../repositories/auth_repository.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException: [$statusCode] $message';
}

class ApiClient {
  final http.Client _client = http.Client();
  final SharedPreferences _prefs;

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const Duration _timeout = Duration(seconds: 15);

  ApiClient(this._prefs);

  String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://localhost:8000/api/v1'; // Windows, macOS, iOS simulator
  }

  // ── Internal token helpers ─────────────────────────────────────────

  String? get _accessToken => _prefs.getString(_accessTokenKey);
  String? get _refreshToken => _prefs.getString(_refreshTokenKey);

  Future<void> _saveTokens(String access, String refresh) async {
    await _prefs.setString(_accessTokenKey, access);
    await _prefs.setString(_refreshTokenKey, refresh);
  }

  Future<void> _clearTokens() async {
    await _prefs.remove(_accessTokenKey);
    await _prefs.remove(_refreshTokenKey);
  }

  // ── Public API methods ─────────────────────────────────────────────

  /// GET with auto-token and refresh retry.
  Future<dynamic> get(String path, {bool requiresAuth = true}) async {
    return _requestWithRefresh((token) {
      return _client
          .get(Uri.parse('$baseUrl$path'), headers: _buildHeaders(token))
          .timeout(_timeout);
    }, requiresAuth: requiresAuth);
  }

  /// POST with auto-token and refresh retry.
  Future<dynamic> post(String path, {
    Map<String, dynamic>? body,
    bool requiresAuth = true,
  }) async {
    return _requestWithRefresh((token) {
      return _client
          .post(
            Uri.parse('$baseUrl$path'),
            headers: _buildHeaders(token),
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(_timeout);
    }, requiresAuth: requiresAuth);
  }

  /// PATCH with auto-token and refresh retry.
  Future<dynamic> patch(String path, {
    Map<String, dynamic>? body,
    bool requiresAuth = true,
  }) async {
    return _requestWithRefresh((token) {
      return _client
          .patch(
            Uri.parse('$baseUrl$path'),
            headers: _buildHeaders(token),
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(_timeout);
    }, requiresAuth: requiresAuth);
  }

  // ── Token refresh interceptor ──────────────────────────────────────

  Future<dynamic> _requestWithRefresh(
    Future<http.Response> Function(String? token) request, {
    required bool requiresAuth,
  }) async {
    final token = requiresAuth ? _accessToken : null;
    http.Response response = await request(token);

    // If 401 and we have a refresh token, try to refresh once
    if (response.statusCode == 401 && requiresAuth && _refreshToken != null) {
      final refreshed = await _tryRefreshToken();
      if (refreshed) {
        // Retry the original request with the new token
        response = await request(_accessToken);
      }
    }

    return _processResponse(response);
  }

  Future<bool> _tryRefreshToken() async {
    final refreshToken = _refreshToken;
    if (refreshToken == null) return false;

    try {
      final response = await _client
          .post(
            Uri.parse('$baseUrl/auth/refresh'),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: jsonEncode({'refresh_token': refreshToken}),
          )
          .timeout(_timeout);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final jsonResponse = jsonDecode(response.body) as Map<String, dynamic>;
        final data = jsonResponse.containsKey('data')
            ? jsonResponse['data'] as Map<String, dynamic>
            : jsonResponse;

        final newAccess = data['access_token'] as String?;
        final newRefresh = data['refresh_token'] as String?;

        if (newAccess != null && newRefresh != null) {
          await _saveTokens(newAccess, newRefresh);
          return true;
        }
      }
      // Refresh failed — clear tokens
      await _clearTokens();
      return false;
    } catch (_) {
      await _clearTokens();
      return false;
    }
  }

  // ── Shared helpers ─────────────────────────────────────────────────

  Map<String, String> _buildHeaders(String? token) {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  dynamic _processResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;

      final Map<String, dynamic> jsonResponse =
          jsonDecode(response.body) as Map<String, dynamic>;

      // Unwrap backend's SuccessResponse: { "success": true, "data": ... }
      if (jsonResponse.containsKey('success') &&
          jsonResponse['success'] == true) {
        return jsonResponse['data'];
      }
      return jsonResponse;
    } else {
      String errorMessage = 'Unknown error';
      try {
        final Map<String, dynamic> errorJson =
            jsonDecode(response.body) as Map<String, dynamic>;
        // FastAPI returns validation errors as list in 'detail' or string.
        if (errorJson['detail'] is String) {
          errorMessage = errorJson['detail'];
        } else if (errorJson['detail'] is List) {
          errorMessage =
              (errorJson['detail'] as List).map((e) => e['msg']).join(', ');
        } else {
          errorMessage = errorJson.toString();
        }
      } catch (_) {
        if (response.body.isNotEmpty) {
          errorMessage = response.body;
        }
      }
      throw ApiException(response.statusCode, errorMessage);
    }
  }
}

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(sharedPreferencesProvider));
});
