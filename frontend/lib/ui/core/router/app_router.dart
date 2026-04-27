import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../data/models/user_model.dart';
import '../../../../data/repositories/auth_repository.dart';
import '../../features/auth/view_models/auth_view_model.dart';
import '../../features/auth/views/login_view.dart';
import '../../features/auth/views/register_view.dart';
import '../../features/auth/views/role_selection_view.dart';
import '../../features/dashboard/views/parent_dashboard_view.dart';
import '../../features/dashboard/views/child_dashboard_view.dart';
import '../../features/tasks/views/tasks_view.dart';
import '../../features/wallet/views/wallet_view.dart';
import '../../features/splash/views/splash_view.dart';
import 'parent_shell.dart' show ParentShell, ChildShell;


final _rootNavigatorKey = GlobalKey<NavigatorState>();

// Parent branch keys
final _parentDashboardKey = GlobalKey<NavigatorState>(debugLabel: 'parentDash');
final _parentTasksKey     = GlobalKey<NavigatorState>(debugLabel: 'parentTasks');
final _parentWalletKey    = GlobalKey<NavigatorState>(debugLabel: 'parentWallet');

// Child branch keys
final _childDashboardKey  = GlobalKey<NavigatorState>(debugLabel: 'childDash');
final _childTasksKey      = GlobalKey<NavigatorState>(debugLabel: 'childTasks');
final _childWalletKey     = GlobalKey<NavigatorState>(debugLabel: 'childWallet');

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
      final location  = state.matchedLocation;

      // Always let splash play
      if (location == '/splash') return null;

      // Still initializing — hold position
      if (authState.isLoading && !authState.hasValue && !authState.hasError) {
        return null;
      }

      final isAuth   = ref.read(authRepositoryProvider).hasToken;
      final isPublic = _publicRoutes.contains(location);

      // Not authenticated → go to login
      if (!isAuth && !isPublic) return '/login';

      // Already authenticated → skip login/register, but ALLOW role-selection
      // (needed right after register before user picks role)
      if (isAuth && (location == '/login' || location == '/register')) {
        final user = authState.value;
        return _homeForRole(user?.role);
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
                builder: (context, state) => const LoginView(),
      ),
      GoRoute(
        path: '/register',
                builder: (context, state) => const RegisterView(),
      ),
      GoRoute(
        path: '/role-selection',
                builder: (context, state) => const RoleSelectionView(),
      ),

      // ── Parent Shell ────────────────────────────────────────────────
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => ParentShell(navigationShell: shell),
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
        builder: (context, state, shell) => ChildShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _childDashboardKey,
            routes: [
              GoRoute(
                path: '/child/dashboard',
                  builder: (context, state) => const ChildDashboardView(),
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _childTasksKey,
            routes: [
              GoRoute(
                path: '/child/tasks',
                  builder: (context, state) => const TasksView(),
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _childWalletKey,
            routes: [
              GoRoute(
                path: '/child/wallet',
                  builder: (context, state) => const WalletView(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

String _homeForRole(String? role) {
  if (role == 'child') return '/child/dashboard';
  return '/parent/dashboard';
}
