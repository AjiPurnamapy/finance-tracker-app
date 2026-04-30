import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/auth_models.dart';
import '../models/user_model.dart';
import '../services/api_client.dart';
import '../services/token_manager.dart';

// sharedPreferencesProvider now lives in token_manager.dart.
// Re-export it here so existing code that imports from auth_repository.dart
// does not break.
export '../services/token_manager.dart' show sharedPreferencesProvider;

class AuthRepository {
  final ApiClient _apiClient;
  final TokenManager _tokenManager;

  AuthRepository(this._apiClient, this._tokenManager);

  Future<void> login(String email, String password) async {
    final response = await _apiClient.post('/auth/login', body: {
      'email': email,
      'password': password,
    }, requiresAuth: false);

    final tokenResponse = TokenResponse.fromJson(response);
    await _tokenManager.saveTokens(
        tokenResponse.accessToken, tokenResponse.refreshToken);
  }

  Future<void> register(
    String email,
    String password,
    String fullName, {
    String role = 'parent',
  }) async {
    await _apiClient.post('/auth/register', body: {
      'email': email,
      'password': password,
      'full_name': fullName,
      'role': role,
    }, requiresAuth: false);
  }

  Future<User> getCurrentUser() async {
    if (!await hasToken) {
      throw ApiException(401, 'No token found locally');
    }
    final response = await _apiClient.get('/users/me');
    return User.fromJson(response);
  }

  /// Update the user's role via PATCH /users/me
  Future<User> updateRole(String role) async {
    final response = await _apiClient.patch('/users/me', body: {'role': role});
    return User.fromJson(response);
  }

  Future<void> logout() async {
    final refreshToken = await _tokenManager.getRefreshToken();

    if (refreshToken != null && await hasToken) {
      try {
        await _apiClient.post('/auth/logout', body: {
          'refresh_token': refreshToken,
        });
      } catch (_) {
        // Still clear local tokens even if server request fails.
      }
    }
    await _tokenManager.clearTokens();
  }

  /// True if an access token exists in secure storage.
  Future<bool> get hasToken => _tokenManager.hasToken();
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(tokenManagerProvider),
  );
});
