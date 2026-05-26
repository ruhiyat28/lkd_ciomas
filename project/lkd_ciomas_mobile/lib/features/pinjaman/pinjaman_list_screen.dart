import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../models/pinjaman.dart';

final pinjamanListProvider = FutureProvider<List<Pinjaman>>((ref) async {
  final api = ref.watch(apiClientProvider);
  final params = <String, dynamic>{'page': 1, 'per_page': 50};
  final res = await api.get(ApiEndpoints.pinjaman, params: params);
  final data = res.data['data'] as List;
  return data
      .map((e) => Pinjaman.fromJson(e as Map<String, dynamic>))
      .toList();
});

class PinjamanListScreen extends ConsumerWidget {
  const PinjamanListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pinjamanAsync = ref.watch(pinjamanListProvider);
    final auth = ref.watch(authProvider);
    final user = auth.user;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Pinjaman')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(pinjamanListProvider);
          await ref.read(pinjamanListProvider.future);
        },
        child: pinjamanAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _ErrorView(
              onRetry: () => ref.invalidate(pinjamanListProvider)),
          data: (list) {
            if (list.isEmpty) return const _EmptyView();
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _PinjamanCard(p: list[i]),
            );
          },
        ),
      ),
      floatingActionButton: (user?.canWritePinjaman == true ||
              user?.isNasabah == true)
          ? FloatingActionButton.extended(
              onPressed: () => context.push('/pinjaman/tambah'),
              icon: const Icon(Icons.add_rounded),
              label: const Text('Ajukan'),
            )
          : null,
    );
  }
}

class _PinjamanCard extends StatelessWidget {
  final Pinjaman p;
  const _PinjamanCard({required this.p});

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(p.status);
    return InkWell(
      onTap: () => context.push('/pinjaman/${p.id}'),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: AppShadows.sm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.primarySoft,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.account_balance_rounded,
                      color: AppColors.primary, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        p.nasabah,
                        style: const TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w800),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text('${p.spk} · ${p.jenisPinjaman}',
                          style: const TextStyle(
                              fontSize: 11.5,
                              color: AppColors.textSecondary)),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    _statusLabel(p.status),
                    style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.w700,
                        color: color),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Jumlah',
                          style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textSecondary)),
                      const SizedBox(height: 2),
                      Text(p.jumlahPinjaman.toCurrencyRp,
                          style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              color: AppColors.primary)),
                    ],
                  ),
                ),
                if (p.saldoPokok != null && p.saldoPokok! > 0)
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        const Text('Sisa',
                            style: TextStyle(
                                fontSize: 11,
                                color: AppColors.textSecondary)),
                        const SizedBox(height: 2),
                        Text(p.saldoPokok!.toCurrencyRp,
                            style: const TextStyle(
                                fontSize: 13.5,
                                fontWeight: FontWeight.w700)),
                      ],
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _statusColor(String s) {
    switch (s) {
      case 'cair':
        return AppColors.success;
      case 'lunas':
        return AppColors.info;
      case 'pengajuan':
      case 'cek_dokumen':
      case 'verifikasi':
        return AppColors.warning;
      case 'ditolak':
        return AppColors.error;
      default:
        return AppColors.textSecondary;
    }
  }

  String _statusLabel(String s) {
    switch (s) {
      case 'cair':
        return 'AKTIF';
      case 'lunas':
        return 'LUNAS';
      case 'pengajuan':
        return 'PENGAJUAN';
      case 'cek_dokumen':
        return 'CEK DOK';
      case 'verifikasi':
        return 'VERIFIKASI';
      case 'ditolak':
        return 'DITOLAK';
      default:
        return s.toUpperCase();
    }
  }
}

class _EmptyView extends StatelessWidget {
  const _EmptyView();
  @override
  Widget build(BuildContext context) {
    return ListView(
      children: const [
        SizedBox(height: 120),
        Icon(Icons.inbox_rounded, size: 64, color: AppColors.textHint),
        SizedBox(height: 12),
        Center(
          child: Text('Belum ada pinjaman',
              style: TextStyle(color: AppColors.textSecondary)),
        ),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  final VoidCallback onRetry;
  const _ErrorView({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 120),
        const Icon(Icons.cloud_off_rounded,
            size: 64, color: AppColors.textHint),
        const SizedBox(height: 12),
        const Center(
          child: Text('Gagal memuat pinjaman',
              style: TextStyle(color: AppColors.textSecondary)),
        ),
        const SizedBox(height: 16),
        Center(
          child: SizedBox(
            width: 180,
            child: OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Coba Lagi'),
            ),
          ),
        ),
      ],
    );
  }
}
