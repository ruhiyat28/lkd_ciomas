import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/pinjaman.dart';

class VerifikasiFormScreen extends ConsumerStatefulWidget {
  final int id;
  const VerifikasiFormScreen({super.key, required this.id});

  @override
  ConsumerState<VerifikasiFormScreen> createState() =>
      _VerifikasiFormScreenState();
}

class _VerifikasiFormScreenState extends ConsumerState<VerifikasiFormScreen> {
  Pinjaman? _pinjaman;
  bool _loading = true;
  bool _submitting = false;
  String? _rekomendasi;
  final _catatanCtl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = ref.read(apiClientProvider);
    try {
      final res = await api.get(ApiEndpoints.pinjamanDetail(widget.id));
      setState(() {
        _pinjaman = Pinjaman.fromJson(res.data['data']);
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _submit() async {
    if (_rekomendasi == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Pilih rekomendasi'),
            backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _submitting = true);
    final api = ref.read(apiClientProvider);
    try {
      await api.put(ApiEndpoints.verifikasiPinjaman(widget.id), data: {
        'rekomendasi': _rekomendasi,
        'catatan': _catatanCtl.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Verifikasi berhasil disimpan'),
              backgroundColor: AppColors.success),
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
    _catatanCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Form Verifikasi')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _pinjaman == null
              ? const Center(child: Text('Pinjaman tidak ditemukan'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Info pinjaman
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_pinjaman!.spk,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 18)),
                              const SizedBox(height: 8),
                              _info('Nasabah', _pinjaman!.nasabah),
                              _info(
                                  'Jumlah', _pinjaman!.jumlahPinjaman.toCurrencyRp),
                              _info('Tenor', '${_pinjaman!.tenor} bulan'),
                              _info('Jasa', '${_pinjaman!.jasaPersen}%'),
                              _info(
                                  'Tanggal Pengajuan',
                                  formatDateApi(
                                      _pinjaman!.tanggalPengajuan)),
                              if (_pinjaman!.tujuan != null &&
                                  _pinjaman!.tujuan!.isNotEmpty)
                                _info('Tujuan', _pinjaman!.tujuan!),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 16),

                      const Text('Rekomendasi Verifikasi',
                          style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: ChoiceChip(
                              label: const Text('Layak'),
                              avatar: Icon(Icons.check_circle_rounded,
                                  size: 18,
                                  color: _rekomendasi == 'layak'
                                      ? AppColors.success
                                      : AppColors.textSecondary),
                              selected: _rekomendasi == 'layak',
                              selectedColor:
                                  AppColors.success.withValues(alpha: 0.18),
                              onSelected: (_) =>
                                  setState(() => _rekomendasi = 'layak'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: ChoiceChip(
                              label: const Text('Tidak Layak'),
                              avatar: Icon(Icons.cancel_rounded,
                                  size: 18,
                                  color: _rekomendasi == 'tidak_layak'
                                      ? AppColors.error
                                      : AppColors.textSecondary),
                              selected: _rekomendasi == 'tidak_layak',
                              selectedColor:
                                  AppColors.error.withValues(alpha: 0.18),
                              onSelected: (_) => setState(
                                  () => _rekomendasi = 'tidak_layak'),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _catatanCtl,
                        decoration: const InputDecoration(
                          labelText: 'Catatan Verifikasi',
                          hintText: 'Hasil kunjungan, kondisi jaminan, dll',
                        ),
                        maxLines: 4,
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
                              : const Text('SIMPAN VERIFIKASI'),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _info(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
              width: 120,
              child: Text(label,
                  style: const TextStyle(color: AppColors.textSecondary))),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
