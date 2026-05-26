import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../models/pinjaman.dart';

final verifikasiListProvider = FutureProvider<List<Pinjaman>>((ref) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.pinjaman,
        params: {
          'page': 1,
          'per_page': 50,
          'status': 'verifikasi',
        });
    final data = res.data['data'] as List;
    return data.map((e) => Pinjaman.fromJson(e)).toList();
  } catch (e) {
    throw Exception('Gagal memuat data verifikasi');
  }
});

class VerifikasiListScreen extends ConsumerWidget {
  const VerifikasiListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listAsync = ref.watch(verifikasiListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Verifikasi Pinjaman')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(verifikasiListProvider);
          await ref.read(verifikasiListProvider.future);
        },
        child: listAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 64, color: AppColors.error),
                const SizedBox(height: 16),
                const Text('Gagal memuat verifikasi'),
                ElevatedButton(
                  onPressed: () => ref.refresh(verifikasiListProvider),
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
                        Icon(Icons.verified_outlined, size: 64, color: AppColors.disabled),
                        SizedBox(height: 16),
                        Text('Tidak ada pinjaman menunggu verifikasi',
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
                final p = list[i];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  child: ListTile(
                    leading: const CircleAvatar(
                      backgroundColor: AppColors.warning,
                      child: Icon(Icons.pending, color: Colors.white),
                    ),
                    title: Text(p.nasabah),
                    subtitle: Text(
                        '${p.spk} · ${p.jumlahPinjaman.toCurrencyRp}'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('/verifikasi/${p.id}'),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
