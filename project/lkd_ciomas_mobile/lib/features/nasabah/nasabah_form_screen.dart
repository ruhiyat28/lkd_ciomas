import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../features/auth/config_provider.dart';

class NasabahFormScreen extends ConsumerStatefulWidget {
  final int? id;
  const NasabahFormScreen({super.key, this.id});

  @override
  ConsumerState<NasabahFormScreen> createState() => _NasabahFormScreenState();
}

class _NasabahFormScreenState extends ConsumerState<NasabahFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _namaCtl = TextEditingController();
  final _nikCtl = TextEditingController();
  final _noHpCtl = TextEditingController();
  final _alamatCtl = TextEditingController();
  final _tempatLahirCtl = TextEditingController();
  final _pekerjaanCtl = TextEditingController();
  final _namaPasanganCtl = TextEditingController();
  final _nikPasanganCtl = TextEditingController();
  final _ketJaminanCtl = TextEditingController();

  String _kodeDesa = '';
  String? _jenisKelamin;
  String? _tanggalLahir;
  bool _loading = false;
  bool _isEdit = false;
  bool _loadingDetail = false;

  static const _fallbackDesa = [
    {'kode': 'UT', 'nama': 'UJUNG TEBU'},
    {'kode': 'CS', 'nama': 'CISITU'},
    {'kode': 'SK', 'nama': 'SIKETUG'},
    {'kode': 'LB', 'nama': 'LEBAK'},
    {'kode': 'CM', 'nama': 'CITAMAN'},
    {'kode': 'PK', 'nama': 'PONDOK KAHURU'},
    {'kode': 'SB', 'nama': 'SUKABARES'},
    {'kode': 'SD', 'nama': 'SUKADANA'},
    {'kode': 'SR', 'nama': 'SUKARENA'},
    {'kode': 'CP', 'nama': 'CEMPLANG'},
    {'kode': 'PJ', 'nama': 'PANYAUNGAN JAYA'},
  ];

  @override
  void initState() {
    super.initState();
    _isEdit = widget.id != null;
    if (_isEdit) _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _loadingDetail = true);
    final api = ref.read(apiClientProvider);
    try {
      final res = await api.get(ApiEndpoints.nasabahDetail(widget.id!));
      final n = res.data['data'];
      _namaCtl.text = n['nama'] ?? '';
      _nikCtl.text = n['nik'] ?? '';
      _noHpCtl.text = n['no_hp'] ?? '';
      _alamatCtl.text = n['alamat'] ?? '';
      _tempatLahirCtl.text = n['tempat_lahir'] ?? '';
      _pekerjaanCtl.text = n['pekerjaan'] ?? '';
      _namaPasanganCtl.text = n['nama_pasangan'] ?? '';
      _nikPasanganCtl.text = n['nik_pasangan'] ?? '';
      _ketJaminanCtl.text = n['keterangan_jaminan'] ?? '';
      _kodeDesa = n['kode_desa'] ?? '';
      _jenisKelamin = n['jenis_kelamin'];
      _tanggalLahir = n['tanggal_lahir'];
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Gagal memuat data nasabah'),
              backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _loadingDetail = false);
    }
  }

  @override
  void dispose() {
    _namaCtl.dispose();
    _nikCtl.dispose();
    _noHpCtl.dispose();
    _alamatCtl.dispose();
    _tempatLahirCtl.dispose();
    _pekerjaanCtl.dispose();
    _namaPasanganCtl.dispose();
    _nikPasanganCtl.dispose();
    _ketJaminanCtl.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final initial = DateTime.tryParse(_tanggalLahir ?? '') ??
        DateTime.now().subtract(const Duration(days: 365 * 25));
    final date = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(1945),
      lastDate: DateTime.now(),
    );
    if (date != null) {
      setState(() => _tanggalLahir =
          '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}');
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_isEdit && _kodeDesa.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Desa wajib dipilih'),
            backgroundColor: AppColors.error),
      );
      return;
    }
    setState(() => _loading = true);

    final api = ref.read(apiClientProvider);
    final data = <String, dynamic>{
      'nama': _namaCtl.text,
      'nik': _nikCtl.text,
      'no_hp': _noHpCtl.text,
      'alamat': _alamatCtl.text,
      'tempat_lahir': _tempatLahirCtl.text,
      'pekerjaan': _pekerjaanCtl.text,
      'nama_pasangan': _namaPasanganCtl.text,
      'nik_pasangan': _nikPasanganCtl.text,
      'keterangan_jaminan': _ketJaminanCtl.text,
      if (_kodeDesa.isNotEmpty) 'kode_desa': _kodeDesa,
      if (_jenisKelamin != null) 'jenis_kelamin': _jenisKelamin,
      if (_tanggalLahir != null) 'tanggal_lahir': _tanggalLahir,
    };

    try {
      if (_isEdit) {
        await api.put(ApiEndpoints.nasabahDetail(widget.id!), data: data);
      } else {
        await api.post(ApiEndpoints.nasabah, data: data);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_isEdit ? 'Data diperbarui' : 'Nasabah ditambahkan'),
            backgroundColor: AppColors.success,
          ),
        );
        context.pop();
      }
    } on DioException catch (e) {
      if (mounted) {
        final msg = e.response?.data?['message'] as String? ?? 'Gagal menyimpan';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg), backgroundColor: AppColors.error),
        );
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
    final config = ref.watch(configProvider);
    final desaList = config?.desaList ?? _fallbackDesa;
    final currentValue = desaList.any((d) => d['kode'] == _kodeDesa)
        ? _kodeDesa
        : null;

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEdit ? 'Edit Nasabah' : 'Tambah Nasabah'),
      ),
      body: _loadingDetail
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextFormField(
                      controller: _namaCtl,
                      decoration:
                          const InputDecoration(labelText: 'Nama Lengkap *'),
                      validator: (v) => v == null || v.trim().isEmpty
                          ? 'Nama wajib diisi'
                          : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _nikCtl,
                      decoration: const InputDecoration(
                          labelText: 'NIK (16 digit) *'),
                      keyboardType: TextInputType.number,
                      maxLength: 17,
                      validator: (v) {
                        final s = v?.trim() ?? '';
                        if (s.isEmpty) return 'NIK wajib diisi';
                        if (!RegExp(r'^\d{16}$').hasMatch(s)) {
                          return 'NIK harus 16 digit angka';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 4),
                    DropdownButtonFormField<String>(
                      initialValue: currentValue,
                      decoration:
                          const InputDecoration(labelText: 'Desa *'),
                      items: desaList
                          .map((d) => DropdownMenuItem(
                                value: d['kode'],
                                child:
                                    Text('${d['kode']} — ${d['nama']}'),
                              ))
                          .toList(),
                      onChanged: (v) => setState(() => _kodeDesa = v ?? ''),
                      validator: (v) =>
                          (v == null || v.isEmpty) ? 'Desa wajib dipilih' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _noHpCtl,
                      decoration: const InputDecoration(labelText: 'No. HP'),
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _alamatCtl,
                      decoration: const InputDecoration(labelText: 'Alamat'),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _tempatLahirCtl,
                      decoration:
                          const InputDecoration(labelText: 'Tempat Lahir'),
                    ),
                    const SizedBox(height: 12),
                    InkWell(
                      onTap: _pickDate,
                      child: InputDecorator(
                        decoration: const InputDecoration(
                          labelText: 'Tanggal Lahir',
                          suffixIcon: Icon(Icons.calendar_today),
                        ),
                        child: Text(_tanggalLahir ?? 'Pilih tanggal',
                            style: TextStyle(
                                color: _tanggalLahir == null
                                    ? AppColors.textHint
                                    : AppColors.textPrimary)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: _jenisKelamin,
                      decoration: const InputDecoration(
                          labelText: 'Jenis Kelamin'),
                      items: const [
                        DropdownMenuItem(value: 'L', child: Text('Laki-laki')),
                        DropdownMenuItem(value: 'P', child: Text('Perempuan')),
                      ],
                      onChanged: (v) => setState(() => _jenisKelamin = v),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _pekerjaanCtl,
                      decoration:
                          const InputDecoration(labelText: 'Pekerjaan'),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _namaPasanganCtl,
                      decoration:
                          const InputDecoration(labelText: 'Nama Pasangan'),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _nikPasanganCtl,
                      decoration:
                          const InputDecoration(labelText: 'NIK Pasangan'),
                      keyboardType: TextInputType.number,
                      maxLength: 17,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _ketJaminanCtl,
                      decoration: const InputDecoration(
                          labelText: 'Keterangan Jaminan'),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: ElevatedButton(
                        onPressed: _loading ? null : _save,
                        child: _loading
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white))
                            : Text(_isEdit ? 'SIMPAN PERUBAHAN' : 'SIMPAN'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
