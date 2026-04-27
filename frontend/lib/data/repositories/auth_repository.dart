import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/auth_models.dart';
import '../models/user_model.dart';
import '../services/api_client.dart';

// Override this provider in main.dart once SharedPreferences is initialized
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});

class AuthRepository {
  final ApiClient _apiClient;
  final SharedPreferences _prefs;

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';

  AuthRepository(this._apiClient, this._prefs);

  Future<void> login(String email, String password) async {
    final response = await _apiClient.post('/auth/login', body: {
      'email': email,
      'password': password,
    });
    
    final tokenResponse = TokenResponse.fromJson(response);
    await _saveTokens(tokenResponse.accessToken, tokenResponse.refreshToken);
  }

  Future<void> register(String email, String password, String fullName, {String role = 'parent'}) async {
    await _apiClient.post('/auth/register', body: {
      'email': email,
      'password': password,
      'full_name': fullName,
      'role': role,
    });
  }

  Future<User> getCurrentUser() async {
    final token = _prefs.getString(_accessTokenKey);
    if (token == null) {
      throw ApiException(401, 'No token found locally');
    }
    
    final response = await _apiClient.get('/users/me', token: token);
    return User.fromJson(response);
  }

  Future<void> logout() async {
    final refreshToken = _prefs.getString(_refreshTokenKey);
    final accessToken = _prefs.getString(_accessTokenKey);
    
    if (refreshToken != null && accessToken != null) {
      try {
        await _apiClient.post('/auth/logout', body: {
          'refresh_token': refreshToken,
        }, token: accessToken);
      } catch (_) {
        // We still want to clear local tokens even if the server request fails.
      }
    }
    await _clearTokens();
  }

  Future<void> _saveTokens(String access, String refresh) async {
    await _prefs.setString(_accessTokenKey, access);
    await _prefs.setString(_refreshTokenKey, refresh);
  }

  Future<void> _clearTokens() async {
    await _prefs.remove(_accessTokenKey);
    await _prefs.remove(_refreshTokenKey);
  }

  bool get hasToken => _prefs.containsKey(_accessTokenKey);
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(sharedPreferencesProvider),
  );
});
