import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/savings_goal_model.dart';
import '../services/api_client.dart';

class SavingsRepository {
  final ApiClient _apiClient;

  SavingsRepository(this._apiClient);

  Future<List<SavingsGoalModel>> listGoals() async {
    final response = await _apiClient.get('/savings-goals');
    final items = response as List<dynamic>;
    return items
        .map((e) => SavingsGoalModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<SavingsGoalModel> createGoal({
    required String name,
    required double targetAmount,
  }) async {
    final response = await _apiClient.post('/savings-goals', body: {
      'name': name,
      'target_amount': targetAmount.toStringAsFixed(2),
    });
    return SavingsGoalModel.fromJson(response as Map<String, dynamic>);
  }

  Future<SavingsGoalModel> contribute({
    required String goalId,
    required double amount,
  }) async {
    final response = await _apiClient.post(
      '/savings-goals/$goalId/contribute',
      body: {'amount': amount.toStringAsFixed(2)},
    );
    return SavingsGoalModel.fromJson(response as Map<String, dynamic>);
  }

  Future<void> deleteGoal(String goalId) async {
    await _apiClient.delete('/savings-goals/$goalId');
  }
}

final savingsRepositoryProvider = Provider<SavingsRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SavingsRepository(apiClient);
});
