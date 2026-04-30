import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:shared_preferences/shared_preferences.dart';

// sharedPreferencesProvider is defined in token_manager.dart and
// re-exported from auth_repository.dart — import from either is fine.
import 'data/repositories/auth_repository.dart';
import 'ui/core/router/app_router.dart';
import 'ui/core/themes/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Use path URL strategy for web (removes the '#' from the URL).
  usePathUrlStrategy();

  // SharedPreferences is only used as a web fallback inside TokenManager.
  // On native, flutter_secure_storage handles everything.
  final prefs = await SharedPreferences.getInstance();

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ],
      child: const FinanceTrackerApp(),
    ),
  );
}

class FinanceTrackerApp extends ConsumerWidget {
  const FinanceTrackerApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final goRouter = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'Finance Tracker Family',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      routerConfig: goRouter,
    );
  }
}
