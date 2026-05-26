import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/pinjaman.dart';

final jadwalProvider = FutureProvider.family<JadwalAngsuranData?, int>((ref, id) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.pinjamanAngsuran(id));
    return JadwalAngsuranData.fromJson(res.data['data']);
  } catch (e) {
    return null;
  }
});

class JadwalAngsuranData {
  final int pinjamanId;
  final String spk;
  final int jumlahPinjaman;
  final int saldoPokok;
  final int angsuranPokok;
  final int angsuranJasa;
  final int angsuranTotal;
  final int pokokTerbayar;
  final int jasaTerbayar;
  final List<JadwalAngsuran> jadwal;

  JadwalAngsuranData({
    required this.pinjamanId,
    required this.spk,
    required this.jumlahPinjaman,
    required this.saldoPokok,
    required this.angsuranPokok,
    required this.angsuranJasa,
    required this.angsuranTotal,
    required this.pokokTerbayar,
    required this.jasaTerbayar,
    required this.jadwal,
  });

  factory JadwalAngsuranData.fromJson(Map<String, dynamic> json) {
    return JadwalAngsuranData(
      pinjamanId: json['pinjaman_id'] as int,
      spk: json['spk'] as String? ?? '',
      jumlahPinjaman: json['jumlah_pinjaman'] as int? ?? 0,
      saldoPokok: json['saldo_pokok'] as int? ?? 0,
      angsuranPokok: json['angsuran_pokok'] as int? ?? 0,
      angsuranJasa: json['angsuran_jasa'] as int? ?? 0,
      angsuranTotal: json['angsuran_total'] as int? ?? 0,
      pokokTerbayar: json['pokok_terbayar'] as int? ?? 0,
      jasaTerbayar: json['jasa_terbayar'] as int? ?? 0,
      jadwal: (json['jadwal'] as List?)
              ?.map((e) => JadwalAngsuran.fromJson(e))
              .toList() ??
          [],
    );
  }
}

class JadwalAngsuranScreen extends ConsumerWidget {
  final int id;
  const JadwalAngsuranScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jadwalAsync = ref.watch(jadwalProvider(id));

    return Scaffold(
      appBar: AppBar(title: const Text('Jadwal Angsuran')),
      body: jadwalAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(child: Text('Gagal memuat jadwal')),
        data: (data) {
          if (data == null) {
            return const Center(child: Text('Data tidak ditemukan'));
          }
          return RefreshIndicator(
            onRefresh: () async {
          ref.invalidate(jadwalProvider(id));
          await ref.read(jadwalProvider(id).future);
        },
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Summary
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(data.spk,
                                  style: const TextStyle(fontWeight: FontWeight.bold)),
                              Text('Sisa: ${data.saldoPokok.toCurrencyRp}',
                                  style: const TextStyle(
                                      color: AppColors.primary,
                                      fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text('Terbayar: ${data.pokokTerbayar.toCurrencyRp}',
                                style: const TextStyle(
                                    fontSize: 12, color: AppColors.success)),
                            Text('${data.jadwal.where((j) => j.lunas).length}/${data.jadwal.length}',
                                style: const TextStyle(fontSize: 12)),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 8),
                // Table header
                Card(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                    child: Row(
                      children: const [
                        SizedBox(width: 30, child: Text('#', style: TextStyle(fontWeight: FontWeight.bold))),
                        Expanded(child: Text('Tanggal', style: TextStyle(fontWeight: FontWeight.bold))),
                        Expanded(child: Text('Pokok', style: TextStyle(fontWeight: FontWeight.bold), textAlign: TextAlign.right)),
                        Expanded(child: Text('Jasa', style: TextStyle(fontWeight: FontWeight.bold), textAlign: TextAlign.right)),
                        Expanded(child: Text('Total', style: TextStyle(fontWeight: FontWeight.bold), textAlign: TextAlign.right)),
                        SizedBox(width: 60, child: Text('Status', style: TextStyle(fontWeight: FontWeight.bold))),
                      ],
                    ),
                  ),
                ),
                ...data.jadwal.map((j) => Card(
                      margin: const EdgeInsets.symmetric(vertical: 2),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                        child: Row(
                          children: [
                            SizedBox(width: 30, child: Text('${j.ke}')),
                            Expanded(child: Text(formatDateApi(j.tanggal), style: const TextStyle(fontSize: 12))),
                            Expanded(child: Text(j.pokok.toCurrencyRp, textAlign: TextAlign.right, style: const TextStyle(fontSize: 12))),
                            Expanded(child: Text(j.jasa.toCurrencyRp, textAlign: TextAlign.right, style: const TextStyle(fontSize: 12))),
                            Expanded(child: Text(j.total.toCurrencyRp, textAlign: TextAlign.right, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                            SizedBox(
                              width: 60,
                              child: Icon(
                                j.lunas ? Icons.check_circle : (j.terlambat ? Icons.warning : Icons.schedule),
                                color: j.lunas
                                    ? AppColors.success
                                    : j.terlambat
                                        ? AppColors.error
                                        : AppColors.textSecondary,
                                size: 18,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )),
              ],
            ),
          );
        },
      ),
    );
  }
}
