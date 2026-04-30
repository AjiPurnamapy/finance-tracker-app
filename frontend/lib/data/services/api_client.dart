import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart' show kIsWeb, kReleaseMode;

import 'token_manager.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException: [$statusCode] $message';
}

class ApiClient {
  final http.Client _client = http.Client();
  final TokenManager _tokenManager;

  static const Duration _timeout = Duration(seconds: 15);

  ApiClient(this._tokenManager);

  // ── Base URL (H-1 fix) ────────────────────────────────────────────────
  // Release builds always use HTTPS. Dev builds use the local emulator URLs.

  String get baseUrl {
    if (kReleaseMode) {
      // TODO: Replace with your production domain before release
      return 'https://api.yourdomain.com/api/v1';
    }
    // Development only ↓
    if (kIsWeb) return 'http://localhost:8000/api/v1';
    if (Platform.isAndroid) return 'http://10.0.2.2:8000/api/v1';
    return 'http://localhost:8000/api/v1'; // Windows / macOS / iOS sim
  }

  // ── Public API methods ────────────────────────────────────────────────

  Future<dynamic> get(String path, {bool requiresAuth = true}) =>
      _requestWithRefresh(
        (token) => _client
            .get(Uri.parse('$baseUrl$path'), headers: _buildHeaders(token))
            .timeout(_timeout),
        requiresAuth: requiresAuth,
      );

  Future<dynamic> post(
    String path, {
    Map<String, dynamic>? body,
    bool requiresAuth = true,
  }) =>
      _requestWithRefresh(
        (token) => _client
            .post(
              Uri.parse('$baseUrl$path'),
              headers: _buildHeaders(token),
              body: body != null ? jsonEncode(body) : null,
            )
            .timeout(_timeout),
        requiresAuth: requiresAuth,
      );

  Future<dynamic> patch(
    String path, {
    Map<String, dynamic>? body,
    bool requiresAuth = true,
  }) =>
      _requestWithRefresh(
        (token) => _client
            .patch(
              Uri.parse('$baseUrl$path'),
              headers: _buildHeaders(token),
              body: body != null ? jsonEncode(body) : null,
            )
            .timeout(_timeout),
        requiresAuth: requiresAuth,
      );

  Future<dynamic> delete(String path, {bool requiresAuth = true}) =>
      _requestWithRefresh(
        (token) => _client
            .delete(Uri.parse('$baseUrl$path'), headers: _buildHeaders(token))
            .timeout(_timeout),
        requiresAuth: requiresAuth,
      );

  // ── Token refresh interceptor ─────────────────────────────────────────

  Future<dynamic> _requestWithRefresh(
    Future<http.Response> Function(String? token) request, {
    required bool requiresAuth,
  }) async {
    final token =
        requiresAuth ? await _tokenManager.getAccessToken() : null;
    http.Response response = await request(token);

    // On 401, attempt token refresh once
    if (response.statusCode == 401 &&
        requiresAuth &&
        await _tokenManager.getRefreshToken() != null) {
      final refreshed = await _tryRefreshToken();
      if (refreshed) {
        response = await request(await _tokenManager.getAccessToken());
      }
    }

    return _processResponse(response);
  }

  Future<bool> _tryRefreshToken() async {
    final refreshToken = await _tokenManager.getRefreshToken();
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
        final jsonResponse =
            jsonDecode(response.body) as Map<String, dynamic>;
        final data = jsonResponse.containsKey('data')
            ? jsonResponse['data'] as Map<String, dynamic>
            : jsonResponse;

        final newAccess = data['access_token'] as String?;
        final newRefresh = data['refresh_token'] as String?;

        if (newAccess != null && newRefresh != null) {
          await _tokenManager.saveTokens(newAccess, newRefresh);
          return true;
        }
      }
      await _tokenManager.clearTokens();
      return false;
    } catch (_) {
      await _tokenManager.clearTokens();
      return false;
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────

  Map<String, String> _buildHeaders(String? token) {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null) headers['Authorization'] = 'Bearer $token';
    return headers;
  }

  dynamic _processResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;

      final decoded = jsonDecode(response.body);

      // Some endpoints (e.g. savings-goals) return a raw List, not a Map wrapper
      if (decoded is List) return decoded;

      final jsonResponse = decoded as Map<String, dynamic>;

      // Unwrap SuccessResponse / PaginatedResponse: { "success": true, "data": ... }
      if (jsonResponse.containsKey('success') &&
          jsonResponse['success'] == true) {
        return jsonResponse['data'];
      }
      return jsonResponse;
    } else {
      String errorMessage = 'Unknown error';
      try {
        final errorJson =
            jsonDecode(response.body) as Map<String, dynamic>;
        if (errorJson['detail'] is String) {
          errorMessage = errorJson['detail'];
        } else if (errorJson['detail'] is List) {
          errorMessage =
              (errorJson['detail'] as List).map((e) => e['msg']).join(', ');
        } else {
          errorMessage = errorJson.toString();
        }
      } catch (_) {
        if (response.body.isNotEmpty) errorMessage = response.body;
      }
      throw ApiException(response.statusCode, errorMessage);
    }
  }
}

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(tokenManagerProvider));
});
