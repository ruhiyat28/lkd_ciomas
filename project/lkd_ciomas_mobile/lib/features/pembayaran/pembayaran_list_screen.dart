import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/pembayaran.dart';

final pembayaranListProvider = FutureProvider<List<Pembayaran>>((ref) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.pembayaran, params: {'page': 1, 'per_page': 50});
    final data = res.data['data'] as List;
    return data.map((e) => Pembayaran.fromJson(e)).toList();
  } catch (e) {
    throw Exception('Gagal memuat pembayaran');
  }
});

class PembayaranListScreen extends ConsumerWidget {
  const PembayaranListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listAsync = ref.watch(pembayaranListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Riwayat Pembayaran')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(pembayaranListProvider);
          await ref.read(pembayaranListProvider.future);
        },
        child: listAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 64, color: AppColors.error),
                const SizedBox(height: 16),
                const Text('Gagal memuat pembayaran'),
                ElevatedButton(
                  onPressed: () => ref.refresh(pembayaranListProvider),
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
                        Icon(Icons.receipt_long, size: 64, color: AppColors.disabled),
                        SizedBox(height: 16),
                        Text('Belum ada pembayaran',
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
                                  style: const TextStyle(fontWeight: FontWeight.bold)),
                            ),
                            _statusChip(b),
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
                                    color: AppColors.primary)),
                            const Spacer(),
                            Text(formatDateApi(b.tanggalBayar),
                                style: const TextStyle(
                                    fontSize: 12,
                                    color: AppColors.textSecondary)),
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

  Widget _statusChip(Pembayaran b) {
    Color color;
    String label;
    if (b.isWaiting) {
      color = AppColors.warning;
      label = 'Menunggu';
    } else if (b.isApproved) {
      color = AppColors.success;
      label = 'Diterima';
    } else if (b.isRejected) {
      color = AppColors.error;
      label = 'Ditolak';
    } else {
      color = AppColors.success;
      label = 'Valid';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(label, style: TextStyle(fontSize: 10, color: color)),
    );
  }
}
