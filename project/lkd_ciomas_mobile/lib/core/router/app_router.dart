import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../auth/auth_repository.dart';
import '../../features/auth/splash_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';

import '../../features/dashboard/dashboard_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/profile/change_password_screen.dart';
import '../../features/profile/bonus_saya_screen.dart';
import '../../features/nasabah/nasabah_list_screen.dart';
import '../../features/nasabah/nasabah_detail_screen.dart';
import '../../features/nasabah/nasabah_form_screen.dart';
import '../../features/pinjaman/pinjaman_list_screen.dart';
import '../../features/pinjaman/pinjaman_detail_screen.dart';
import '../../features/pinjaman/pinjaman_form_screen.dart';
import '../../features/pinjaman/jadwal_angsuran_screen.dart';
import '../../features/pembayaran/pembayaran_list_screen.dart';
import '../../features/pembayaran/pembayaran_form_screen.dart';
import '../../features/pembayaran/acc_pembayaran_screen.dart';
import '../../features/tabungan/tabungan_screen.dart';
import '../../features/tabungan/tabungan_setor_screen.dart';
import '../../features/verifikasi/verifikasi_list_screen.dart';
import '../../features/verifikasi/verifikasi_form_screen.dart';
import '../../features/penagihan/penagihan_list_screen.dart';
import '../../features/penagihan/penagihan_bayar_screen.dart';
import '../../features/umkm/umkm_katalog_screen.dart';
import '../../features/umkm/umkm_produk_detail_screen.dart';
import '../../features/umkm/umkm_pesanan_saya_screen.dart';
import '../../features/umkm/umkm_toko_saya_screen.dart';
import '../../features/umkm/umkm_daftar_penjual_screen.dart';
import '../../features/umkm/umkm_pesanan_masuk_screen.dart';
import 'shell_screen.dart';

/// ChangeNotifier that fires whenever the auth state changes so GoRouter
/// can re-run its `redirect` logic and auto-navigate (e.g. after login,
/// logout, or session check completes).
class _AuthRouterListenable extends ChangeNotifier {
  _AuthRouterListenable(this._ref) {
    _ref.listen<AuthState>(authProvider, (prev, next) {
      if (prev?.status != next.status) {
        notifyListeners();
      }
    });
  }
  // ignore: unused_field
  final Ref _ref;
}

final _authRouterListenableProvider = Provider<_AuthRouterListenable>((ref) {
  return _AuthRouterListenable(ref);
});

final routerProvider = Provider<GoRouter>((ref) {
  final listenable = ref.watch(_authRouterListenableProvider);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: listenable,
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      final loc = state.matchedLocation;
      final isAuthRoute = loc == '/login' || loc == '/register';

      // While we don't know yet, keep user on splash
      if (auth.status == AuthStatus.unknown) {
        return loc == '/splash' ? null : '/splash';
      }

      final isLoggedIn = auth.status == AuthStatus.authenticated;

      // Logged out -> only allow login/register
      if (!isLoggedIn) {
        if (loc == '/splash') return '/login';
        if (!isAuthRoute) return '/login';
        return null;
      }

      // Logged in -> push away from splash/login/register
      if (loc == '/splash' || isAuthRoute) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),

      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),

      ShellRoute(
        builder: (_, __, child) => ShellScreen(child: child),
        routes: [
          // Dashboard
          GoRoute(
            path: '/dashboard',
            builder: (_, __) => const DashboardScreen(),
          ),

          // Profile
          GoRoute(
            path: '/profile',
            builder: (_, __) => const ProfileScreen(),
          ),
          GoRoute(
            path: '/change-password',
            builder: (_, __) => const ChangePasswordScreen(),
          ),
          GoRoute(
            path: '/bonus-saya',
            builder: (_, __) => const BonusSayaScreen(),
          ),

          // Nasabah
          GoRoute(
            path: '/nasabah',
            builder: (_, __) => const NasabahListScreen(),
          ),
          GoRoute(
            path: '/nasabah/tambah',
            builder: (_, __) => const NasabahFormScreen(),
          ),
          GoRoute(
            path: '/nasabah/:id',
            builder: (_, state) => NasabahDetailScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/nasabah/:id/edit',
            builder: (_, state) => NasabahFormScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),

          // Pinjaman
          GoRoute(
            path: '/pinjaman',
            builder: (_, __) => const PinjamanListScreen(),
          ),
          GoRoute(
            path: '/pinjaman/tambah',
            builder: (_, __) => const PinjamanFormScreen(),
          ),
          GoRoute(
            path: '/pinjaman/:id',
            builder: (_, state) => PinjamanDetailScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/pinjaman/:id/jadwal',
            builder: (_, state) => JadwalAngsuranScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),

          // Pembayaran
          GoRoute(
            path: '/pembayaran',
            builder: (_, __) => const PembayaranListScreen(),
          ),
          GoRoute(
            path: '/pembayaran/tambah',
            builder: (_, __) => const PembayaranFormScreen(),
          ),
          GoRoute(
            path: '/pembayaran/acc',
            builder: (_, __) => const AccPembayaranScreen(),
          ),

          // Tabungan
          GoRoute(
            path: '/tabungan',
            builder: (_, __) => const TabunganScreen(),
          ),
          GoRoute(
            path: '/tabungan/setor',
            builder: (_, __) => const TabunganSetorScreen(),
          ),
          GoRoute(
            path: '/tabungan/tarik',
            builder: (_, __) => const TabunganSetorScreen(isTarik: true),
          ),

          // Verifikasi
          GoRoute(
            path: '/verifikasi',
            builder: (_, __) => const VerifikasiListScreen(),
          ),
          GoRoute(
            path: '/verifikasi/:id',
            builder: (_, state) => VerifikasiFormScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),

          // Penagihan
          GoRoute(
            path: '/penagihan',
            builder: (_, __) => const PenagihanListScreen(),
          ),
          GoRoute(
            path: '/penagihan/bayar/:pinjamanId',
            builder: (_, state) => PenagihanBayarScreen(
              pinjamanId: int.parse(state.pathParameters['pinjamanId']!),
            ),
          ),

          // UMKM
          GoRoute(
            path: '/umkm/katalog',
            builder: (_, __) => const UmkmKatalogScreen(),
          ),
          GoRoute(
            path: '/umkm/produk/:id',
            builder: (_, state) => UmkmProdukDetailScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/umkm/pesanan-saya',
            builder: (_, __) => const UmkmPesananSayaScreen(),
          ),
          GoRoute(
            path: '/umkm/toko-saya',
            builder: (_, __) => const UmkmTokoSayaScreen(),
          ),
          GoRoute(
            path: '/umkm/daftar-penjual',
            builder: (_, __) => const UmkmDaftarPenjualScreen(),
          ),
          GoRoute(
            path: '/umkm/pesanan-masuk',
            builder: (_, __) => const UmkmPesananMasukScreen(),
          ),
        ],
      ),
    ],
  );
});
