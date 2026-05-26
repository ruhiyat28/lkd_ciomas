import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/utils/validators.dart';
import 'config_provider.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameCtl = TextEditingController();
  final _namaCtl = TextEditingController();
  final _passwordCtl = TextEditingController();
  final _nikCtl = TextEditingController();
  final _noHpCtl = TextEditingController();
  final _alamatCtl = TextEditingController();
  final _tempatLahirCtl = TextEditingController();
  final _pekerjaanCtl = TextEditingController();
  final _namaPasanganCtl = TextEditingController();

  String _kodeDesa = '';
  String? _jenisKelamin;
  String? _tanggalLahir;
  bool _loading = false;
  bool _obscure = true;

  @override
  void dispose() {
    _usernameCtl.dispose();
    _namaCtl.dispose();
    _passwordCtl.dispose();
    _nikCtl.dispose();
    _noHpCtl.dispose();
    _alamatCtl.dispose();
    _tempatLahirCtl.dispose();
    _pekerjaanCtl.dispose();
    _namaPasanganCtl.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);

    final error = await ref.read(authProvider.notifier).register(
          username: _usernameCtl.text.trim(),
          nama: _namaCtl.text.trim(),
          password: _passwordCtl.text,
          nik: _nikCtl.text.trim(),
          noHp: _noHpCtl.text.trim(),
          kodeDesa: _kodeDesa,
          alamat: _alamatCtl.text,
          tempatLahir: _tempatLahirCtl.text,
          tanggalLahir: _tanggalLahir,
          jenisKelamin: _jenisKelamin,
          pekerjaan: _pekerjaanCtl.text,
          namaPasangan: _namaPasanganCtl.text,
        );

    setState(() => _loading = false);

    if (mounted) {
      if (error == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Pendaftaran berhasil! Silakan login.'),
            backgroundColor: AppColors.success,
          ),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error), backgroundColor: AppColors.error),
        );
      }
    }
  }

  final _fallbackDesa = [
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
  Widget build(BuildContext context) {
    final config = ref.watch(configProvider);
    final desaList = config?.desaList ?? _fallbackDesa;
    if (_kodeDesa.isEmpty && desaList.isNotEmpty) {
      _kodeDesa = (desaList.first['kode'] as String?) ?? '';
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Daftar Nasabah')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Data Akun',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              TextFormField(
                controller: _usernameCtl,
                decoration: const InputDecoration(labelText: 'Username *'),
                validator: Validators.username,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _passwordCtl,
                obscureText: _obscure,
                decoration: InputDecoration(
                  labelText: 'Password *',
                  suffixIcon: IconButton(
                    icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                validator: Validators.password,
              ),

              const SizedBox(height: 24),
              const Text('Data Pribadi',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              TextFormField(
                controller: _namaCtl,
                decoration: const InputDecoration(labelText: 'Nama Lengkap *'),
                validator: (v) => Validators.required(v, 'Nama'),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _nikCtl,
                decoration: const InputDecoration(labelText: 'NIK (16 digit) *'),
                keyboardType: TextInputType.number,
                maxLength: 17,
                validator: Validators.nik,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _noHpCtl,
                decoration: const InputDecoration(labelText: 'No. HP'),
                keyboardType: TextInputType.phone,
                validator: Validators.noHp,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _kodeDesa,
                decoration: const InputDecoration(labelText: 'Desa *'),
                items: desaList
                    .map((d) => DropdownMenuItem(
                          value: d['kode'],
                          child: Text('${d['kode']} — ${d['nama']}'),
                        ))
                    .toList(),
                onChanged: (v) => setState(() => _kodeDesa = v ?? ''),
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
                decoration: const InputDecoration(labelText: 'Tempat Lahir'),
              ),
              const SizedBox(height: 12),
              InkWell(
                onTap: () => _pickDate(context),
                child: InputDecorator(
                  decoration: const InputDecoration(
                    labelText: 'Tanggal Lahir',
                    suffixIcon: Icon(Icons.calendar_today),
                  ),
                  child: Text(_tanggalLahir ?? 'Pilih tanggal'),
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _jenisKelamin,
                decoration: const InputDecoration(labelText: 'Jenis Kelamin'),
                items: const [
                  DropdownMenuItem(value: 'L', child: Text('Laki-laki')),
                  DropdownMenuItem(value: 'P', child: Text('Perempuan')),
                ],
                onChanged: (v) => setState(() => _jenisKelamin = v),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _pekerjaanCtl,
                decoration: const InputDecoration(labelText: 'Pekerjaan'),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _namaPasanganCtl,
                decoration: const InputDecoration(labelText: 'Nama Pasangan'),
              ),

              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: _loading ? null : _register,
                  child: _loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : const Text('DAFTAR',
                          style: TextStyle(fontSize: 16)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _pickDate(BuildContext context) async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime.now().subtract(const Duration(days: 365 * 20)),
      firstDate: DateTime(1945),
      lastDate: DateTime.now(),
    );
    if (date != null) {
      setState(() => _tanggalLahir =
          '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}');
    }
  }
}
