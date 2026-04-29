import 'package:flutter/foundation.dart';

@immutable
class WalletModel {
  final String id;
  final String userId;
  final double balanceIdr;
  final double balancePts;
  final DateTime updatedAt;

  const WalletModel({
    required this.id,
    required this.userId,
    required this.balanceIdr,
    required this.balancePts,
    required this.updatedAt,
  });

  factory WalletModel.fromJson(Map<String, dynamic> json) {
    return WalletModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      balanceIdr: double.parse(json['balance_idr'].toString()),
      balancePts: double.parse(json['balance_pts'].toString()),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}
