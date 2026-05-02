import 'package:flutter/foundation.dart';

@immutable
class TaskModel {
  final String id;
  final String familyId;
  final String createdBy;
  final String assignedTo;
  final String title;
  final String? description;
  final double rewardAmount;
  final String rewardCurrency; // "IDR" | "PTS"
  final String status; // created | submitted | approved | rejected | completed
  final DateTime? dueDate;
  final bool isRecurring;
  final String? recurrenceType; // daily | weekly | custom
  final DateTime? completedAt;
  final String? rewardTransactionId;
  final DateTime createdAt;
  final DateTime updatedAt;

  const TaskModel({
    required this.id,
    required this.familyId,
    required this.createdBy,
    required this.assignedTo,
    required this.title,
    this.description,
    required this.rewardAmount,
    required this.rewardCurrency,
    required this.status,
    this.dueDate,
    required this.isRecurring,
    this.recurrenceType,
    this.completedAt,
    this.rewardTransactionId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory TaskModel.fromJson(Map<String, dynamic> json) {
    return TaskModel(
      id: json['id'] as String,
      familyId: json['family_id'] as String,
      createdBy: json['created_by'] as String,
      assignedTo: json['assigned_to'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      rewardAmount: double.parse(json['reward_amount'].toString()),
      rewardCurrency: json['reward_currency'] as String? ?? 'IDR',
      status: json['status'] as String,
      dueDate: json['due_date'] != null
          ? DateTime.parse(json['due_date'] as String)
          : null,
      isRecurring: json['is_recurring'] as bool? ?? false,
      recurrenceType: json['recurrence_type'] as String?,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'] as String)
          : null,
      rewardTransactionId: json['reward_transaction_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  TaskModel copyWith({String? status, DateTime? completedAt}) {
    return TaskModel(
      id: id,
      familyId: familyId,
      createdBy: createdBy,
      assignedTo: assignedTo,
      title: title,
      description: description,
      rewardAmount: rewardAmount,
      rewardCurrency: rewardCurrency,
      status: status ?? this.status,
      dueDate: dueDate,
      isRecurring: isRecurring,
      recurrenceType: recurrenceType,
      completedAt: completedAt ?? this.completedAt,
      rewardTransactionId: rewardTransactionId,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }
}
