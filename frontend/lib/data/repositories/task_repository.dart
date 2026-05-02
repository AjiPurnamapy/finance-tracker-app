import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/task_model.dart';
import '../services/api_client.dart';

class TaskRepository {
  final ApiClient _apiClient;

  TaskRepository(this._apiClient);

  /// List tasks for the current user.
  /// Child sees only their own assigned tasks; parent sees all family tasks.
  Future<List<TaskModel>> listTasks({
    String? status,
    int page = 1,
    int perPage = 50,
  }) async {
    var path = '/tasks/?page=$page&per_page=$perPage';
    if (status != null) path += '&status=$status';

    final response = await _apiClient.get(path);
    final items = response as List<dynamic>;
    return items
        .map((e) => TaskModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get a single task by ID.
  Future<TaskModel> getTask(String taskId) async {
    final response = await _apiClient.get('/tasks/$taskId');
    return TaskModel.fromJson(response as Map<String, dynamic>);
  }

  /// Child submits a task for parent review.
  Future<TaskModel> submitTask(String taskId) async {
    final response = await _apiClient.post('/tasks/$taskId/submit');
    return TaskModel.fromJson(response as Map<String, dynamic>);
  }
}

final taskRepositoryProvider = Provider<TaskRepository>((ref) {
  return TaskRepository(ref.watch(apiClientProvider));
});
