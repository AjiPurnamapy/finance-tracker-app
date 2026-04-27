import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../data/models/user_model.dart';
import '../../../../data/repositories/auth_repository.dart';
import '../../../../data/services/api_client.dart';

class AuthViewModel extends AsyncNotifier<User?> {
  late AuthRepository _repository;

  @override
  Future<User?> build() async {
    _repository = ref.watch(authRepositoryProvider);
    return _checkAuthStatus();
  }

  Future<User?> _checkAuthStatus() async {
    if (_repository.hasToken) {
      try {
        final user = await _repository.getCurrentUser();
        return user;
      } on ApiException catch (e) {
        // Token is invalid or expired
        if (e.statusCode == 401) {
          await _repository.logout();
          return null;
        }
        // Other API errors (500, etc.)
        rethrow;
      } catch (e) {
        // Network errors like SocketException
        rethrow;
      }
    }
    return null;
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      await _repository.login(email, password);
      final user = await _repository.getCurrentUser();
      state = AsyncValue.data(user);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }

  Future<void> register(String email, String password, String fullName, {String role = 'parent'}) async {
    state = const AsyncValue.loading();
    try {
      await _repository.register(email, password, fullName, role: role);
      // Auto login after registration
      await _repository.login(email, password);
      final user = await _repository.getCurrentUser();
      state = AsyncValue.data(user);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }

  Future<void> logout() async {
    state = const AsyncValue.loading();
    await _repository.logout();
    state = const AsyncValue.data(null);
  }
}

final authViewModelProvider = AsyncNotifierProvider<AuthViewModel, User?>(() {
  return AuthViewModel();
});
