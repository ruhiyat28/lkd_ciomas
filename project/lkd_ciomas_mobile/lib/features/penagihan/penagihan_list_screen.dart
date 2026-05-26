import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/utils/currency_format.dart';
import '../../models/pinjaman.dart';
import '../../core/api/api_endpoints.dart';

final tagihanProvider = FutureProvider<List<Pinjaman>>((ref) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.pinjaman,
        params: {'status': 'aktif', 'page': 1, 'per_page': 100});
    final data = res.data['data'] as List;
    return data.map((e) => Pinjaman.fromJson(e)).toList();
  } catch (e) {
    throw Exception('Gagal memuat tagihan');
  }
});

class PenagihanListScreen extends ConsumerWidget {
  const PenagihanListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tagihanAsync = ref.watch(tagihanProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Tagihan Aktif')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(tagihanProvider);
          await ref.read(tagihanProvider.future);
        },
        child: tagihanAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _error(ref),
          data: (list) {
            if (list.isEmpty) return _empty();
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _TagihanCard(p: list[i]),
            );
          },
        ),
      ),
    );
  }

  Widget _error(WidgetRef ref) => ListView(
        children: [
          const SizedBox(height: 120),
          const Icon(Icons.cloud_off_rounded,
              size: 64, color: AppColors.textHint),
          const SizedBox(height: 12),
          const Center(
              child: Text('Gagal memuat tagihan',
                  style: TextStyle(color: AppColors.textSecondary))),
          const SizedBox(height: 16),
          Center(
            child: SizedBox(
              width: 180,
              child: OutlinedButton.icon(
                onPressed: () => ref.invalidate(tagihanProvider),
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Coba Lagi'),
              ),
            ),
          ),
        ],
      );

  Widget _empty() => ListView(
        children: const [
          SizedBox(height: 120),
          Icon(Icons.check_circle_outline_rounded,
              size: 64, color: AppColors.success),
          SizedBox(height: 12),
          Center(
            child: Text('Semua tagihan sudah lunas',
                style: TextStyle(color: AppColors.textSecondary)),
          ),
        ],
      );
}

class _TagihanCard extends StatelessWidget {
  final Pinjaman p;
  const _TagihanCard({required this.p});

  @override
  Widget build(BuildContext context) {
    final nunggak = p.bulanNunggak ?? 0;
    final danger = nunggak > 0;
    final color = danger ? AppColors.error : AppColors.success;

    return InkWell(
      onTap: () => context.push('/penagihan/bayar/${p.id}'),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: AppShadows.sm,
          border: danger
              ? Border.all(
                  color: AppColors.error.withValues(alpha: 0.18), width: 1)
              : null,
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                danger
                    ? Icons.warning_amber_rounded
                    : Icons.check_circle_outline_rounded,
                color: color,
                size: 22,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    p.nasabah,
                    style: const TextStyle(
                        fontSize: 14.5, fontWeight: FontWeight.w800),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    p.spk,
                    style: const TextStyle(
                        fontSize: 11.5, color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Text(
                        p.angsuranTotal?.toCurrencyRp ?? '-',
                        style: const TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w800,
                            color: AppColors.primary),
                      ),
                      const SizedBox(width: 10),
                      if (danger)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.error.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            '$nunggak bln nunggak',
                            style: const TextStyle(
                                fontSize: 10.5,
                                fontWeight: FontWeight.w700,
                                color: AppColors.error),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textHint),
          ],
        ),
      ),
    );
  }
}
