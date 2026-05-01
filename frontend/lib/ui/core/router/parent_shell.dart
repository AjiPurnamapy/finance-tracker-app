import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../themes/app_colors.dart';

class ParentShell extends StatelessWidget {
  final StatefulNavigationShell navigationShell;
  const ParentShell({super.key, required this.navigationShell});

  void _onTap(int index) => navigationShell.goBranch(
        index,
        initialLocation: index == navigationShell.currentIndex,
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: navigationShell,
      bottomNavigationBar: _DarkNavBar(
        currentIndex: navigationShell.currentIndex,
        onTap: _onTap,
        items: const [
          _NavItem(icon: Icons.grid_view_rounded,    label: 'Dashboard'),
          _NavItem(icon: Icons.task_alt_rounded,     label: 'Tasks'),
          _NavItem(icon: Icons.account_balance_wallet_rounded, label: 'Wallet'),
        ],
      ),
    );
  }
}

class ChildShell extends StatelessWidget {
  final StatefulNavigationShell navigationShell;
  const ChildShell({super.key, required this.navigationShell});

  void _onTap(int index) => navigationShell.goBranch(
        index,
        initialLocation: index == navigationShell.currentIndex,
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: navigationShell,
      bottomNavigationBar: _DarkNavBar(
        currentIndex: navigationShell.currentIndex,
        onTap: _onTap,
        items: const [
          _NavItem(icon: Icons.home_rounded,                  label: 'Home'),
          _NavItem(icon: Icons.savings_rounded,               label: 'Savings'),
          _NavItem(icon: Icons.account_balance_wallet_rounded,label: 'Wallet'),
          _NavItem(icon: Icons.qr_code_scanner_rounded,       label: 'Scan'),
          _NavItem(icon: Icons.people_rounded,                label: 'Family'),
        ],
      ),
    );
  }
}

// ── Shared dark bottom nav bar ────────────────────────────────────────────────

class _NavItem {
  final IconData icon;
  final String label;
  const _NavItem({required this.icon, required this.label});
}

class _DarkNavBar extends StatelessWidget {
  final int currentIndex;
  final void Function(int) onTap;
  final List<_NavItem> items;

  const _DarkNavBar({
    required this.currentIndex,
    required this.onTap,
    required this.items,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.elevated,
        border: Border(
          top: BorderSide(
            color: Colors.white.withValues(alpha: 0.06),
            width: 1,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: List.generate(items.length, (i) {
              final selected = i == currentIndex;
              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => onTap(i),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: selected
                      ? BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                        )
                      : null,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        items[i].icon,
                        size: 22,
                        color: selected
                            ? AppColors.primary
                            : Colors.white.withValues(alpha: 0.35),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        items[i].label,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
                          color: selected
                              ? AppColors.primary
                              : Colors.white.withValues(alpha: 0.35),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}
