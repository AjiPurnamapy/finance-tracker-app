import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../data/models/task_model.dart';
import '../../../core/themes/app_colors.dart';
import '../view_models/task_view_model.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Status constants
// ─────────────────────────────────────────────────────────────────────────────

const _kAllStatus = [
  (value: null,          label: 'Semua'),
  (value: 'created',     label: 'Baru'),
  (value: 'submitted',   label: 'Dikirim'),
  (value: 'approved',    label: 'Disetujui'),
  (value: 'rejected',    label: 'Ditolak'),
  (value: 'completed',   label: 'Selesai'),
];

// ─────────────────────────────────────────────────────────────────────────────
// Root view
// ─────────────────────────────────────────────────────────────────────────────

class TasksView extends ConsumerWidget {
  const TasksView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(taskViewModelProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        bottom: false,
        child: state.when(
          loading: () => const _LoadingBody(),
          error: (e, _) => _ErrorBody(
            onRetry: () => ref.read(taskViewModelProvider.notifier).refresh(),
          ),
          data: (data) => _Body(data: data),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading skeleton
// ─────────────────────────────────────────────────────────────────────────────

class _LoadingBody extends StatelessWidget {
  const _LoadingBody();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _shimmerHeader(),
        _shimmerChips(),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
            itemCount: 4,
            separatorBuilder: (_, _) => const SizedBox(height: 14),
            itemBuilder: (_, _) => _shimmerCard(),
          ),
        ),
      ],
    );
  }

  Widget _shimmerBlock({required double h, double w = double.infinity, double r = 8}) =>
      Container(
        height: h,
        width: w,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(r),
        ),
      );

  Widget _shimmerHeader() => Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
        child: _shimmerBlock(h: 28, w: 160),
      );

  Widget _shimmerChips() => Padding(
        padding: const EdgeInsets.only(left: 20, bottom: 16),
        child: SizedBox(
          height: 36,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: 5,
            separatorBuilder: (_, _) => const SizedBox(width: 8),
            itemBuilder: (_, _) => _shimmerBlock(h: 36, w: 72, r: 20),
          ),
        ),
      );

  Widget _shimmerCard() => Container(
        height: 100,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
        ),
      );
}

// ─────────────────────────────────────────────────────────────────────────────
// Error body
// ─────────────────────────────────────────────────────────────────────────────

class _ErrorBody extends StatelessWidget {
  final VoidCallback onRetry;
  const _ErrorBody({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded,
              color: AppColors.disabledIcon, size: 52),
          const SizedBox(height: 16),
          Text('Gagal memuat tugas',
              style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 16,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text('Pastikan koneksi internetmu aktif.',
              style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.35), fontSize: 13)),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: onRetry,
            style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
            child: const Text('Coba Lagi'),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main body (data loaded)
// ─────────────────────────────────────────────────────────────────────────────

class _Body extends ConsumerWidget {
  final TasksState data;
  const _Body({required this.data});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filtered = data.filteredTasks;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Header
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          child: Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Tugasku',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  Text(
                    '${data.allTasks.length} tugas',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.45),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              // Pending badge
              if (_pendingCount(data.allTasks) > 0)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: AppColors.primary.withValues(alpha: 0.4),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.pending_actions_rounded,
                          color: AppColors.primary, size: 14),
                      const SizedBox(width: 4),
                      Text(
                        '${_pendingCount(data.allTasks)} pending',
                        style: const TextStyle(
                          color: AppColors.primary,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // ── Status filter chips
        _StatusFilterChips(
          selected: data.selectedStatus,
          onSelect: (s) =>
              ref.read(taskViewModelProvider.notifier).filterByStatus(s),
        ),
        const SizedBox(height: 8),

        // ── Task list / empty
        Expanded(
          child: filtered.isEmpty
              ? _EmptyState(hasFilter: data.selectedStatus != null)
              : RefreshIndicator(
                  onRefresh: () =>
                      ref.read(taskViewModelProvider.notifier).refresh(),
                  color: AppColors.primary,
                  backgroundColor: AppColors.surface,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 100),
                    itemCount: filtered.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 14),
                    itemBuilder: (context, i) =>
                        _TaskCard(task: filtered[i], context: context),
                  ),
                ),
        ),
      ],
    );
  }

  int _pendingCount(List<TaskModel> tasks) =>
      tasks.where((t) => t.status == 'created').length;
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter chips row
// ─────────────────────────────────────────────────────────────────────────────

class _StatusFilterChips extends StatelessWidget {
  final String? selected;
  final void Function(String?) onSelect;

  const _StatusFilterChips({required this.selected, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 38,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: _kAllStatus.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final item = _kAllStatus[i];
          final isSelected = selected == item.value;
          return AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            child: GestureDetector(
              onTap: () => onSelect(item.value),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: isSelected
                      ? AppColors.primary
                      : AppColors.surface,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isSelected
                        ? AppColors.primary
                        : Colors.white.withValues(alpha: 0.08),
                  ),
                ),
                child: Text(
                  item.label,
                  style: TextStyle(
                    color: isSelected
                        ? Colors.white
                        : Colors.white.withValues(alpha: 0.55),
                    fontSize: 12,
                    fontWeight:
                        isSelected ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Task card
// ─────────────────────────────────────────────────────────────────────────────

class _TaskCard extends ConsumerStatefulWidget {
  final TaskModel task;
  final BuildContext context;

  const _TaskCard({required this.task, required this.context});

  @override
  ConsumerState<_TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends ConsumerState<_TaskCard> {
  bool _submitting = false;

  Future<void> _onSubmit() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Selesaikan Tugas?',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        content: Text(
          'Tandai "${widget.task.title}" sebagai selesai dan kirim ke orang tua untuk diverifikasi.',
          style: TextStyle(
              color: Colors.white.withValues(alpha: 0.65), fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Batal',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.5))),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
            child: const Text('Kirim'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    setState(() => _submitting = true);
    try {
      await ref.read(taskViewModelProvider.notifier).submitTask(widget.task.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Tugas berhasil dikirim! Menunggu persetujuan.'),
            backgroundColor: AppColors.surface,
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Gagal mengirim tugas. Coba lagi.'),
            backgroundColor: AppColors.errorSurface,
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final task = widget.task;
    final accent = _accentColor(task.status);
    final fmt = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.06),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.15),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── Left accent strip
              Container(
                width: 4,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [accent, accent.withValues(alpha: 0.4)],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
              ),

              // ── Content
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Title row + status badge
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Task icon
                          Container(
                            width: 38,
                            height: 38,
                            decoration: BoxDecoration(
                              color: accent.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(
                              _taskIcon(task),
                              color: accent,
                              size: 18,
                            ),
                          ),
                          const SizedBox(width: 10),
                          // Title + description
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  task.title,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700,
                                    height: 1.3,
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                if (task.description != null &&
                                    task.description!.isNotEmpty)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 2),
                                    child: Text(
                                      task.description!,
                                      style: TextStyle(
                                        color:
                                            Colors.white.withValues(alpha: 0.45),
                                        fontSize: 12,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          // Status badge
                          _StatusBadge(status: task.status),
                        ],
                      ),
                      const SizedBox(height: 12),

                      // ── Meta row: reward + due date
                      Row(
                        children: [
                          // Reward
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: AppColors.success.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  task.rewardCurrency == 'PTS'
                                      ? Icons.stars_rounded
                                      : Icons.payments_rounded,
                                  color: AppColors.success,
                                  size: 13,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  task.rewardCurrency == 'PTS'
                                      ? '${task.rewardAmount.toInt()} pts'
                                      : fmt.format(task.rewardAmount),
                                  style: const TextStyle(
                                    color: AppColors.success,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          // Recurring badge
                          if (task.isRecurring)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppColors.primary.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.repeat_rounded,
                                      color: AppColors.primary.withValues(alpha: 0.8),
                                      size: 12),
                                  const SizedBox(width: 3),
                                  Text(
                                    _recurrenceLabel(task.recurrenceType),
                                    style: TextStyle(
                                      color: AppColors.primary.withValues(alpha: 0.8),
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          const Spacer(),
                          // Due date
                          if (task.dueDate != null)
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.calendar_today_rounded,
                                  size: 11,
                                  color: _dueDateColor(task.dueDate!, task.status),
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  _formatDueDate(task.dueDate!),
                                  style: TextStyle(
                                    color: _dueDateColor(task.dueDate!, task.status),
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                        ],
                      ),

                      // ── Submit button (only for 'created' status)
                      if (task.status == 'created') ...[
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          height: 38,
                          child: FilledButton(
                            onPressed: _submitting ? null : _onSubmit,
                            style: FilledButton.styleFrom(
                              backgroundColor: AppColors.primary,
                              disabledBackgroundColor:
                                  AppColors.primary.withValues(alpha: 0.4),
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10)),
                              padding: EdgeInsets.zero,
                            ),
                            child: _submitting
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(Icons.check_circle_outline_rounded,
                                          size: 15),
                                      SizedBox(width: 6),
                                      Text('Tandai Selesai',
                                          style: TextStyle(
                                              fontSize: 13,
                                              fontWeight: FontWeight.w700)),
                                    ],
                                  ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Status badge chip
// ─────────────────────────────────────────────────────────────────────────────

class _StatusBadge extends StatelessWidget {
  final String status;
  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    final color = _accentColor(status);
    final label = _statusLabel(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty state
// ─────────────────────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final bool hasFilter;
  const _EmptyState({required this.hasFilter});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.06),
                ),
              ),
              child: Icon(
                hasFilter
                    ? Icons.filter_list_off_rounded
                    : Icons.task_alt_rounded,
                color: Colors.white.withValues(alpha: 0.25),
                size: 36,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              hasFilter ? 'Tidak ada tugas' : 'Belum ada tugas',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              hasFilter
                  ? 'Tidak ada tugas dengan status ini.'
                  : 'Orang tuamu belum membuat tugas untukmu.\nTunggu sebentar ya! 😊',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.4),
                fontSize: 14,
                height: 1.6,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

Color _accentColor(String status) {
  switch (status) {
    case 'created':
      return AppColors.primary;
    case 'submitted':
      return const Color(0xFFF59E0B); // amber
    case 'approved':
    case 'completed':
      return AppColors.success;
    case 'rejected':
      return AppColors.error;
    default:
      return AppColors.primary;
  }
}

String _statusLabel(String status) {
  switch (status) {
    case 'created':    return 'BARU';
    case 'submitted':  return 'DIKIRIM';
    case 'approved':   return 'DISETUJUI';
    case 'rejected':   return 'DITOLAK';
    case 'completed':  return 'SELESAI';
    default:           return status.toUpperCase();
  }
}

IconData _taskIcon(TaskModel task) {
  if (task.isRecurring) return Icons.repeat_rounded;
  if (task.rewardCurrency == 'PTS') return Icons.stars_rounded;
  return Icons.task_alt_rounded;
}

String _recurrenceLabel(String? type) {
  switch (type) {
    case 'daily':  return 'Harian';
    case 'weekly': return 'Mingguan';
    default:       return 'Rutin';
  }
}

Color _dueDateColor(DateTime due, String status) {
  if (status == 'approved' || status == 'completed') {
    return Colors.white.withValues(alpha: 0.35);
  }
  final now = DateTime.now();
  if (due.isBefore(now)) return AppColors.error;
  if (due.difference(now).inDays <= 2) return const Color(0xFFF59E0B);
  return Colors.white.withValues(alpha: 0.35);
}

String _formatDueDate(DateTime due) {
  final now = DateTime.now();
  final diff = due.difference(now).inDays;
  if (diff < 0) return 'Terlambat';
  if (diff == 0) return 'Hari ini';
  if (diff == 1) return 'Besok';
  return DateFormat('d MMM', 'id').format(due);
}
