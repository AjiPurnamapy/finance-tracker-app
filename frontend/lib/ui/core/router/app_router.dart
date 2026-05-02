import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../data/models/user_model.dart';
import '../../features/auth/view_models/auth_view_model.dart';
import '../../features/auth/views/login_view.dart';
import '../../features/auth/views/register_view.dart';
import '../../features/auth/views/role_selection_view.dart';
import '../../features/dashboard/views/parent_dashboard_view.dart';
import '../../features/dashboard/views/child_home_view.dart';
import '../../features/savings/views/child_savings_view.dart';
import '../../features/wallet/views/child_wallet_view.dart';
import '../../features/scan/views/scan_view.dart';
import '../../features/family/views/child_family_view.dart';
import '../../features/tasks/views/tasks_view.dart';
import '../../features/wallet/views/wallet_view.dart';
import '../../features/splash/views/splash_view.dart';
import 'parent_shell.dart' show ParentShell, ChildShell;

final _rootNavigatorKey = GlobalKey<NavigatorState>();

// Parent branch keys
final _parentDashboardKey = GlobalKey<NavigatorState>(debugLabel: 'parentDash');
final _parentTasksKey = GlobalKey<NavigatorState>(debugLabel: 'parentTasks');
final _parentWalletKey = GlobalKey<NavigatorState>(debugLabel: 'parentWallet');

// Child branch keys
final _childHomeKey    = GlobalKey<NavigatorState>(debugLabel: 'childHome');
final _childTasksKey   = GlobalKey<NavigatorState>(debugLabel: 'childTasks');
final _childSavingsKey = GlobalKey<NavigatorState>(debugLabel: 'childSavings');
final _childWalletKey  = GlobalKey<NavigatorState>(debugLabel: 'childWallet');
final _childScanKey    = GlobalKey<NavigatorState>(debugLabel: 'childScan');
final _childFamilyKey  = GlobalKey<NavigatorState>(debugLabel: 'childFamily');

const _publicRoutes = {'/splash', '/login', '/register', '/role-selection'};

final appRouterProvider = Provider<GoRouter>((ref) {
  final notifier = ValueNotifier<AsyncValue<User?>>(const AsyncValue.loading());
  ref.listen(authViewModelProvider, (_, next) => notifier.value = next);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/splash',
    refreshListenable: notifier,
    redirect: (context, state) {
      final authState = notifier.value;
      final location = state.matchedLocation;

      // Always let splash play
      if (location == '/splash') return null;

      // Still initializing — hold position
      if (authState.isLoading && !authState.hasValue && !authState.hasError) {
        return null;
      }

      // H-3 FIX: Use authViewModel state (server-verified), not just local hasToken
      final user = authState.value;
      final isAuthenticated = user != null;
      final isPublic = _publicRoutes.contains(location);

      // Not authenticated → go to login
      if (!isAuthenticated && !isPublic) return '/login';

      // Already authenticated → skip login/register/role-selection
      if (isAuthenticated &&
          (location == '/login' ||
           location == '/register' ||
           location == '/role-selection')) {
        return _homeForRole(user.role);
      }

      return null;
    },
    routes: [
      // ── Public ─────────────────────────────────────────────────────
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashView(),
      ),
      GoRoute(
        path: '/login',
        pageBuilder: (context, state) => _fadeRoute(
          key: state.pageKey,
          child: const LoginView(),
        ),
      ),
      GoRoute(
        path: '/register',
        pageBuilder: (context, state) => _fadeRoute(
          key: state.pageKey,
          child: RegisterView(
            preselectedRole: state.uri.queryParameters['role'],
          ),
        ),
      ),
      GoRoute(
        path: '/role-selection',
        pageBuilder: (context, state) => _fadeRoute(
          key: state.pageKey,
          child: const RoleSelectionView(),
        ),
      ),

      // ── Parent Shell ────────────────────────────────────────────────
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) =>
            ParentShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _parentDashboardKey,
            routes: [
              GoRoute(
                path: '/parent/dashboard',
                builder: (context, state) => const ParentDashboardView(),
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _parentTasksKey,
            routes: [
              GoRoute(
                path: '/parent/tasks',
                builder: (context, state) => const TasksView(),
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _parentWalletKey,
            routes: [
              GoRoute(
                path: '/parent/wallet',
                builder: (context, state) => const WalletView(),
              ),
            ],
          ),
        ],
      ),

      // ── Child Shell ─────────────────────────────────────────────────
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) =>
            ChildShell(navigationShell: shell),
        branches: [
          // index 0 — Home
          StatefulShellBranch(
            navigatorKey: _childHomeKey,
            routes: [
              GoRoute(
                path: '/child/home',
                builder: (context, state) => const ChildHomeView(),
              ),
            ],
          ),
          // index 1 — Tasks
          StatefulShellBranch(
            navigatorKey: _childTasksKey,
            routes: [
              GoRoute(
                path: '/child/tasks',
                builder: (context, state) => const TasksView(),
              ),
            ],
          ),
          // index 2 — Savings
          StatefulShellBranch(
            navigatorKey: _childSavingsKey,
            routes: [
              GoRoute(
                path: '/child/savings',
                builder: (context, state) => const ChildSavingsView(),
              ),
            ],
          ),
          // index 3 — Wallet
          StatefulShellBranch(
            navigatorKey: _childWalletKey,
            routes: [
              GoRoute(
                path: '/child/wallet',
                builder: (context, state) => const ChildWalletView(),
              ),
            ],
          ),
          // index 4 — Scan
          StatefulShellBranch(
            navigatorKey: _childScanKey,
            routes: [
              GoRoute(
                path: '/child/scan',
                builder: (context, state) => const ScanView(),
              ),
            ],
          ),
          // index 5 — Family
          StatefulShellBranch(
            navigatorKey: _childFamilyKey,
            routes: [
              GoRoute(
                path: '/child/family',
                builder: (context, state) => const ChildFamilyView(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

String _homeForRole(String? role) {
  if (role?.trim().toLowerCase() == 'child') return '/child/home';
  return '/parent/dashboard';
}

/// Smooth fade transition for auth routes.
/// Replaces GoRouter's default slide-up so navigating between
/// login → role-selection → register feels seamless.
CustomTransitionPage<void> _fadeRoute({
  required LocalKey key,
  required Widget child,
}) {
  return CustomTransitionPage<void>(
    key: key,
    child: child,
    transitionDuration: const Duration(milliseconds: 280),
    reverseTransitionDuration: const Duration(milliseconds: 200),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      return FadeTransition(
        opacity: CurveTween(curve: Curves.easeInOut).animate(animation),
        child: child,
      );
    },
  );
}
