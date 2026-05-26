import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_repository.dart';

class ChangePasswordScreen extends ConsumerStatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  ConsumerState<ChangePasswordScreen> createState() =>
      _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends ConsumerState<ChangePasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _oldCtl = TextEditingController();
  final _newCtl = TextEditingController();
  final _confirmCtl = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _oldCtl.dispose();
    _newCtl.dispose();
    _confirmCtl.dispose();
    super.dispose();
  }

  Future<void> _change() async {
    if (!_formKey.currentState!.validate()) return;
    if (_newCtl.text != _confirmCtl.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Konfirmasi password tidak cocok'),
            backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _loading = true);
    final error = await ref
        .read(authProvider.notifier)
        .changePassword(_oldCtl.text, _newCtl.text);
    setState(() => _loading = false);

    if (mounted) {
      if (error == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Password berhasil diubah'),
              backgroundColor: AppColors.success),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error), backgroundColor: AppColors.error),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ganti Password')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              TextFormField(
                controller: _oldCtl,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password Lama'),
                validator: (v) =>
                    v == null || v.isEmpty ? 'Password lama wajib diisi' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _newCtl,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password Baru'),
                validator: (v) =>
                    v == null || v.length < 6 ? 'Minimal 6 karakter' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _confirmCtl,
                obscureText: true,
                decoration:
                    const InputDecoration(labelText: 'Konfirmasi Password Baru'),
                validator: (v) => v == null || v.isEmpty
                    ? 'Konfirmasi password wajib diisi'
                    : null,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: _loading ? null : _change,
                  child: _loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : const Text('SIMPAN'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
