import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../data/models/task_model.dart';
import '../../../../data/repositories/task_repository.dart';
import '../../../../data/services/api_client.dart';

@immutable
class TasksState {
  final List<TaskModel> allTasks;
  final String? selectedStatus; // null = show all

  const TasksState({
    required this.allTasks,
    this.selectedStatus,
  });

  List<TaskModel> get filteredTasks {
    if (selectedStatus == null) return allTasks;
    return allTasks.where((t) => t.status == selectedStatus).toList();
  }

  TasksState copyWith({
    List<TaskModel>? allTasks,
    Object? selectedStatus = _sentinel,
  }) {
    return TasksState(
      allTasks: allTasks ?? this.allTasks,
      selectedStatus:
          selectedStatus == _sentinel ? this.selectedStatus : selectedStatus as String?,
    );
  }
}

const _sentinel = Object();

class TaskViewModel extends AsyncNotifier<TasksState> {
  @override
  Future<TasksState> build() async {
    return _load();
  }

  Future<TasksState> _load() async {
    try {
      final tasks = await ref.read(taskRepositoryProvider).listTasks();
      // Preserve the current filter if re-loading
      final currentFilter = state.hasValue ? state.requireValue.selectedStatus : null;
      return TasksState(allTasks: tasks, selectedStatus: currentFilter);
    } catch (e) {
      // NOT_IN_FAMILY → return empty state instead of error screen
      if (e is ApiException &&
          (e.statusCode == 404 || e.message.contains('NOT_IN_FAMILY'))) {
        return const TasksState(allTasks: []);
      }
      rethrow;
    }
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_load);
  }

  void filterByStatus(String? status) {
    state.whenData((current) {
      state = AsyncValue.data(current.copyWith(selectedStatus: status));
    });
  }

  /// Child submits a task. Optimistically updates the status in the list.
  Future<void> submitTask(String taskId) async {
    // Optimistic update
    state.whenData((current) {
      final updated = current.allTasks
          .map((t) => t.id == taskId ? t.copyWith(status: 'submitted') : t)
          .toList();
      state = AsyncValue.data(current.copyWith(allTasks: updated));
    });

    try {
      final updatedTask = await ref.read(taskRepositoryProvider).submitTask(taskId);
      state.whenData((current) {
        final tasks = current.allTasks
            .map((t) => t.id == taskId ? updatedTask : t)
            .toList();
        state = AsyncValue.data(current.copyWith(allTasks: tasks));
      });
    } catch (_) {
      // Rollback optimistic update
      state = await AsyncValue.guard(_load);
      rethrow;
    }
  }
}

final taskViewModelProvider =
    AsyncNotifierProvider<TaskViewModel, TasksState>(TaskViewModel.new);
