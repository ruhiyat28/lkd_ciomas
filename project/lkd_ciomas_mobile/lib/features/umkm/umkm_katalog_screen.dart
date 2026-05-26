import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';

class UmkmKatalogScreen extends ConsumerStatefulWidget {
  const UmkmKatalogScreen({super.key});

  @override
  ConsumerState<UmkmKatalogScreen> createState() => _UmkmKatalogScreenState();
}

class _UmkmKatalogScreenState extends ConsumerState<UmkmKatalogScreen> {
  List<Map<String, dynamic>> _produkList = [];
  bool _loading = true;
  bool _isSeller = false;
  String _sellerStatus = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = ref.read(apiClientProvider);
    try {
      final res = await api.get(ApiEndpoints.umkmProduk,
          params: {'page': 1, 'per_page': 50});
      _produkList = List<Map<String, dynamic>>.from(
          res.data['data']?['list'] ?? []);
    } catch (_) {}

    // Check seller status (only meaningful for nasabah)
    try {
      final statusRes = await api.get(ApiEndpoints.umkmPenjualStatus);
      final d = statusRes.data['data'];
      _isSeller = (d?['terdaftar'] == true) &&
          (d?['status'] == 'aktif' || d?['status'] == 'disetujui');
      _sellerStatus = d?['status'] as String? ?? '';
    } catch (_) {
      _isSeller = false;
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final isNasabah = auth.user?.isNasabah == true;

    return Scaffold(
      appBar: AppBar(
        title: const Text('UMKM Katalog'),
        actions: [
          if (isNasabah && !_isSeller && _sellerStatus != 'menunggu')
            IconButton(
              tooltip: 'Daftar Penjual',
              icon: const Icon(Icons.add_business),
              onPressed: () => context.push('/umkm/daftar-penjual'),
            ),
          if (_isSeller)
            PopupMenuButton<String>(
              itemBuilder: (_) => const [
                PopupMenuItem(
                    value: 'toko',
                    child: ListTile(
                      leading: Icon(Icons.store),
                      title: Text('Toko Saya'),
                    )),
                PopupMenuItem(
                    value: 'pesanan',
                    child: ListTile(
                      leading: Icon(Icons.receipt_long),
                      title: Text('Pesanan Saya'),
                    )),
                PopupMenuItem(
                    value: 'masuk',
                    child: ListTile(
                      leading: Icon(Icons.inbox),
                      title: Text('Pesanan Masuk'),
                    )),
              ],
              onSelected: (v) {
                if (v == 'toko') context.push('/umkm/toko-saya');
                if (v == 'pesanan') context.push('/umkm/pesanan-saya');
                if (v == 'masuk') context.push('/umkm/pesanan-masuk');
              },
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _produkList.isEmpty
                ? ListView(
                    children: const [
                      SizedBox(height: 80),
                      Center(
                        child: Column(
                          children: [
                            Icon(Icons.store, size: 64,
                                color: AppColors.disabled),
                            SizedBox(height: 16),
                            Text('Belum ada produk UMKM',
                                style: TextStyle(
                                    color: AppColors.textSecondary)),
                          ],
                        ),
                      ),
                    ],
                  )
                : GridView.builder(
                    padding: const EdgeInsets.all(8),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      childAspectRatio: 0.7,
                      crossAxisSpacing: 8,
                      mainAxisSpacing: 8,
                    ),
                    itemCount: _produkList.length,
                    itemBuilder: (_, i) {
                      final p = _produkList[i];
                      return Card(
                        clipBehavior: Clip.antiAlias,
                        child: InkWell(
                          onTap: () => context.push('/umkm/produk/${p['id']}'),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Gambar placeholder
                              Container(
                                height: 100,
                                color: AppColors.primaryLight.withValues(alpha: 0.1),
                                child: Center(
                                  child: p['gambar'] != null
                                      ? Image.network(
                                          '${ApiEndpoints.baseUrl}${ApiEndpoints.media(p['gambar'])}',
                                          fit: BoxFit.cover,
                                          width: double.infinity,
                                          height: double.infinity,
                                          errorBuilder: (_, __, ___) =>
                                              const Icon(Icons.image,
                                                  size: 40,
                                                  color: AppColors.disabled),
                                        )
                                      : const Icon(Icons.image,
                                          size: 40,
                                          color: AppColors.disabled),
                                ),
                              ),
                              Padding(
                                padding: const EdgeInsets.all(8),
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      p['nama_produk'] ?? '',
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      ((p['harga'] as num?) ?? 0).toInt().toCurrencyRp,
                                      style: const TextStyle(
                                        color: AppColors.primary,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                      ),
                                    ),
                                    Text(
                                      '${p['nama_penjual'] ?? ''} · ${p['desa'] ?? ''}',
                                      style: const TextStyle(
                                          fontSize: 10,
                                          color: AppColors.textSecondary),
                                    ),
                                  ],
                                ),
                              ),
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
