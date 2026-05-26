import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../api/api_client.dart';
import '../auth/auth_provider.dart';
import '../../models/user.dart';
import '../../models/nasabah.dart';
import '../../models/tabungan.dart';
import '../api/api_endpoints.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthState {
  final AuthStatus status;
  final User? user;
  final Nasabah? nasabah;
  final RekeningTabungan? rekening;
  final String? token;
  final String? error;

  const AuthState({
    this.status = AuthStatus.unknown,
    this.user,
    this.nasabah,
    this.rekening,
    this.token,
    this.error,
  });

  AuthState copyWith({
    AuthStatus? status,
    User? user,
    Nasabah? nasabah,
    RekeningTabungan? rekening,
    String? token,
    String? error,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      nasabah: nasabah ?? this.nasabah,
      rekening: rekening ?? this.rekening,
      token: token ?? this.token,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiClient _api;

  AuthNotifier(this._api) : super(const AuthState());

  Future<void> checkSession() async {
    final token = await _api.getToken();
    if (token == null) {
      state = const AuthState(status: AuthStatus.unauthenticated);
      return;
    }
    try {
      final res = await _api.get(ApiEndpoints.me);
      final data = res.data['data'];
      state = AuthState(
        status: AuthStatus.authenticated,
        user: User.fromJson(data['user']),
        nasabah: data['nasabah'] != null
            ? Nasabah.fromJson(data['nasabah'])
            : null,
        rekening: data['rekening'] != null
            ? RekeningTabungan.fromJson(data['rekening'])
            : null,
        token: token,
      );
    } catch (e) {
      await _api.deleteToken();
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  Future<String?> login(String username, String password,
      {String? fcmToken}) async {
    try {
      state = state.copyWith(error: null);
      final res = await _api.post(ApiEndpoints.login, data: {
        'username': username,
        'password': password,
        if (fcmToken != null) 'fcm_token': fcmToken,
      });
      final data = res.data['data'];
      final token = data['token'] as String;
      await _api.saveToken(token);
      final user = User.fromJson(data['user']);
      state = AuthState(
        status: AuthStatus.authenticated,
        user: user,
        token: token,
      );
      // Fetch full profile (nasabah + rekening data)
      try {
        final meRes = await _api.get(ApiEndpoints.me);
        final meData = meRes.data['data'];
        state = AuthState(
          status: AuthStatus.authenticated,
          user: User.fromJson(meData['user']),
          nasabah: meData['nasabah'] != null
              ? Nasabah.fromJson(meData['nasabah'])
              : null,
          rekening: meData['rekening'] != null
              ? RekeningTabungan.fromJson(meData['rekening'])
              : null,
          token: token,
        );
      } catch (_) {
        // keep the basic auth state from login
      }
      return null;
    } on DioException catch (e) {
      final msg = e.response?.data?['message'] as String? ??
          'Gagal login. Periksa koneksi.';
      state = state.copyWith(error: msg);
      return msg;
    } catch (e) {
      final msg = 'Terjadi kesalahan. Silakan coba lagi.';
      state = state.copyWith(error: msg);
      return msg;
    }
  }

  Future<void> logout() async {
    await _api.deleteToken();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  Future<String?> register({
    required String username,
    required String nama,
    required String password,
    required String nik,
    required String noHp,
    required String kodeDesa,
    String? alamat,
    String? tempatLahir,
    String? tanggalLahir,
    String? jenisKelamin,
    String? pekerjaan,
    String? namaPasangan,
  }) async {
    try {
      await _api.post(ApiEndpoints.register, data: {
        'username': username,
        'nama': nama,
        'password': password,
        'nik': nik,
        'no_hp': noHp,
        'kode_desa': kodeDesa,
        'alamat': alamat ?? '',
        'tempat_lahir': tempatLahir ?? '',
        'tanggal_lahir': tanggalLahir ?? '',
        'jenis_kelamin': jenisKelamin ?? '',
        'pekerjaan': pekerjaan ?? '',
        'nama_pasangan': namaPasangan ?? '',
      });
      return null;
    } on DioException catch (e) {
      return e.response?.data?['message'] as String? ??
          'Gagal mendaftar.';
    } catch (e) {
      return 'Terjadi kesalahan. Silakan coba lagi.';
    }
  }

  Future<String?> changePassword(
      String oldPassword, String newPassword) async {
    try {
      await _api.post(ApiEndpoints.changePassword, data: {
        'old_password': oldPassword,
        'new_password': newPassword,
      });
      return null;
    } on DioException catch (e) {
      return e.response?.data?['message'] as String? ??
          'Gagal mengubah password.';
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }
}

final authProvider =
    StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final api = ref.watch(apiClientProvider);
  return AuthNotifier(api);
});
