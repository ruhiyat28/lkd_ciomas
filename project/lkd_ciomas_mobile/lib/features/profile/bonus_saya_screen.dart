import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/bonus.dart';

final bonusSayaProvider = FutureProvider<BonusData?>((ref) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.bonusSaya);
    return BonusData.fromJson(res.data['data']);
  } catch (e) {
    return null;
  }
});

class BonusSayaScreen extends ConsumerWidget {
  const BonusSayaScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bonusAsync = ref.watch(bonusSayaProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Bonus Saya')),
      body: RefreshIndicator(
        onRefresh: () async => ref.refresh(bonusSayaProvider),
        child: bonusAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 64, color: AppColors.error),
                const SizedBox(height: 16),
                const Text('Gagal memuat bonus'),
                ElevatedButton(
                  onPressed: () => ref.refresh(bonusSayaProvider),
                  child: const Text('Coba Lagi'),
                ),
              ],
            ),
          ),
          data: (data) {
            if (data == null || data.items.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 80),
                  Center(
                    child: Column(
                      children: [
                        Icon(Icons.emoji_events, size: 64, color: AppColors.disabled),
                        SizedBox(height: 16),
                        Text('Belum ada bonus',
                            style: TextStyle(color: AppColors.textSecondary)),
                      ],
                    ),
                  ),
                ],
              );
            }
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Summary
                Card(
                  color: AppColors.primary,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Text('Total Bonus',
                            style: TextStyle(color: Colors.white70)),
                        Text(data.totalSemua.toCurrencyRp,
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 28,
                                fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        Text('Belum diklaim: ${data.totalBonus.toCurrencyRp}',
                            style: const TextStyle(color: Colors.white70)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                if (data.items.isNotEmpty)
                  ...data.items.map((item) => Card(
                        child: ListTile(
                          leading: Icon(
                            item.tipe == 'bonus_petugas'
                                ? Icons.person
                                : Icons.supervisor_account,
                            color: item.status == 'diklaim'
                                ? AppColors.success
                                : AppColors.warning,
                          ),
                          title: Text(
                              '${item.tipe == 'bonus_petugas' ? 'Bonus' : 'Bonus Pembina'}'),
                          subtitle: Text(
                              '${item.status.replaceAll('_', ' ')} · ${formatDateApi(item.tanggalHitung)}'),
                          trailing: Text(
                            item.jumlahBonus.toCurrencyRp,
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: item.status == 'diklaim'
                                  ? AppColors.success
                                  : AppColors.textPrimary,
                            ),
                          ),
                        ),
                      )),
              ],
            );
          },
        ),
      ),
    );
  }
}
