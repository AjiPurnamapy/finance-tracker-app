import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/dashboard/views/dashboard_view.dart';
import '../../features/tasks/views/tasks_view.dart';
import '../../features/wallet/views/wallet_view.dart';
import 'scaffold_with_nav_bar.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _dashboardNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'dashboard');
final _tasksNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'tasks');
final _walletNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'wallet');

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/dashboard',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return ScaffoldWithNavBar(navigationShell: navigationShell);
        },
        branches: [
          StatefulShellBranch(
            navigatorKey: _dashboardNavigatorKey,
            routes: [
              GoRoute(
                path: '/dashboard',
                builder: (context, state) => const DashboardView(),
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _tasksNavigatorKey,
            routes: [
              GoRoute(
                path: '/tasks',
                builder: (context, state) => const TasksView(),
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _walletNavigatorKey,
            routes: [
              GoRoute(
                path: '/wallet',
                builder: (context, state) => const WalletView(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});
