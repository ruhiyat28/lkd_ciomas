import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';

class TabunganSetorScreen extends ConsumerStatefulWidget {
  final bool isTarik;
  const TabunganSetorScreen({super.key, this.isTarik = false});

  @override
  ConsumerState<TabunganSetorScreen> createState() => _TabunganSetorScreenState();
}

class _TabunganSetorScreenState extends ConsumerState<TabunganSetorScreen> {
  final _formKey = GlobalKey<FormState>();
  final _jumlahCtl = TextEditingController();
  final _ketCtl = TextEditingController();
  int? _nasabahId;
  String _kategori = 'sukarela';
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    final nasabah = ref.read(authProvider).nasabah;
    if (nasabah != null) _nasabahId = nasabah.id;
  }

  @override
  void dispose() {
    _jumlahCtl.dispose();
    _ketCtl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_nasabahId == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Tidak ada data nasabah'),
              backgroundColor: AppColors.error),
        );
      }
      return;
    }
    final jumlah =
        int.tryParse(_jumlahCtl.text.replaceAll(RegExp(r'[^0-9]'), ''));
    if (jumlah == null || jumlah <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Jumlah tidak valid'),
            backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _loading = true);
    final api = ref.read(apiClientProvider);
    try {
      final endpoint = widget.isTarik ? ApiEndpoints.tabunganTarik : ApiEndpoints.tabunganSetor;
      await api.post(endpoint, data: {
        'nasabah_id': _nasabahId,
        'kategori': _kategori,
        'jumlah': jumlah,
        'keterangan': _ketCtl.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('${widget.isTarik ? "Penarikan" : "Setoran"} $_kategori berhasil'),
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
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.isTarik ? 'Tarik Tabungan' : 'Setor Tabungan')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DropdownButtonFormField<String>(
                value: _kategori,
                decoration: const InputDecoration(labelText: 'Kategori'),
                items: const [
                  DropdownMenuItem(value: 'pokok', child: Text('Pokok')),
                  DropdownMenuItem(value: 'wajib', child: Text('Wajib')),
                  DropdownMenuItem(value: 'sukarela', child: Text('Sukarela')),
                ],
                onChanged: (v) => setState(() => _kategori = v ?? 'sukarela'),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _jumlahCtl,
                decoration: const InputDecoration(
                  labelText: 'Jumlah (Rp)',
                  prefixIcon: Icon(Icons.monetization_on),
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _ketCtl,
                decoration: const InputDecoration(
                  labelText: 'Keterangan',
                  prefixIcon: Icon(Icons.notes),
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : Text(widget.isTarik ? 'SIMPAN PENARIKAN' : 'SIMPAN SETORAN'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}


