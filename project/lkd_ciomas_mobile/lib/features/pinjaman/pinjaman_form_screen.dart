import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';

class PinjamanFormScreen extends ConsumerStatefulWidget {
  const PinjamanFormScreen({super.key});

  @override
  ConsumerState<PinjamanFormScreen> createState() => _PinjamanFormScreenState();
}

class _PinjamanFormScreenState extends ConsumerState<PinjamanFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _jumlahCtl = TextEditingController();
  final _tujuanCtl = TextEditingController();
  final _nasabahCtl = TextEditingController();
  int _tenor = 12;
  double _jasaPersen = 1.5;
  bool _loading = false;

  // Nasabah search
  List<Map<String, dynamic>> _nasabahResults = [];
  bool _searchingNasabah = false;
  Map<String, dynamic>? _selectedNasabah;
  Timer? _searchDebounce;

  // Kalkulasi
  int? _pokok;
  int? _jasa;
  int? _total;
  int? _pokokTerakhir;
  int? _totalTerakhir;

  final _tenorOptions = [3, 6, 10, 12, 18, 24, 36];

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _jumlahCtl.dispose();
    _tujuanCtl.dispose();
    _nasabahCtl.dispose();
    super.dispose();
  }

  void _onNasabahSearch(String v) {
    setState(() => _selectedNasabah = null);
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (v.length >= 2) _searchNasabah(v);
    });
  }

  Future<void> _searchNasabah(String q) async {
    if (q.length < 2) return;
    setState(() => _searchingNasabah = true);
    final api = ref.read(apiClientProvider);
    try {
      final res = await api.get(ApiEndpoints.nasabah,
          params: {'q': q, 'page': 1, 'per_page': 10});
      _nasabahResults =
          List<Map<String, dynamic>>.from(res.data['data'] ?? []);
    } catch (_) {
      _nasabahResults = [];
    }
    setState(() => _searchingNasabah = false);
  }

  Future<void> _hitung() async {
    final jumlah =
        int.tryParse(_jumlahCtl.text.replaceAll(RegExp(r'[^0-9]'), ''));
    if (jumlah == null || jumlah <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Masukkan jumlah pinjaman'),
            backgroundColor: AppColors.error),
      );
      return;
    }

    final api = ref.read(apiClientProvider);
    try {
      final res = await api.post(ApiEndpoints.hitungAngsuran, data: {
        'jumlah': jumlah,
        'tenor': _tenor,
        'jasa_persen': _jasaPersen,
      });
      final d = res.data['data'];
      setState(() {
        _pokok = d['pokok'] as int;
        _jasa = d['jasa'] as int;
        _total = d['total'] as int;
        _pokokTerakhir = d['pokok_terakhir'] as int;
        _totalTerakhir = d['total_terakhir'] as int;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Gagal hitung: $e'),
              backgroundColor: AppColors.error),
        );
      }
    }
  }

  Future<void> _ajukan() async {
    if (!_formKey.currentState!.validate()) return;

    final user = ref.read(authProvider).user;
    final isStaff = user != null && !user.isNasabah;

    if (isStaff && _selectedNasabah == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Pilih nasabah terlebih dahulu'),
            backgroundColor: AppColors.error),
      );
      return;
    }

    final jumlah =
        int.tryParse(_jumlahCtl.text.replaceAll(RegExp(r'[^0-9]'), ''));
    if (jumlah == null || jumlah <= 0) return;

    setState(() => _loading = true);
    final api = ref.read(apiClientProvider);
    try {
      final data = <String, dynamic>{
        'jumlah': jumlah,
        'tenor': _tenor,
        'jasa_persen': _jasaPersen,
        'tujuan': _tujuanCtl.text,
      };
      if (isStaff && _selectedNasabah != null) {
        data['nasabah_id'] = _selectedNasabah!['id'];
      }
      await api.post(ApiEndpoints.pinjaman, data: data);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Pinjaman berhasil diajukan'),
              backgroundColor: AppColors.success),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Gagal: $e'),
              backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final user = auth.user;
    final isStaff = user != null && !user.isNasabah;

    return Scaffold(
      appBar: AppBar(title: const Text('Ajukan Pinjaman')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Cari Nasabah (hanya untuk staff)
              if (isStaff) ...[
                const Text('Pilih Nasabah',
                    style: TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 8),
                TextField(
                  controller: _nasabahCtl,
                  decoration: InputDecoration(
                    hintText: 'Cari nama/NIK nasabah...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _selectedNasabah != null
                        ? IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () {
                              setState(() {
                                _selectedNasabah = null;
                                _nasabahCtl.clear();
                                _nasabahResults = [];
                              });
                            },
                          )
                        : null,
                  ),
                  onChanged: _onNasabahSearch,
                ),
                if (_searchingNasabah)
                  const Padding(
                    padding: EdgeInsets.all(8),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                if (_nasabahResults.isNotEmpty && _selectedNasabah == null)
                  ..._nasabahResults.map((n) => Card(
                        margin: const EdgeInsets.symmetric(vertical: 2),
                        child: ListTile(
                          dense: true,
                          leading: CircleAvatar(
                            radius: 16,
                            backgroundColor: AppColors.primaryLight,
                            child: Text(
                              (n['nama'] as String? ?? '?')[0],
                              style:
                                  const TextStyle(color: Colors.white, fontSize: 12),
                            ),
                          ),
                          title: Text(n['nama'] ?? '',
                              style: const TextStyle(fontSize: 14)),
                          subtitle: Text(
                              '${n['nasabah_id'] ?? ''} · ${n['nama_desa'] ?? ''}',
                              style: const TextStyle(fontSize: 11)),
                          onTap: () {
                            setState(() {
                              _selectedNasabah = n;
                              _nasabahCtl.text = '${n['nama']} (${n['nasabah_id']})';
                              _nasabahResults = [];
                            });
                          },
                        ),
                      )),
                if (_selectedNasabah != null)
                  Card(
                    color: AppColors.success.withValues(alpha: 0.05),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle,
                              color: AppColors.success, size: 20),
                          const SizedBox(width: 8),
                          Text('Dipilih: ${_selectedNasabah!['nama']}',
                              style: const TextStyle(
                                  fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 16),
              ],

              TextFormField(
                controller: _jumlahCtl,
                decoration: const InputDecoration(
                  labelText: 'Jumlah Pinjaman (Rp)',
                  prefixIcon: Icon(Icons.monetization_on),
                ),
                keyboardType: TextInputType.number,
                onChanged: (_) {
                  setState(() {
                    _pokok = null;
                    _jasa = null;
                    _total = null;
                  });
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<int>(
                value: _tenor,
                decoration: const InputDecoration(
                  labelText: 'Tenor (bulan)',
                  prefixIcon: Icon(Icons.calendar_month),
                ),
                items: _tenorOptions
                    .map((t) =>
                        DropdownMenuItem(value: t, child: Text('$t bulan')))
                    .toList(),
                onChanged: (v) {
                  setState(() {
                    _tenor = v ?? 12;
                    _pokok = null;
                    _jasa = null;
                    _total = null;
                  });
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<double>(
                value: _jasaPersen,
                decoration: const InputDecoration(
                  labelText: 'Jasa (%)',
                  prefixIcon: Icon(Icons.percent),
                ),
                items: [1.0, 1.5, 2.0, 2.5, 3.0]
                    .map((p) =>
                        DropdownMenuItem(value: p, child: Text('$p%')))
                    .toList(),
                onChanged: (v) {
                  setState(() {
                    _jasaPersen = v ?? 1.5;
                    _pokok = null;
                    _jasa = null;
                    _total = null;
                  });
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _tujuanCtl,
                decoration: const InputDecoration(
                  labelText: 'Tujuan Pinjaman',
                  prefixIcon: Icon(Icons.edit_note),
                ),
                maxLines: 2,
              ),

              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _hitung,
                  icon: const Icon(Icons.calculate),
                  label: const Text('HITUNG ANGSURAN'),
                ),
              ),

              // Hasil Kalkulasi
              if (_pokok != null) ...[
                const SizedBox(height: 16),
                Card(
                  color: AppColors.primaryLight.withValues(alpha: 0.05),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Text('Simulasi Angsuran',
                            style: TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 16)),
                        const Divider(),
                        _row('Angsuran Pokok', _pokok!.toCurrencyRp),
                        _row('Angsuran Jasa', _jasa!.toCurrencyRp),
                        _row('Angsuran Total', _total!.toCurrencyRp,
                            bold: true),
                        const Divider(),
                        _row('Pokok Terakhir', _pokokTerakhir!.toCurrencyRp),
                        _row('Total Terakhir', _totalTerakhir!.toCurrencyRp),
                        const SizedBox(height: 16),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _loading ? null : _ajukan,
                            child: _loading
                                ? const SizedBox(
                                    height: 20,
                                    width: 20,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.white))
                                : const Text('AJUKAN PINJAMAN'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _row(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
              child: Text(label,
                  style: const TextStyle(color: AppColors.textSecondary))),
          Text(value,
              style: TextStyle(
                  fontWeight: bold ? FontWeight.bold : FontWeight.normal,
                  fontSize: bold ? 16 : 14)),
        ],
      ),
    );
  }
}
