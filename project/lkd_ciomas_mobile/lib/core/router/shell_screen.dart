import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../auth/auth_repository.dart';
import '../theme/app_colors.dart';
import '../../models/user.dart';

class ShellScreen extends ConsumerWidget {
  final Widget child;

  const ShellScreen({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final user = auth.user;

    if (user == null) return child;

    final tabs = _getTabs(user);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: child,
      bottomNavigationBar: _BottomNav(tabs: tabs),
    );
  }

  List<ShellTab> _getTabs(User user) {
    if (user.isAdmin || user.isManajer) {
      return const [
        ShellTab('Beranda', Icons.dashboard_outlined,
            Icons.dashboard_rounded, '/dashboard'),
        ShellTab('Nasabah', Icons.people_outline,
            Icons.people_rounded, '/nasabah'),
        ShellTab('Pinjaman', Icons.account_balance_outlined,
            Icons.account_balance_rounded, '/pinjaman'),
        ShellTab('ACC', Icons.verified_outlined,
            Icons.verified_rounded, '/pembayaran/acc'),
        ShellTab('Profil', Icons.person_outline,
            Icons.person_rounded, '/profile'),
      ];
    }
    if (user.isKader) {
      return const [
        ShellTab('Beranda', Icons.dashboard_outlined,
            Icons.dashboard_rounded, '/dashboard'),
        ShellTab('Nasabah', Icons.people_outline,
            Icons.people_rounded, '/nasabah'),
        ShellTab('Pinjaman', Icons.account_balance_outlined,
            Icons.account_balance_rounded, '/pinjaman'),
        ShellTab('Tagihan', Icons.receipt_long_outlined,
            Icons.receipt_long_rounded, '/penagihan'),
        ShellTab('Profil', Icons.person_outline,
            Icons.person_rounded, '/profile'),
      ];
    }
    if (user.isVerifikator) {
      return const [
        ShellTab('Verifikasi', Icons.fact_check_outlined,
            Icons.fact_check_rounded, '/verifikasi'),
        ShellTab('Cari', Icons.search_outlined,
            Icons.search_rounded, '/nasabah'),
        ShellTab('Profil', Icons.person_outline,
            Icons.person_rounded, '/profile'),
      ];
    }
    if (user.isPenagih) {
      return const [
        ShellTab('Tagihan', Icons.receipt_long_outlined,
            Icons.receipt_long_rounded, '/penagihan'),
        ShellTab('Bonus', Icons.emoji_events_outlined,
            Icons.emoji_events_rounded, '/bonus-saya'),
        ShellTab('Profil', Icons.person_outline,
            Icons.person_rounded, '/profile'),
      ];
    }
    // Nasabah default
    return const [
      ShellTab('Beranda', Icons.home_outlined,
          Icons.home_rounded, '/dashboard'),
      ShellTab('Pinjaman', Icons.account_balance_outlined,
          Icons.account_balance_rounded, '/pinjaman'),
      ShellTab('Tabungan', Icons.savings_outlined,
          Icons.savings_rounded, '/tabungan'),
      ShellTab('UMKM', Icons.storefront_outlined,
          Icons.storefront_rounded, '/umkm/katalog'),
      ShellTab('Profil', Icons.person_outline,
          Icons.person_rounded, '/profile'),
    ];
  }
}

class _BottomNav extends StatelessWidget {
  final List<ShellTab> tabs;
  const _BottomNav({required this.tabs});

  int _currentIndex(String location) {
    int best = 0;
    int bestLen = -1;
    for (int i = 0; i < tabs.length; i++) {
      final p = tabs[i].path;
      if (location == p || location.startsWith('$p/')) {
        if (p.length > bestLen) {
          best = i;
          bestLen = p.length;
        }
      }
    }
    return best;
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final currentIndex = _currentIndex(location);

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 18,
            offset: const Offset(0, -4),
          ),
        ],
        border: const Border(
          top: BorderSide(color: AppColors.divider, width: 0.6),
        ),
      ),
      child: SafeArea(
        top: false,
        child: NavigationBar(
          selectedIndex: currentIndex,
          onDestinationSelected: (i) => context.go(tabs[i].path),
          destinations: tabs
              .map((t) => NavigationDestination(
                    icon: Icon(t.icon),
                    selectedIcon: Icon(t.selectedIcon),
                    label: t.label,
                  ))
              .toList(),
        ),
      ),
    );
  }
}

class ShellTab {
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final String path;

  const ShellTab(this.label, this.icon, this.selectedIcon, this.path);
}
