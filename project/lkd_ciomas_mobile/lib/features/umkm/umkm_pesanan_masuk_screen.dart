import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';

class UmkmPesananMasukScreen extends ConsumerStatefulWidget {
  const UmkmPesananMasukScreen({super.key});

  @override
  ConsumerState<UmkmPesananMasukScreen> createState() =>
      _UmkmPesananMasukScreenState();
}

class _UmkmPesananMasukScreenState
    extends ConsumerState<UmkmPesananMasukScreen> {
  List<Map<String, dynamic>> _orders = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = ref.read(apiClientProvider);
    try {
      final res = await api.get(ApiEndpoints.umkmPesanan,
          params: {'page': 1, 'per_page': 50, 'role': 'penjual'});
      _orders = List<Map<String, dynamic>>.from(
          res.data['data']?['list'] ?? []);
    } catch (_) {}
    setState(() => _loading = false);
  }

  Future<void> _updateStatus(int id, String status) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.put(ApiEndpoints.umkmPesananStatus(id), data: {
        'status': status,
      });
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Gagal: $e'), backgroundColor: AppColors.error),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pesanan Masuk')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _orders.isEmpty
                ? ListView(
                    children: const [
                      SizedBox(height: 80),
                      Center(
                        child: Column(
                          children: [
                            Icon(Icons.inbox, size: 64,
                                color: AppColors.disabled),
                            SizedBox(height: 16),
                            Text('Belum ada pesanan masuk',
                                style: TextStyle(
                                    color: AppColors.textSecondary)),
                          ],
                        ),
                      ),
                    ],
                  )
                : ListView.builder(
                    itemCount: _orders.length,
                    itemBuilder: (_, i) {
                      final o = _orders[i];
                      final status = o['status'] as String? ?? '';
                      return Card(
                        margin: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 4),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                        '${o['nomor_pesanan'] ?? ''}',
                                        style: const TextStyle(
                                            fontWeight: FontWeight.bold)),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: AppColors.warning
                                          .withValues(alpha: 0.1),
                                      borderRadius:
                                          BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      o['status_label'] ?? '',
                                      style: const TextStyle(
                                          fontSize: 10,
                                          color: AppColors.warning),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                  'Pembeli: ${o['pembeli_nama'] ?? ''}',
                                  style: const TextStyle(fontSize: 12)),
                              Text(
                                'Total: ${((o['total_harga'] as num?) ?? 0).toInt().toCurrencyRp}',
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold),
                              ),
                              if (status == 'menunggu') ...[
                                const SizedBox(height: 8),
                                SizedBox(
                                  width: double.infinity,
                                  child: ElevatedButton(
                                    onPressed: () =>
                                        _updateStatus(o['id'], 'diproses'),
                                    child: const Text('PROSES PESANAN'),
                                  ),
                                ),
                              ],
                              if (status == 'diproses') ...[
                                const SizedBox(height: 8),
                                SizedBox(
                                  width: double.infinity,
                                  child: OutlinedButton(
                                    onPressed: () =>
                                        _updateStatus(o['id'], 'dikirim'),
                                    child: const Text('KIRIM PESANAN'),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}
