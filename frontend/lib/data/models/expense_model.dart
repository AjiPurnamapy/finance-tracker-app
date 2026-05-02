import 'package:flutter/foundation.dart';

@immutable
class ExpenseModel {
  final String id;
  final double amount;
  final String currency;
  final String category;
  final String title;
  final String? description;
  final DateTime spentAt;
  final bool deductFromWallet;

  const ExpenseModel({
    required this.id,
    required this.amount,
    required this.currency,
    required this.category,
    required this.title,
    this.description,
    required this.spentAt,
    required this.deductFromWallet,
  });

  factory ExpenseModel.fromJson(Map<String, dynamic> json) {
    return ExpenseModel(
      id: json['id'] as String,
      amount: double.parse(json['amount'].toString()),
      currency: json['currency'] as String? ?? 'IDR',
      category: json['category'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      spentAt: DateTime.parse(json['spent_at'] as String),
      deductFromWallet: json['deduct_from_wallet'] as bool? ?? false,
    );
  }
}

/// Maps backend category values to display labels
const Map<String, String> kExpenseCategoryLabels = {
  'food_dining': 'Makanan',
  'transportation': 'Transportasi',
  'entertainment': 'Hiburan',
  'shopping': 'Belanja',
  'education': 'Pendidikan',
  'health': 'Kesehatan',
  'utilities': 'Utilitas',
  'other': 'Lainnya',
};
