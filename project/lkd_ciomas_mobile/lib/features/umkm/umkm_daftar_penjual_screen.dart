import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_endpoints.dart';

class UmkmDaftarPenjualScreen extends ConsumerStatefulWidget {
  const UmkmDaftarPenjualScreen({super.key});

  @override
  ConsumerState<UmkmDaftarPenjualScreen> createState() =>
      _UmkmDaftarPenjualScreenState();
}

class _UmkmDaftarPenjualScreenState
    extends ConsumerState<UmkmDaftarPenjualScreen> {
  final _formKey = GlobalKey<FormState>();
  final _namaUsahaCtl = TextEditingController();
  final _jenisUsahaCtl = TextEditingController();
  final _deskripsiCtl = TextEditingController();
  final _noHpCtl = TextEditingController();
  final _alamatCtl = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _namaUsahaCtl.dispose();
    _jenisUsahaCtl.dispose();
    _deskripsiCtl.dispose();
    _noHpCtl.dispose();
    _alamatCtl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    final api = ref.read(apiClientProvider);
    try {
      await api.post(ApiEndpoints.umkmPenjualDaftar, data: {
        'nama_usaha': _namaUsahaCtl.text,
        'jenis_usaha': _jenisUsahaCtl.text,
        'deskripsi': _deskripsiCtl.text,
        'no_hp_usaha': _noHpCtl.text,
        'alamat_usaha': _alamatCtl.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Pengajuan penjual berhasil dikirim!'),
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
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Daftar Penjual UMKM')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                  'Isi data usaha Anda untuk mendaftar sebagai penjual UMKM'),
              const SizedBox(height: 16),
              TextFormField(
                controller: _namaUsahaCtl,
                decoration: const InputDecoration(labelText: 'Nama Usaha *'),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Nama usaha wajib diisi' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _jenisUsahaCtl,
                decoration: const InputDecoration(labelText: 'Jenis Usaha *'),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Jenis usaha wajib diisi' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _deskripsiCtl,
                decoration: const InputDecoration(labelText: 'Deskripsi'),
                maxLines: 3,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _noHpCtl,
                decoration: const InputDecoration(labelText: 'No. HP Usaha'),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _alamatCtl,
                decoration: const InputDecoration(labelText: 'Alamat Usaha'),
                maxLines: 2,
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
                      : const Text('DAFTAR SEBAGAI PENJUAL'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
