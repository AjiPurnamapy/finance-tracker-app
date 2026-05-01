import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../data/models/savings_goal_model.dart';
import '../../savings/view_models/savings_view_model.dart';
import '../../../core/themes/app_colors.dart';

class ChildSavingsView extends ConsumerWidget {
  const ChildSavingsView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(savingsViewModelProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                children: [
                  const Text(
                    'Tabunganku',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const Spacer(),
                  GestureDetector(
                    onTap: () => _showCreateGoalSheet(context, ref),
                    child: Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.add_rounded,
                          color: Colors.white, size: 20),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: state.when(
                loading: () => const Center(
                  child: CircularProgressIndicator(
                    color: AppColors.primary,
                  ),
                ),
                error: (e, _) => _ErrorState(
                  error: e,
                  onRetry: () =>
                      ref.read(savingsViewModelProvider.notifier).refresh(),
                ),
                data: (goals) => goals.isEmpty
                    ? _EmptyState(
                        onCreate: () =>
                            _showCreateGoalSheet(context, ref),
                      )
                    : RefreshIndicator(
                        onRefresh: () =>
                            ref.read(savingsViewModelProvider.notifier).refresh(),
                        color: AppColors.primary,
                        backgroundColor: AppColors.surface,
                        child: ListView.separated(
                          padding: const EdgeInsets.fromLTRB(20, 0, 20, 100),
                          itemCount: goals.length,
                          separatorBuilder: (_, idx) =>
                              const SizedBox(height: 16),
                          itemBuilder: (context, i) => _GoalCard(
                            goal: goals[i],
                            onContribute: () =>
                                _showContributeSheet(context, ref, goals[i]),
                            onDelete: () => _confirmDelete(
                                context, ref, goals[i]),
                          ),
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showCreateGoalSheet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => const _CreateGoalSheet(),
    );
  }

  void _showContributeSheet(
      BuildContext context, WidgetRef ref, SavingsGoalModel goal) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _ContributeSheet(goal: goal),
    );
  }

  void _confirmDelete(
      BuildContext context, WidgetRef ref, SavingsGoalModel goal) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Hapus Goal',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        content: Text(
          'Hapus "${goal.name}"?',
          style: TextStyle(color: Colors.white.withValues(alpha: 0.7)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Batal',
                style:
                    TextStyle(color: Colors.white.withValues(alpha: 0.55))),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ref
                  .read(savingsViewModelProvider.notifier)
                  .deleteGoal(goal.id);
            },
            child: const Text('Hapus',
                style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }
}

// ── Empty State ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final VoidCallback onCreate;
  const _EmptyState({required this.onCreate});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: AppColors.surface,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.savings_rounded,
                size: 44,
                color: AppColors.primary.withValues(alpha: 0.7),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Mulai goal tabungan pertamamu',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'Tentukan target untuk sesuatu yang kamu inginkan, misalnya sepeda atau gadget baru.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.45),
                fontSize: 14,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: onCreate,
                icon: const Icon(Icons.add_rounded),
                label: const Text('Buat Goal Pertama'),
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  textStyle: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Error State ───────────────────────────────────────────────────────────────

class _ErrorState extends StatelessWidget {
  final Object error;
  final VoidCallback onRetry;
  const _ErrorState({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final errStr = error.toString();
    if (errStr.contains('NOT_IN_FAMILY')) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: const BoxDecoration(
                  color: AppColors.surface,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.family_restroom_rounded,
                    color: AppColors.primary, size: 40),
              ),
              const SizedBox(height: 24),
              const Text(
                'Belum Bergabung',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 12),
              const Text(
                'Minta orang tuamu untuk mengundangmu ke dalam keluarga agar bisa menggunakan fitur ini.',
                style: TextStyle(
                    color: Colors.white54, fontSize: 14, height: 1.5),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off_rounded,
              color: AppColors.disabledIcon, size: 52),
          const SizedBox(height: 12),
          Text(
            'Gagal memuat tabungan',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.6),
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: onRetry,
            style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary),
            child: const Text('Coba Lagi'),
          ),
        ],
      ),
    );
  }
}

// ── Goal Card ─────────────────────────────────────────────────────────────────

class _GoalCard extends StatelessWidget {
  final SavingsGoalModel goal;
  final VoidCallback onContribute;
  final VoidCallback onDelete;

  const _GoalCard({
    required this.goal,
    required this.onContribute,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final fmt = NumberFormat.currency(
      locale: 'id_ID',
      symbol: 'Rp ',
      decimalDigits: 0,
    );
    final pct = (goal.progressPercent * 100).toStringAsFixed(0);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: goal.isCompleted
            ? const LinearGradient(
                colors: [AppColors.success, AppColors.successDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : const LinearGradient(
                colors: [AppColors.primary, AppColors.primaryDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: (goal.isCompleted
                    ? AppColors.success
                    : AppColors.primary)
                .withValues(alpha: 0.3),
            blurRadius: 20,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  goal.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (goal.isCompleted)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    '✓ SELESAI',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                )
              else
                PopupMenuButton<String>(
                  icon: Icon(Icons.more_vert_rounded,
                      color: Colors.white.withValues(alpha: 0.6), size: 20),
                  color: AppColors.surface,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  onSelected: (v) {
                    if (v == 'delete') onDelete();
                  },
                  itemBuilder: (_) => [
                    const PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete_outline_rounded,
                              color: AppColors.error, size: 18),
                          SizedBox(width: 8),
                          Text('Hapus',
                              style: TextStyle(color: AppColors.error)),
                        ],
                      ),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '${fmt.format(goal.currentAmount)} dari ${fmt.format(goal.targetAmount)}',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.75),
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 14),
          // Progress bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: goal.progressPercent,
              backgroundColor: Colors.white.withValues(alpha: 0.2),
              valueColor:
                  const AlwaysStoppedAnimation<Color>(Colors.white),
              minHeight: 6,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '$pct% tercapai',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                'Sisa: ${fmt.format(goal.remaining)}',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 12,
                ),
              ),
            ],
          ),
          if (!goal.isCompleted) ...[
            const SizedBox(height: 14),
            GestureDetector(
              onTap: onContribute,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Center(
                  child: Text(
                    '+ Tambah Tabungan',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ── Create Goal Sheet ─────────────────────────────────────────────────────────

class _CreateGoalSheet extends ConsumerStatefulWidget {
  const _CreateGoalSheet();

  @override
  ConsumerState<_CreateGoalSheet> createState() => _CreateGoalSheetState();
}

class _CreateGoalSheetState extends ConsumerState<_CreateGoalSheet> {
  final _nameController = TextEditingController();
  final _amountController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    final amount =
        double.tryParse(_amountController.text.replaceAll('.', '').replaceAll(',', ''));
    if (name.isEmpty || amount == null || amount <= 0) return;

    setState(() => _isLoading = true);
    try {
      await ref
          .read(savingsViewModelProvider.notifier)
          .createGoal(name: name, targetAmount: amount);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Gagal membuat goal. Coba lagi.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
          24, 16, 24, MediaQuery.of(context).viewInsets.bottom + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            'Buat Goal Baru',
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 20),
          _SheetField(
            controller: _nameController,
            label: 'Nama Goal',
            hint: 'Contoh: Sepeda baru',
          ),
          const SizedBox(height: 12),
          _SheetField(
            controller: _amountController,
            label: 'Target (Rp)',
            hint: '500000',
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _isLoading ? null : _submit,
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Simpan',
                      style: TextStyle(
                          fontSize: 15, fontWeight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Contribute Sheet ──────────────────────────────────────────────────────────

class _ContributeSheet extends ConsumerStatefulWidget {
  final SavingsGoalModel goal;
  const _ContributeSheet({required this.goal});

  @override
  ConsumerState<_ContributeSheet> createState() => _ContributeSheetState();
}

class _ContributeSheetState extends ConsumerState<_ContributeSheet> {
  final _amountController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final amount = double.tryParse(
        _amountController.text.replaceAll('.', '').replaceAll(',', ''));
    if (amount == null || amount <= 0) return;

    setState(() => _isLoading = true);
    try {
      await ref
          .read(savingsViewModelProvider.notifier)
          .contribute(goalId: widget.goal.id, amount: amount);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Gagal menambah tabungan. Coba lagi.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
          24, 16, 24, MediaQuery.of(context).viewInsets.bottom + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Tambah ke "${widget.goal.name}"',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 20),
          _SheetField(
            controller: _amountController,
            label: 'Jumlah (Rp)',
            hint: '50000',
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _isLoading ? null : _submit,
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Simpan',
                      style: TextStyle(
                          fontSize: 15, fontWeight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Shared Sheet Field ────────────────────────────────────────────────────────

class _SheetField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final String hint;
  final TextInputType keyboardType;

  const _SheetField({
    required this.controller,
    required this.label,
    required this.hint,
    this.keyboardType = TextInputType.text,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.65),
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          keyboardType: keyboardType,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle:
                TextStyle(color: Colors.white.withValues(alpha: 0.25)),
            filled: true,
            fillColor: AppColors.background,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide:
                  BorderSide(color: Colors.white.withValues(alpha: 0.1)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide:
                  BorderSide(color: Colors.white.withValues(alpha: 0.1)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppColors.primary),
            ),
          ),
        ),
      ],
    );
  }
}
