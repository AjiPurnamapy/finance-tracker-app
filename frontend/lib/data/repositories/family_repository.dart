import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/family_model.dart';
import '../services/api_client.dart';

class FamilyRepository {
  final ApiClient _apiClient;

  FamilyRepository(this._apiClient);

  /// Returns null if user is not in any family yet
  Future<FamilyModel?> getMyFamily() async {
    try {
      final response = await _apiClient.get('/families/me');
      return FamilyModel.fromJson(response as Map<String, dynamic>);
    } on ApiException catch (e) {
      // 404 = not in a family yet
      if (e.statusCode == 404) return null;
      rethrow;
    }
  }

  /// Join a family via 6-digit invite code
  Future<FamilyModel> joinFamily(String inviteCode) async {
    final response = await _apiClient.post('/invitations/join', body: {
      'invite_code': inviteCode,
    });
    return FamilyModel.fromJson(response as Map<String, dynamic>);
  }
}

final familyRepositoryProvider = Provider<FamilyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return FamilyRepository(apiClient);
});
