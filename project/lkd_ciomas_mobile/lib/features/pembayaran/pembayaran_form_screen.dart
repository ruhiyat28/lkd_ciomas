import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';

class PembayaranFormScreen extends ConsumerStatefulWidget {
  const PembayaranFormScreen({super.key});

  @override
  ConsumerState<PembayaranFormScreen> createState() => _PembayaranFormScreenState();
}

class _PembayaranFormScreenState extends ConsumerState<PembayaranFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _jumlahCtl = TextEditingController();
  final _ketCtl = TextEditingController();
  int? _pinjamanId;
  String _searchQuery = '';
  bool _loading = false;
  bool _submitting = false;

  // Search results
  List<Map<String, dynamic>> _searchResults = [];

  Future<void> _searchPinjaman(String q) async {
    if (q.length < 2) return;
    setState(() => _loading = true);
    final api = ref.read(apiClientProvider);
    try {
      final res = await api.get(ApiEndpoints.pinjaman,
          params: {'q': q, 'status': 'aktif', 'page': 1, 'per_page': 10});
      _searchResults = (res.data['data'] as List?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ?? [];
    } catch (_) {
      _searchResults = [];
    }
    setState(() => _loading = false);
  }

  Future<void> _submit() async {
    if (_pinjamanId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pilih pinjaman'), backgroundColor: AppColors.error),
      );
      return;
    }
    final jumlah = int.tryParse(_jumlahCtl.text.replaceAll(RegExp(r'[^0-9]'), ''));
    if (jumlah == null || jumlah <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Jumlah bayar tidak valid'), backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _submitting = true);
    final api = ref.read(apiClientProvider);
    try {
      await api.post(ApiEndpoints.pembayaran, data: {
        'pinjaman_id': _pinjamanId,
        'jumlah_bayar': jumlah,
        'keterangan': _ketCtl.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Pembayaran berhasil dicatat'), backgroundColor: AppColors.success),
        );
        context.pop();
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
    _jumlahCtl.dispose();
    _ketCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Catat Pembayaran')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Cari Pinjaman',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              TextField(
                decoration: const InputDecoration(
                  hintText: 'Cari SPK atau nama nasabah...',
                  prefixIcon: Icon(Icons.search),
                ),
                onChanged: (v) {
                  _searchQuery = v;
                  _searchPinjaman(v);
                },
              ),
              const SizedBox(height: 8),

              if (_loading)
                const Center(child: CircularProgressIndicator())
              else if (_searchResults.isNotEmpty)
                ..._searchResults.map((p) => Card(
                      margin: const EdgeInsets.symmetric(vertical: 2),
                      color: _pinjamanId == p['id']
                          ? AppColors.primaryLight.withValues(alpha: 0.1)
                          : null,
                      child: ListTile(
                        dense: true,
                        title: Text(p['spk'] ?? ''),
                        subtitle: Text(
                            '${p['nasabah'] ?? ''} · ${(p['saldo_pokok'] as int? ?? 0).toCurrencyRp}'),
                        trailing: _pinjamanId == p['id']
                            ? const Icon(Icons.check_circle, color: AppColors.success)
                            : null,
                        onTap: () => setState(() {
                          _pinjamanId = (p['id'] as num?)?.toInt();
                        }),
                      ),
                    )),

              if (_pinjamanId != null) ...[
                const SizedBox(height: 16),
                const Text('Detail Pembayaran',
                    style:
                        TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _jumlahCtl,
                  decoration: const InputDecoration(
                    labelText: 'Jumlah Bayar (Rp)',
                    prefixIcon: Icon(Icons.monetization_on),
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _ketCtl,
                  decoration: const InputDecoration(
                    labelText: 'Keterangan (opsional)',
                    prefixIcon: Icon(Icons.notes),
                  ),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: _submitting ? null : _submit,
                    child: _submitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Text('SIMPAN PEMBAYARAN'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
