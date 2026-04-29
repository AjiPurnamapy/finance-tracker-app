import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class RoleSelectionView extends ConsumerStatefulWidget {
  const RoleSelectionView({super.key});

  @override
  ConsumerState<RoleSelectionView> createState() => _RoleSelectionViewState();
}

class _RoleSelectionViewState extends ConsumerState<RoleSelectionView> {
  String? _selectedRole;

  void _onContinue() {
    if (_selectedRole == null) return;
    context.push('/register?role=$_selectedRole');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D1117),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0),
                  child: IntrinsicHeight(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 48),
                        const Text(
                          'How will you use\nthe app?',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 34,
                            fontWeight: FontWeight.w800,
                            height: 1.15,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Choose the role that best describes you\nto customize your experience.',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.5),
                            fontSize: 15,
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 40),
                        _RoleCard(
                          isSelected: _selectedRole == 'parent',
                          onTap: () => setState(() => _selectedRole = 'parent'),
                          iconData: Icons.shield_rounded,
                          iconColor: const Color(0xFF137FEC),
                          title: 'I am a Parent',
                          subtitle: 'Family head & Administrator',
                          description:
                              'Manage family spending, set smart limits, and scan receipts with AI.',
                        ),
                        const SizedBox(height: 16),
                        _RoleCard(
                          isSelected: _selectedRole == 'child',
                          onTap: () => setState(() => _selectedRole = 'child'),
                          iconData: Icons.savings_rounded,
                          iconColor: const Color(0xFF10B981),
                          title: 'I am a Student',
                          subtitle: 'Child or dependent account',
                          description:
                              'Track your allowance, save for big goals, and learn healthy financial habits.',
                        ),
                        const Spacer(),
                        const SizedBox(height: 24),
                        // Continue button
                        SizedBox(
                          width: double.infinity,
                          height: 56,
                          child: AnimatedOpacity(
                            duration: const Duration(milliseconds: 300),
                            opacity: _selectedRole != null ? 1.0 : 0.4,
                            child: FilledButton(
                              onPressed:
                                  (_selectedRole != null) ? _onContinue : null,
                              style: FilledButton.styleFrom(
                                backgroundColor: const Color(0xFF137FEC),
                                disabledBackgroundColor:
                                    const Color(0xFF137FEC).withValues(alpha: 0.4),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                              ),
                              child: const Text(
                                'Continue',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 32),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  final bool isSelected;
  final VoidCallback onTap;
  final IconData iconData;
  final Color iconColor;
  final String title;
  final String subtitle;
  final String description;

  const _RoleCard({
    required this.isSelected,
    required this.onTap,
    required this.iconData,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeInOut,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: isSelected
              ? iconColor.withValues(alpha: 0.08)
              : const Color(0xFF1A1F2E),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? iconColor : const Color(0xFF2A2F3E),
            width: isSelected ? 1.5 : 1,
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
                    color: iconColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(iconData, color: iconColor, size: 24),
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
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.45),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isSelected ? iconColor : Colors.transparent,
                    border: Border.all(
                      color: isSelected
                          ? iconColor
                          : Colors.white.withValues(alpha: 0.25),
                      width: 1.5,
                    ),
                  ),
                  child: isSelected
                      ? const Icon(Icons.check, color: Colors.white, size: 14)
                      : null,
                ),
              ],
            ),
            const SizedBox(height: 14),
            Text(
              description,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.55),
                fontSize: 14,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
