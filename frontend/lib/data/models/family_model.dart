import 'package:flutter/foundation.dart';

@immutable
class FamilyMemberModel {
  final String id;
  final String userId;
  final String fullName;
  final String email;
  final String role; // 'admin' | 'member'
  final DateTime joinedAt;

  const FamilyMemberModel({
    required this.id,
    required this.userId,
    required this.fullName,
    required this.email,
    required this.role,
    required this.joinedAt,
  });

  factory FamilyMemberModel.fromJson(Map<String, dynamic> json) {
    return FamilyMemberModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      fullName: json['full_name'] as String,
      email: json['email'] as String,
      role: json['role'] as String,
      joinedAt: DateTime.parse(json['joined_at'] as String),
    );
  }
}

@immutable
class FamilyModel {
  final String id;
  final String name;
  final int memberCount;
  final List<FamilyMemberModel> members;
  final DateTime createdAt;

  const FamilyModel({
    required this.id,
    required this.name,
    required this.memberCount,
    required this.members,
    required this.createdAt,
  });

  factory FamilyModel.fromJson(Map<String, dynamic> json) {
    final memberList = (json['members'] as List<dynamic>? ?? [])
        .map((m) => FamilyMemberModel.fromJson(m as Map<String, dynamic>))
        .toList();
    return FamilyModel(
      id: json['id'] as String,
      name: json['name'] as String,
      memberCount: json['member_count'] as int? ?? memberList.length,
      members: memberList,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
