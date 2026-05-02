import 'package:flutter/foundation.dart';

@immutable
class TransactionModel {
  final String id;
  final String familyId;
  final String? sourceWalletId;       // null = dari sistem (task reward)
  final String? destinationWalletId;  // null = keluar (expense)
  final double amount;
  final String currency;
  final String type; // 'task_reward' | 'allowance' | 'topup' | 'expense' | 'pts_exchange' | 'fund_request'
  final String description;
  final String? referenceType;
  final String? referenceId;
  final DateTime createdAt;

  const TransactionModel({
    required this.id,
    required this.familyId,
    this.sourceWalletId,
    this.destinationWalletId,
    required this.amount,
    required this.currency,
    required this.type,
    required this.description,
    this.referenceType,
    this.referenceId,
    required this.createdAt,
  });

  // Transaksi masuk jika ada destinationWalletId dan tidak ada sourceWalletId
  // atau type yang mengindikasikan pemasukan
  bool get isCredit => type == 'task_reward' ||
      type == 'allowance' ||
      type == 'topup' ||
      (type == 'fund_request' && sourceWalletId != null) ||
      (destinationWalletId != null && sourceWalletId == null); // General credit heuristic

  factory TransactionModel.fromJson(Map<String, dynamic> json) {
    return TransactionModel(
      id: json['id'] as String,
      familyId: json['family_id'] as String,
      sourceWalletId: json['source_wallet_id'] as String?,
      destinationWalletId: json['destination_wallet_id'] as String?,
      amount: double.parse(json['amount'].toString()),
      currency: json['currency'] as String? ?? 'IDR',
      type: json['type'] as String,
      description: json['description'] as String? ?? '',
      referenceType: json['reference_type'] as String?,
      referenceId: json['reference_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
