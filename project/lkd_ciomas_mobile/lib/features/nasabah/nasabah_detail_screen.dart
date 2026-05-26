import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/nasabah.dart';

final nasabahDetailProvider = FutureProvider.family<Nasabah?, int>((ref, id) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.nasabahDetail(id));
    return Nasabah.fromJson(res.data['data']);
  } catch (e) {
    return null;
  }
});

class NasabahDetailScreen extends ConsumerWidget {
  final int id;
  const NasabahDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(nasabahDetailProvider(id));
    final auth = ref.watch(authProvider);
    final user = auth.user;

    return Scaffold(
      appBar: AppBar(title: const Text('Detail Nasabah')),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 64, color: AppColors.error),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.refresh(nasabahDetailProvider(id)),
                child: const Text('Coba Lagi'),
              ),
            ],
          ),
        ),
        data: (nasabah) {
          if (nasabah == null) {
            return const Center(child: Text('Nasabah tidak ditemukan'));
          }
          return RefreshIndicator(
            onRefresh: () async => ref.refresh(nasabahDetailProvider(id)),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Header
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 30,
                          backgroundColor: AppColors.primaryLight,
                          child: Text(
                            nasabah.nama.isNotEmpty ? nasabah.nama[0] : '?',
                            style: const TextStyle(
                                fontSize: 24, color: Colors.white),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(nasabah.nama,
                                  style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold)),
                              Text(nasabah.nasabahId,
                                  style: const TextStyle(
                                      color: AppColors.textSecondary)),
                              Container(
                                margin: const EdgeInsets.only(top: 4),
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: nasabah.isAktif
                                      ? AppColors.success.withValues(alpha: 0.1)
                                      : AppColors.warning.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  nasabah.isAktif ? 'Aktif' : 'Calon',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: nasabah.isAktif
                                        ? AppColors.success
                                        : AppColors.warning,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (user?.canWriteNasabah == true)
                          IconButton(
                            icon: const Icon(Icons.edit),
                            onPressed: () =>
                                context.push('/nasabah/$id/edit'),
                          ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 12),

                // Info Pribadi
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Data Pribadi',
                            style: TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 16)),
                        const Divider(),
                        _info('NIK', nasabah.nik),
                        _info('Desa', '${nasabah.namaDesa} (${nasabah.kodeDesa})'),
                        _info('No. HP', nasabah.noHp),
                        _info('Alamat', nasabah.alamat),
                        _info('Tempat Lahir', nasabah.tempatLahir ?? '-'),
                        _info('Tanggal Lahir',
                            formatDateApi(nasabah.tanggalLahir)),
                        _info('Jenis Kelamin',
                            nasabah.jenisKelamin == 'L' ? 'Laki-laki' : nasabah.jenisKelamin == 'P' ? 'Perempuan' : '-'),
                        _info('Pekerjaan', nasabah.pekerjaan),
                        if (nasabah.namaPasangan != null &&
                            nasabah.namaPasangan!.isNotEmpty)
                          _info('Pasangan', nasabah.namaPasangan!),
                        _info('Status', nasabah.status),
                      ],
                    ),
                  ),
                ),

                // Rekening
                if (nasabah.rekening != null) ...[
                  const SizedBox(height: 12),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Tabungan',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold, fontSize: 16)),
                          const Divider(),
                          _info(
                              'No. Rekening', nasabah.rekening!.noRekening),
                          _info('Saldo Pokok',
                              nasabah.rekening!.saldoPokok.toCurrencyRp),
                          _info('Saldo Wajib',
                              nasabah.rekening!.saldoWajib.toCurrencyRp),
                          _info('Saldo Sukarela',
                              nasabah.rekening!.saldoSukarela.toCurrencyRp),
                          _info('Total Saldo',
                              nasabah.rekening!.totalSaldo.toCurrencyRp,
                              bold: true),
                        ],
                      ),
                    ),
                  ),
                ],

                // Pinjaman
                if (nasabah.pinjaman != null &&
                    nasabah.pinjaman!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Pinjaman',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold, fontSize: 16)),
                          const Divider(),
                          ...nasabah.pinjaman!.map((p) => ListTile(
                                dense: true,
                                title: Text('${p.spk} · ${p.jenisPinjaman}'),
                                subtitle: Text(
                                    '${p.jumlahPinjaman.toCurrencyRp} · ${p.tenor} bulan'),
                                trailing: Text(p.status,
                                    style: TextStyle(
                                      color: p.status == 'cair'
                                          ? AppColors.success
                                          : p.status == 'lunas'
                                              ? AppColors.info
                                              : AppColors.warning,
                                    )),
                                onTap: () =>
                                    context.push('/pinjaman/${p.id}'),
                              )),
                        ],
                      ),
                    ),
                  ),
                ],

                // Approve button (for calon)
                if (nasabah.isCalon &&
                    (user?.isAdmin == true ||
                        user?.isManajer == true)) ...[
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => _approve(context, ref, id, 'approve'),
                          icon: const Icon(Icons.check),
                          label: const Text('Setujui'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.success,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _approve(context, ref, id, 'reject'),
                          icon: const Icon(Icons.close),
                          label: const Text('Tolak'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppColors.error,
                            side: const BorderSide(color: AppColors.error),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _info(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 110, child: Text(label,
              style: const TextStyle(color: AppColors.textSecondary))),
          Expanded(
            child: Text(value,
                style: TextStyle(
                    fontWeight: bold ? FontWeight.bold : FontWeight.normal)),
          ),
        ],
      ),
    );
  }

  Future<void> _approve(BuildContext context, WidgetRef ref, int id, String action) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.post(ApiEndpoints.nasabahApprove(id), data: {'action': action});
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(action == 'approve' ? 'Nasabah disetujui' : 'Pendaftaran ditolak'),
            backgroundColor: AppColors.success,
          ),
        );
        ref.refresh(nasabahDetailProvider(id));
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
