import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';

class UmkmPesananSayaScreen extends ConsumerStatefulWidget {
  const UmkmPesananSayaScreen({super.key});

  @override
  ConsumerState<UmkmPesananSayaScreen> createState() =>
      _UmkmPesananSayaScreenState();
}

class _UmkmPesananSayaScreenState extends ConsumerState<UmkmPesananSayaScreen> {
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
          params: {'page': 1, 'per_page': 50, 'role': 'pembeli'});
      _orders = List<Map<String, dynamic>>.from(
          res.data['data']?['list'] ?? []);
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pesanan Saya')),
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
                            Icon(Icons.receipt_long, size: 64,
                                color: AppColors.disabled),
                            SizedBox(height: 16),
                            Text('Belum ada pesanan',
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
                      return Card(
                        margin: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 4),
                        child: ListTile(
                          title: Text('${o['nomor_pesanan'] ?? ''}'),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Penjual: ${o['penjual_nama'] ?? ''}',
                                  style: const TextStyle(fontSize: 12)),
                              Text(
                                  'Total: ${((o['total_harga'] as num?)?.toInt() ?? 0).toCurrencyRp}',
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold)),
                              Text(
                                '${o['status_label'] ?? ''} · ${o['status_pembayaran_label'] ?? ''}',
                                style: const TextStyle(fontSize: 11),
                              ),
                            ],
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {}, // detail
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}
