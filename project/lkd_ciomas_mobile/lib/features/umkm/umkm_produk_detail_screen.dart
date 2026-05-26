import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';

class UmkmProdukDetailScreen extends ConsumerStatefulWidget {
  final int id;
  const UmkmProdukDetailScreen({super.key, required this.id});

  @override
  ConsumerState<UmkmProdukDetailScreen> createState() =>
      _UmkmProdukDetailScreenState();
}

class _UmkmProdukDetailScreenState extends ConsumerState<UmkmProdukDetailScreen> {
  Map<String, dynamic>? _produk;
  bool _loading = true;
  int _jumlah = 1;
  final _catatanCtl = TextEditingController();
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = ref.read(apiClientProvider);
    try {
      final res =
          await api.get(ApiEndpoints.umkmProdukDetail(widget.id));
      setState(() {
        _produk = res.data['data'];
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _order() async {
    setState(() => _submitting = true);
    final api = ref.read(apiClientProvider);
    try {
      await api.post(ApiEndpoints.umkmPesanan, data: {
        'penjual_id': _produk!['penjual_id'],
        'items': [
          {'produk_id': widget.id, 'jumlah': _jumlah},
        ],
        'catatan_pembeli': _catatanCtl.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Pesanan berhasil dibuat'),
              backgroundColor: AppColors.success),
        );
        context.push('/umkm/pesanan-saya');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Gagal: $e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  void dispose() {
    _catatanCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Detail Produk')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _produk == null
              ? const Center(child: Text('Produk tidak ditemukan'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Gambar
                      Container(
                        height: 200,
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: AppColors.primaryLight.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: _produk!['gambar'] != null
                            ? ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Image.network(
                                  '${ApiEndpoints.baseUrl}${ApiEndpoints.media(_produk!['gambar'])}',
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) =>
                                      const Icon(Icons.image, size: 64),
                                ),
                              )
                            : const Icon(Icons.image, size: 64),
                      ),

                      const SizedBox(height: 16),
                      Text(_produk!['nama_produk'] ?? '',
                          style: const TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 22)),
                      const SizedBox(height: 4),
                      Text(
                        ((_produk!['harga'] as num?) ?? 0).toInt().toCurrencyRp,
                        style: const TextStyle(
                            color: AppColors.primary,
                            fontSize: 20,
                            fontWeight: FontWeight.bold),
                      ),

                      const SizedBox(height: 12),
                      Row(
                        children: [
                          const Icon(Icons.store, size: 16,
                              color: AppColors.textSecondary),
                          const SizedBox(width: 4),
                          Text(_produk!['nama_penjual'] ?? '',
                              style: const TextStyle(
                                  color: AppColors.textSecondary)),
                          const Spacer(),
                          if ((_produk!['stok'] as int?) != null)
                            Text('Stok: ${_produk!['stok']}',
                                style: const TextStyle(fontSize: 12)),
                        ],
                      ),

                      const SizedBox(height: 16),
                      const Text('Deskripsi',
                          style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 4),
                      Text(_produk!['deskripsi'] ?? '-',
                          style: const TextStyle(
                              color: AppColors.textSecondary)),

                      const SizedBox(height: 24),
                      const Divider(),
                      const Text('Pesan',
                          style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Text('Jumlah: '),
                          IconButton(
                            icon: const Icon(Icons.remove_circle_outline),
                            onPressed: _jumlah > 1
                                ? () => setState(() => _jumlah--)
                                : null,
                          ),
                          Text('$_jumlah',
                              style: const TextStyle(fontSize: 18)),
                          IconButton(
                            icon: const Icon(Icons.add_circle_outline),
                            onPressed: () =>
                                setState(() => _jumlah++),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _catatanCtl,
                        decoration: const InputDecoration(
                          labelText: 'Catatan (opsional)',
                        ),
                      ),

                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: ElevatedButton(
                          onPressed: _submitting ? null : _order,
                          child: _submitting
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white))
                              : const Text('PESAN SEKARANG'),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}
