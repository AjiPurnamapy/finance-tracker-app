import 'package:flutter/material.dart';

import '../../../core/themes/app_colors.dart';

class ChildDashboardView extends StatelessWidget {
  const ChildDashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.success, AppColors.successDark],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(Icons.savings_rounded, color: Colors.white, size: 36),
              ),
              const SizedBox(height: 24),
              const Text(
                'Child Dashboard',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Your finances coming soon',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.45),
                  fontSize: 15,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
