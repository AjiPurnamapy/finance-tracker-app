import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../data/models/expense_model.dart';
import '../../../../data/models/wallet_model.dart';
import '../../../../data/repositories/expense_repository.dart';
import '../../../../data/repositories/wallet_repository.dart';
import '../../../../data/services/api_client.dart';

class ChildHomeState {
  final WalletModel? wallet;
  final List<ExpenseModel> recentExpenses;
  final String? selectedCategory;
  final bool isLoading;
  final String? error;

  const ChildHomeState({
    this.wallet,
    this.recentExpenses = const [],
    this.selectedCategory,
    this.isLoading = false,
    this.error,
  });

  double get totalSpentThisMonth {
    final now = DateTime.now();
    return recentExpenses
        .where((e) => e.spentAt.year == now.year && e.spentAt.month == now.month)
        .fold(0.0, (sum, e) => sum + e.amount);
  }

  List<ExpenseModel> get filteredExpenses {
    if (selectedCategory == null) return recentExpenses;
    return recentExpenses
        .where((e) => e.category == selectedCategory)
        .toList();
  }

  ChildHomeState copyWith({
    WalletModel? wallet,
    List<ExpenseModel>? recentExpenses,
    String? selectedCategory,
    bool? isLoading,
    String? error,
    bool clearCategory = false,
    bool clearError = false,
  }) {
    return ChildHomeState(
      wallet: wallet ?? this.wallet,
      recentExpenses: recentExpenses ?? this.recentExpenses,
      selectedCategory:
          clearCategory ? null : selectedCategory ?? this.selectedCategory,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : error ?? this.error,
    );
  }
}

class ChildHomeViewModel extends AsyncNotifier<ChildHomeState> {
  @override
  Future<ChildHomeState> build() async {
    return _load();
  }

  Future<ChildHomeState> _load() async {
    final walletRepo = ref.read(walletRepositoryProvider);
    final expenseRepo = ref.read(expenseRepositoryProvider);

    WalletModel? wallet;
    try {
      wallet = await walletRepo.getMyWallet();
    } catch (e) {
      if (e is ApiException && (e.statusCode == 404 || e.message.contains('NOT_IN_FAMILY'))) {
        wallet = null;
      } else {
        rethrow;
      }
    }

    List<ExpenseModel> expenses = [];
    try {
      expenses = await expenseRepo.listExpenses(perPage: 10);
    } catch (e) {
      if (e is ApiException && (e.statusCode == 404 || e.message.contains('NOT_IN_FAMILY'))) {
        expenses = [];
      } else {
        rethrow;
      }
    }

    return ChildHomeState(
      wallet: wallet,
      recentExpenses: expenses,
    );
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_load);
  }

  Future<void> addExpense({
    required double amount,
    required String category,
    required String title,
    String? description,
    bool deductFromWallet = false,
  }) async {
    final expenseRepo = ref.read(expenseRepositoryProvider);
    final newExpense = await expenseRepo.createExpense(
      amount: amount,
      category: category,
      title: title,
      description: description,
      deductFromWallet: deductFromWallet,
    );
    state.whenData((s) {
      state = AsyncValue.data(
        s.copyWith(recentExpenses: [newExpense, ...s.recentExpenses]),
      );
    });
    // Refresh to update wallet balance too
    await refresh();
  }

  void selectCategory(String? category) {
    state.whenData((s) {
      state = AsyncValue.data(s.copyWith(
        selectedCategory: category,
        clearCategory: category == null,
      ));
    });
  }
}

final childHomeViewModelProvider =
    AsyncNotifierProvider<ChildHomeViewModel, ChildHomeState>(
  ChildHomeViewModel.new,
);
