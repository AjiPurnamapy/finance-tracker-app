import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../data/models/savings_goal_model.dart';
import '../../../../data/repositories/savings_repository.dart';
import '../../../../data/services/api_client.dart';

class SavingsViewModel extends AsyncNotifier<List<SavingsGoalModel>> {
  @override
  Future<List<SavingsGoalModel>> build() async {
    return _load();
  }

  Future<List<SavingsGoalModel>> _load() async {
    try {
      return await ref.read(savingsRepositoryProvider).listGoals();
    } catch (e) {
      // M-3: NOT_IN_FAMILY is a normal state (child not yet in family),
      // return empty list so the UI shows its empty/join-family state
      // rather than a red error screen.
      if (e is ApiException &&
          (e.statusCode == 404 || e.message.contains('NOT_IN_FAMILY'))) {
        return [];
      }
      rethrow;
    }
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_load);
  }

  Future<void> createGoal({
    required String name,
    required double targetAmount,
  }) async {
    final newGoal = await ref.read(savingsRepositoryProvider).createGoal(
          name: name,
          targetAmount: targetAmount,
        );
    state.whenData((goals) {
      state = AsyncValue.data([newGoal, ...goals]);
    });
  }

  Future<void> contribute({
    required String goalId,
    required double amount,
  }) async {
    final updated = await ref.read(savingsRepositoryProvider).contribute(
          goalId: goalId,
          amount: amount,
        );
    state.whenData((goals) {
      state = AsyncValue.data(
        goals.map((g) => g.id == goalId ? updated : g).toList(),
      );
    });
  }

  Future<void> deleteGoal(String goalId) async {
    await ref.read(savingsRepositoryProvider).deleteGoal(goalId);
    state.whenData((goals) {
      state = AsyncValue.data(goals.where((g) => g.id != goalId).toList());
    });
  }
}

final savingsViewModelProvider =
    AsyncNotifierProvider<SavingsViewModel, List<SavingsGoalModel>>(
  SavingsViewModel.new,
);
