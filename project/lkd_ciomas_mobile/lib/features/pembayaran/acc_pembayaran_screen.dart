import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/pembayaran.dart';

final accPembayaranProvider = FutureProvider<List<Pembayaran>>((ref) async {
  final api = ref.watch(apiClientProvider);
  final res = await api.get(ApiEndpoints.pembayaran,
      params: {'status_acc': 'menunggu', 'page': 1, 'per_page': 50});
  final data = res.data['data'] as List;
  return data.map((e) => Pembayaran.fromJson(e)).toList();
});

class AccPembayaranScreen extends ConsumerWidget {
  const AccPembayaranScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listAsync = ref.watch(accPembayaranProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('ACC Pembayaran')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(accPembayaranProvider);
          await ref.read(accPembayaranProvider.future);
        },
        child: listAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 64, color: AppColors.error),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    ref.invalidate(accPembayaranProvider);
                  },
                  child: const Text('Coba Lagi'),
                ),
              ],
            ),
          ),
          data: (list) {
            if (list.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 80),
                  Center(
                    child: Column(
                      children: [
                        Icon(Icons.check_circle, size: 64, color: AppColors.success),
                        SizedBox(height: 16),
                        Text('Tidak ada pembayaran menunggu ACC',
                            style: TextStyle(color: AppColors.textSecondary)),
                      ],
                    ),
                  ),
                ],
              );
            }
            return ListView.builder(
              itemCount: list.length,
              itemBuilder: (_, i) {
                final b = list[i];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(b.nasabah,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16)),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppColors.warning.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.schedule_rounded,
                                      size: 12, color: AppColors.warning),
                                  SizedBox(width: 4),
                                  Text('Menunggu',
                                      style: TextStyle(
                                          fontSize: 10,
                                          fontWeight: FontWeight.w700,
                                          color: AppColors.warning)),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text('${b.spk} · ${b.noKuitansi}',
                            style: const TextStyle(
                                fontSize: 12, color: AppColors.textSecondary)),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Text(b.jumlahBayar.toCurrencyRp,
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.primary,
                                    fontSize: 18)),
                            const Spacer(),
                            Text(formatDateApi(b.tanggalBayar),
                                style: const TextStyle(
                                    fontSize: 12,
                                    color: AppColors.textSecondary)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: SizedBox(
                                height: 36,
                                child: ElevatedButton.icon(
                                  onPressed: () => _acc(context, ref, b.id),
                                  icon: const Icon(Icons.check, size: 16),
                                  label: const Text('Terima',
                                      style: TextStyle(fontSize: 12)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppColors.success,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: SizedBox(
                                height: 36,
                                child: OutlinedButton.icon(
                                  onPressed: () => _tolak(context, ref, b.id),
                                  icon: const Icon(Icons.close, size: 16),
                                  label: const Text('Tolak',
                                      style: TextStyle(fontSize: 12)),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: AppColors.error,
                                    side: const BorderSide(
                                        color: AppColors.error),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }

  Future<void> _acc(BuildContext context, WidgetRef ref, int id) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.post(ApiEndpoints.pembayaranAcc(id));
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Pembayaran diterima'),
              backgroundColor: AppColors.success),
        );
        ref.invalidate(accPembayaranProvider);
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Gagal: $e'), backgroundColor: AppColors.error),
        );
      }
    }
  }

  Future<void> _tolak(BuildContext context, WidgetRef ref, int id) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.post(ApiEndpoints.pembayaranTolak(id));
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Pembayaran ditolak'),
              backgroundColor: AppColors.error),
        );
        ref.invalidate(accPembayaranProvider);
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Gagal: $e'), backgroundColor: AppColors.error),
        );
      }
    }
  }
}
