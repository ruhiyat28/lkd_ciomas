import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/pinjaman.dart';

final pinjamanDetailProvider = FutureProvider.family<Pinjaman?, int>((ref, id) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.pinjamanDetail(id));
    return Pinjaman.fromJson(res.data['data']);
  } catch (e) {
    return null;
  }
});

class PinjamanDetailScreen extends ConsumerWidget {
  final int id;
  const PinjamanDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(pinjamanDetailProvider(id));

    return Scaffold(
      appBar: AppBar(title: const Text('Detail Pinjaman')),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(child: Text('Gagal memuat detail')),
        data: (p) {
          if (p == null) {
            return const Center(child: Text('Pinjaman tidak ditemukan'));
          }
          return RefreshIndicator(
            onRefresh: () async {
          ref.invalidate(pinjamanDetailProvider(id));
          await ref.read(pinjamanDetailProvider(id).future);
        },
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Header
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(p.spk,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 18)),
                                  const SizedBox(height: 4),
                                  Text(p.nasabah,
                                      style: const TextStyle(
                                          color: AppColors.textSecondary)),
                                ],
                              ),
                            ),
                            _statusChip(p.status),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 12),

                // Info Pinjaman
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Info Pinjaman',
                            style: TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 16)),
                        const Divider(),
                        _row('Jumlah', p.jumlahPinjaman.toCurrencyRp),
                        _row('Jasa', '${p.jasaPersen}%'),
                        _row('Tenor', '${p.tenor} bulan'),
                        _row('Angsuran Pokok',
                            (p.angsuranPokok ?? 0).toCurrencyRp),
                        _row('Angsuran Jasa',
                            (p.angsuranJasa ?? 0).toCurrencyRp),
                        _row('Angsuran Total',
                            (p.angsuranTotal ?? 0).toCurrencyRp),
                        _row(
                            'Tanggal Pengajuan', formatDateApi(p.tanggalPengajuan)),
                        _row('Tanggal Cair', formatDateApi(p.tanggalCair)),
                        if (p.tujuan != null && p.tujuan!.isNotEmpty)
                          _row('Tujuan', p.tujuan!),
                      ],
                    ),
                  ),
                ),

                // Status Pembayaran (if cair)
                if (p.isAktif) ...[
                  const SizedBox(height: 12),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Status Pembayaran',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold, fontSize: 16)),
                          const Divider(),
                          _row('Saldo Pokok',
                              (p.saldoPokok ?? 0).toCurrencyRp, bold: true),
                          _row('Pokok Terbayar',
                              (p.pokokTerbayar ?? 0).toCurrencyRp),
                          _row('Jasa Terbayar',
                              (p.jasaTerbayar ?? 0).toCurrencyRp),
                          if (p.bulanNunggak != null && p.bulanNunggak! > 0) ...[
                            const Divider(),
                            _row('Tunggakan Pokok',
                                (p.tunggakanPokok ?? 0).toCurrencyRp,
                                color: AppColors.error),
                            _row('Tunggakan Jasa',
                                (p.tunggakanJasa ?? 0).toCurrencyRp,
                                color: AppColors.error),
                            _row('Bulan Nunggak',
                                '${p.bulanNunggak} bulan',
                                color: AppColors.error),
                          ],
                          if (p.kolektibilitasLabel != null &&
                              p.kolektibilitasLabel!.isNotEmpty)
                            _row('Kolektibilitas', p.kolektibilitasLabel!),
                        ],
                      ),
                    ),
                  ),
                ],

                const SizedBox(height: 12),

                // Tombol Jadwal
                if (p.isAktif)
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.calendar_month,
                          color: AppColors.primary),
                      title: const Text('Jadwal Angsuran'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.push('/pinjaman/$id/jadwal'),
                    ),
                  ),

                // Nasabah detail
                if (p.nasabahDetail != null) ...[
                  const SizedBox(height: 12),
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.person, color: AppColors.info),
                      title: Text(p.nasabahDetail!.nama),
                      subtitle: Text(p.nasabahDetail!.nasabahId),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.push('/nasabah/${p.nasabahDetail!.id}'),
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _statusChip(String status) {
    Color color;
    switch (status) {
      case 'cair':
        color = AppColors.success;
        break;
      case 'lunas':
        color = AppColors.info;
        break;
      case 'pengajuan':
      case 'cek_dokumen':
      case 'verifikasi':
        color = AppColors.warning;
        break;
      case 'ditolak':
        color = AppColors.error;
        break;
      default:
        color = AppColors.textSecondary;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(status,
          style: TextStyle(fontSize: 11, color: color)),
    );
  }

  Widget _row(String label, String value, {bool bold = false, Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
              width: 130,
              child: Text(label,
                  style: const TextStyle(color: AppColors.textSecondary))),
          Expanded(
            child: Text(value,
                style: TextStyle(
                    fontWeight: bold ? FontWeight.bold : FontWeight.normal,
                    color: color)),
          ),
        ],
      ),
    );
  }
}
