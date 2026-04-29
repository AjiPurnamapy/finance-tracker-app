import 'package:flutter/foundation.dart';

@immutable
class TransactionModel {
  final String id;
  final String walletId;
  final String type; // 'credit' | 'debit'
  final double amount;
  final String currency;
  final String? description;
  final DateTime createdAt;

  const TransactionModel({
    required this.id,
    required this.walletId,
    required this.type,
    required this.amount,
    required this.currency,
    this.description,
    required this.createdAt,
  });

  bool get isCredit => type == 'credit';

  factory TransactionModel.fromJson(Map<String, dynamic> json) {
    return TransactionModel(
      id: json['id'] as String,
      walletId: json['wallet_id'] as String,
      type: json['type'] as String,
      amount: double.parse(json['amount'].toString()),
      currency: json['currency'] as String? ?? 'IDR',
      description: json['description'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
