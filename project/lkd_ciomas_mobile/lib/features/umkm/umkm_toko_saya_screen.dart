import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';

class UmkmTokoSayaScreen extends ConsumerStatefulWidget {
  const UmkmTokoSayaScreen({super.key});

  @override
  ConsumerState<UmkmTokoSayaScreen> createState() =>
      _UmkmTokoSayaScreenState();
}

class _UmkmTokoSayaScreenState extends ConsumerState<UmkmTokoSayaScreen> {
  Map<String, dynamic>? _penjual;
  List<Map<String, dynamic>> _produkList = [];
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
      // Check seller status
      final statusRes = await api.get(ApiEndpoints.umkmPenjualStatus);
      final statusData = statusRes.data['data'];
      if (statusData['terdaftar'] == true) {
        _penjual = statusData;
        // Load products
        final prodRes = await api.get(ApiEndpoints.umkmProduk,
            params: {'page': 1, 'per_page': 50, 'penjual_id': statusData['id']});
        _produkList = List<Map<String, dynamic>>.from(
            prodRes.data['data']?['list'] ?? []);
      }
    } catch (_) {}
    setState(() => _loading = false);
  }

  Future<void> _tambahProduk() async {
    // Simple dialog
    final namaCtl = TextEditingController();
    final hargaCtl = TextEditingController();
    final stokCtl = TextEditingController(text: '1');
    String kategori = 'makanan';

    final result = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Tambah Produk'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: namaCtl, decoration: const InputDecoration(labelText: 'Nama Produk')),
              TextField(controller: hargaCtl, decoration: const InputDecoration(labelText: 'Harga'), keyboardType: TextInputType.number),
              TextField(controller: stokCtl, decoration: const InputDecoration(labelText: 'Stok'), keyboardType: TextInputType.number),
              DropdownButtonFormField<String>(
                initialValue: kategori,
                decoration: const InputDecoration(labelText: 'Kategori'),
                items: ['makanan', 'minuman', 'pakaian', 'pertanian', 'lainnya']
                    .map((k) => DropdownMenuItem(value: k, child: Text(k)))
                    .toList(),
                onChanged: (v) => kategori = v ?? 'makanan',
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Batal')),
          ElevatedButton(onPressed: () => Navigator.pop(c, true), child: const Text('Simpan')),
        ],
      ),
    );

    if (result == true) {
      final api = ref.read(apiClientProvider);
      try {
        await api.post(ApiEndpoints.umkmProduk, data: {
          'nama_produk': namaCtl.text,
          'harga': int.tryParse(hargaCtl.text) ?? 0,
          'stok': int.tryParse(stokCtl.text) ?? 1,
          'kategori': kategori,
        });
        if (mounted) _load();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Gagal: $e'), backgroundColor: AppColors.error),
          );
        }
      }
    }
  }

  Future<void> _deleteProduk(int produkId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Hapus Produk'),
        content: const Text('Yakin ingin menonaktifkan produk ini?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Batal')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Hapus')),
        ],
      ),
    );
    if (confirm != true) return;
    final api = ref.read(apiClientProvider);
    try {
      await api.delete(ApiEndpoints.umkmProdukDetail(produkId));
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
      appBar: AppBar(title: const Text('Toko Saya')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _penjual == null
              ? ListView(
                  children: const [
                    SizedBox(height: 80),
                    Center(
                      child: Column(
                        children: [
                          Icon(Icons.store, size: 64,
                              color: AppColors.disabled),
                          SizedBox(height: 16),
                          Text('Anda belum terdaftar sebagai penjual',
                              style: TextStyle(
                                  color: AppColors.textSecondary)),
                        ],
                      ),
                    ),
                  ],
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(_penjual!['nama_usaha'] ?? '',
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 18)),
                            Text('Status: ${_penjual!['status_label'] ?? ''}',
                                style: const TextStyle(
                                    color: AppColors.textSecondary)),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        const Text('Produk Saya',
                            style: TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 16)),
                        const Spacer(),
                        IconButton(
                          icon: const Icon(Icons.add_circle,
                              color: AppColors.primary),
                          onPressed: _tambahProduk,
                        ),
                      ],
                    ),
                    if (_produkList.isEmpty)
                      const Card(
                          child: Padding(
                              padding: EdgeInsets.all(24),
                              child: Center(
                                  child: Text('Belum ada produk'))))
                    else
                      ..._produkList.map((p) => Card(
                            margin: const EdgeInsets.symmetric(vertical: 2),
                            child: ListTile(
                              dense: true,
                              title: Text(p['nama_produk'] ?? ''),
                              subtitle: Text(
                                  '${((p['harga'] as num?)?.toInt() ?? 0).toCurrencyRp} · Stok: ${p['stok']}'),
                              trailing: IconButton(
                                icon: Icon(Icons.delete_outline,
                                    color: AppColors.error),
                                onPressed: () => _deleteProduk(p['id']),
                              ),
                            ),
                          )),
                  ],
                ),
      floatingActionButton: _penjual != null
          ? FloatingActionButton(
              onPressed: _tambahProduk,
              child: const Icon(Icons.add),
            )
          : null,
    );
  }
}
