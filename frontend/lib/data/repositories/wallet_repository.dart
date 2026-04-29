import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/wallet_model.dart';
import '../models/transaction_model.dart';
import '../services/api_client.dart';

class WalletRepository {
  final ApiClient _apiClient;

  WalletRepository(this._apiClient);

  Future<WalletModel> getMyWallet() async {
    final response = await _apiClient.get('/wallets/me');
    return WalletModel.fromJson(response as Map<String, dynamic>);
  }

  Future<List<TransactionModel>> listTransactions({
    int page = 1,
    int perPage = 20,
  }) async {
    final response = await _apiClient.get(
      '/transactions/?page=$page&per_page=$perPage',
    );
    final items = response as List<dynamic>;
    return items
        .map((e) => TransactionModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

final walletRepositoryProvider = Provider<WalletRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WalletRepository(apiClient);
});
