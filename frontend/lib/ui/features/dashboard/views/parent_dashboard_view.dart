import 'package:flutter/material.dart';

import '../../../core/themes/app_colors.dart';

class ParentDashboardView extends StatelessWidget {
  const ParentDashboardView({super.key});

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
                  colors: [AppColors.primary, AppColors.primaryDark],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(Icons.shield_rounded, color: Colors.white, size: 36),
              ),
              const SizedBox(height: 24),
              const Text(
                'Parent Dashboard',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Family management coming soon',
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
