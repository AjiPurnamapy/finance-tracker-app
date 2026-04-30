import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../data/models/family_model.dart';
import '../../family/view_models/family_view_model.dart';

class ChildFamilyView extends ConsumerWidget {
  const ChildFamilyView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(familyViewModelProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0D1117),
      body: SafeArea(
        child: state.when(
          loading: () => const Center(
            child: CircularProgressIndicator(color: Color(0xFF137FEC)),
          ),
          error: (e, _) {
            final errStr = e.toString();
            if (errStr.contains('NOT_IN_FAMILY')) {
              return const _NotConnectedState();
            }
            return _ErrorState(
              onRetry: () =>
                  ref.read(familyViewModelProvider.notifier).refresh(),
            );
          },
          data: (family) => family == null
              ? const _NotConnectedState()
              : _ConnectedState(family: family),
        ),
      ),
    );
  }
}

// ── State 1: Not Connected ────────────────────────────────────────────────────

/// Uses ConsumerStatefulWidget so it can access Riverpod providers directly
/// without storing a stale WidgetRef from a parent widget (H-4 fix).
class _NotConnectedState extends ConsumerStatefulWidget {
  const _NotConnectedState();

  @override
  ConsumerState<_NotConnectedState> createState() => _NotConnectedStateState();
}

class _NotConnectedStateState extends ConsumerState<_NotConnectedState> {
  final _codeController = TextEditingController();
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _join() async {
    final code = _codeController.text.trim().toUpperCase();
    // M-5: Validate alphanumeric, exactly 6 chars
    if (code.length != 6 || !RegExp(r'^[A-Z0-9]{6}$').hasMatch(code)) {
      setState(() => _error = 'Kode harus 6 karakter (huruf/angka)');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await ref
          .read(familyViewModelProvider.notifier)
          .joinFamily(code);
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Kode tidak valid atau sudah kadaluarsa');
      }
    } finally {
      // H-5: Always reset loading regardless of success or failure
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const SizedBox(height: 16),
          // Header
          Row(
            children: [
              const Text(
                'Family',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const Spacer(),
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: const Color(0xFF1A1F2E),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  Icons.help_outline_rounded,
                  color: Colors.white.withValues(alpha: 0.4),
                  size: 18,
                ),
              ),
            ],
          ),
          const SizedBox(height: 48),
          // Illustration
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              color: const Color(0xFF1A1F2E),
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFF137FEC).withValues(alpha: 0.3),
                width: 1.5,
              ),
            ),
            child: const Icon(
              Icons.link_rounded,
              color: Color(0xFF137FEC),
              size: 52,
            ),
          ),
          const SizedBox(height: 28),
          const Text(
            'Hubungkan ke Orang Tua',
            style: TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 10),
          Text(
            'Masukkan kode undangan dari orang tuamu untuk mulai mengelola keuangan bersama.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.45),
              fontSize: 14,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 36),
          // Code input
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'MASUKKAN KODE UNDANGAN',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.5),
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.8,
              ),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _codeController,
            keyboardType: TextInputType.number,
            maxLength: 6,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 28,
              fontWeight: FontWeight.w800,
              letterSpacing: 8,
            ),
            decoration: InputDecoration(
              counterText: '',
              hintText: '_ _ _ _ _ _',
              hintStyle: TextStyle(
                color: Colors.white.withValues(alpha: 0.2),
                fontSize: 28,
                letterSpacing: 8,
              ),
              filled: true,
              fillColor: const Color(0xFF1A1F2E),
              errorText: _error,
              errorStyle: const TextStyle(color: Color(0xFFEF4444)),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide(
                  color: Colors.white.withValues(alpha: 0.1),
                ),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide(
                  color: Colors.white.withValues(alpha: 0.1),
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: const BorderSide(color: Color(0xFF137FEC)),
              ),
              errorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: const BorderSide(color: Color(0xFFEF4444)),
              ),
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _isLoading ? null : _join,
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF137FEC),
                disabledBackgroundColor:
                    const Color(0xFF137FEC).withValues(alpha: 0.4),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text(
                      'Hubungkan Akun',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
            ),
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }
}

// ── State 2: Connected ────────────────────────────────────────────────────────

/// Pure StatelessWidget — all read-only rendering, no Riverpod interactions.
class _ConnectedState extends ConsumerWidget {
  final FamilyModel family;
  const _ConnectedState({required this.family});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Find parent member (admin role)
    final parent = family.members
        .where((m) => m.role == 'admin')
        .firstOrNull;

    return RefreshIndicator(
      onRefresh: () =>
          ref.read(familyViewModelProvider.notifier).refresh(),
      color: const Color(0xFF137FEC),
      backgroundColor: const Color(0xFF1A1F2E),
      child: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 16),
          // Header
          const Text(
            'Family',
            style: TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 20),
          // Connected card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF1A1F2E),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: const Color(0xFF10B981).withValues(alpha: 0.3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF137FEC), Color(0xFF0A5AB5)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          parent?.fullName.isNotEmpty == true
                              ? parent!.fullName[0].toUpperCase()
                              : 'P',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'TERHUBUNG KE',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.45),
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.8,
                            ),
                          ),
                          Text(
                            parent?.fullName ?? 'Orang Tua',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircleAvatar(
                            radius: 4,
                            backgroundColor: Color(0xFF10B981),
                          ),
                          SizedBox(width: 6),
                          Text(
                            'AKTIF',
                            style: TextStyle(
                              color: Color(0xFF10B981),
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Divider(color: Colors.white.withValues(alpha: 0.08)),
                const SizedBox(height: 16),
                Row(
                  children: [
                    _InfoChip(
                      icon: Icons.people_rounded,
                      label: '${family.memberCount} Anggota',
                    ),
                    const SizedBox(width: 10),
                    _InfoChip(
                      icon: Icons.family_restroom_rounded,
                      label: family.name,
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          // What parent can see section
          const Text(
            'Apa yang bisa dilihat orang tua?',
            style: TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          _FeatureRow(
            icon: Icons.visibility_rounded,
            iconColor: const Color(0xFF137FEC),
            title: 'Ringkasan Pengeluaran',
            subtitle:
                'Orang tua dapat melihat ringkasan pengeluaranmu setiap bulan.',
          ),
          _FeatureRow(
            icon: Icons.account_balance_wallet_rounded,
            iconColor: const Color(0xFF10B981),
            title: 'Transfer Uang Saku',
            subtitle:
                'Orang tua bisa kirim uang saku langsung ke walletmu.',
          ),
          _FeatureRow(
            icon: Icons.task_alt_rounded,
            iconColor: const Color(0xFFF59E0B),
            title: 'Tugas & Reward',
            subtitle:
                'Selesaikan tugas dari orang tua dan dapatkan reward poin.',
          ),
          const SizedBox(height: 100),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _InfoChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1117),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: Colors.white.withValues(alpha: 0.45)),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.65),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;

  const _FeatureRow({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: iconColor, size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.45),
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Error State ───────────────────────────────────────────────────────────────

class _ErrorState extends StatelessWidget {
  final VoidCallback onRetry;
  const _ErrorState({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off_rounded,
              color: Color(0xFF4A5060), size: 52),
          const SizedBox(height: 12),
          Text(
            'Gagal memuat data family',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.6),
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: onRetry,
            style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF137FEC)),
            child: const Text('Coba Lagi'),
          ),
        ],
      ),
    );
  }
}
