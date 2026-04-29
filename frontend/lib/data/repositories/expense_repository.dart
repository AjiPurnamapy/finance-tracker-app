import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/expense_model.dart';
import '../services/api_client.dart';

class ExpenseRepository {
  final ApiClient _apiClient;

  ExpenseRepository(this._apiClient);

  Future<List<ExpenseModel>> listExpenses({
    String? category,
    int page = 1,
    int perPage = 20,
  }) async {
    var path = '/expenses/?page=$page&per_page=$perPage';
    if (category != null) path += '&category=$category';

    final response = await _apiClient.get(path);
    final items = response as List<dynamic>;
    return items
        .map((e) => ExpenseModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ExpenseModel> createExpense({
    required double amount,
    required String category,
    required String title,
    String? description,
    bool deductFromWallet = false,
  }) async {
    final Map<String, dynamic> body = {
      'amount': amount.toStringAsFixed(2),
      'category': category,
      'title': title,
      'deduct_from_wallet': deductFromWallet,
    };
    if(description != null) {
      body['description'] = description;
    }

    final response = await _apiClient.post('/expenses/', body: body);
    return ExpenseModel.fromJson(response as Map<String, dynamic>);
  }
}

final expenseRepositoryProvider = Provider<ExpenseRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ExpenseRepository(apiClient);
});
