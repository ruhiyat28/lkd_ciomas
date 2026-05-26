import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import 'package:geolocator/geolocator.dart';
import '../../core/theme/app_colors.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/pinjaman.dart';

class PenagihanBayarScreen extends ConsumerStatefulWidget {
  final int pinjamanId;
  const PenagihanBayarScreen({super.key, required this.pinjamanId});

  @override
  ConsumerState<PenagihanBayarScreen> createState() =>
      _PenagihanBayarScreenState();
}

class _PenagihanBayarScreenState extends ConsumerState<PenagihanBayarScreen> {
  Pinjaman? _pinjaman;
  bool _loading = true;
  bool _submitting = false;
  final _jumlahCtl = TextEditingController();
  final _ketCtl = TextEditingController();
  Position? _position;

  @override
  void initState() {
    super.initState();
    _load();
    _getLocation();
  }

  Future<void> _load() async {
    final api = ref.read(apiClientProvider);
    try {
      final res =
          await api.get(ApiEndpoints.pinjamanDetail(widget.pinjamanId));
      setState(() {
        _pinjaman = Pinjaman.fromJson(res.data['data']);
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _getLocation() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings:
            const LocationSettings(accuracy: LocationAccuracy.high),
      );
      if (mounted) setState(() => _position = pos);
    } catch (_) {}
  }

  Future<void> _submit() async {
    final jumlah = int.tryParse(_jumlahCtl.text.replaceAll(RegExp(r'[^0-9]'), ''));
    if (jumlah == null || jumlah <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Jumlah bayar tidak valid'),
            backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _submitting = true);
    final api = ref.read(apiClientProvider);
    try {
      await api.post(ApiEndpoints.pembayaran, data: {
        'pinjaman_id': widget.pinjamanId,
        'jumlah_bayar': jumlah,
        'keterangan': _ketCtl.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Pembayaran berhasil dicatat'),
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
    _jumlahCtl.dispose();
    _ketCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Catat Pembayaran')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _pinjaman == null
              ? const Center(child: Text('Data tidak ditemukan'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Info nasabah
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_pinjaman!.nasabah,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 18)),
                              const SizedBox(height: 4),
                              Text(_pinjaman!.spk,
                                  style: const TextStyle(
                                      color: AppColors.textSecondary)),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  Text('Sisa: ${(_pinjaman!.saldoPokok ?? 0).toCurrencyRp}',
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: AppColors.primary)),
                                  const Spacer(),
                                  if (_pinjaman!.angsuranTotal != null)
                                    Text('Angsuran: ${_pinjaman!.angsuranTotal!.toCurrencyRp}',
                                        style: const TextStyle(fontSize: 12)),
                                ],
                              ),
                              if (_pinjaman!.noHp != null &&
                                  _pinjaman!.noHp!.isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(Icons.phone, size: 14,
                                        color: AppColors.textSecondary),
                                    const SizedBox(width: 4),
                                    Text(_pinjaman!.noHp!,
                                        style: const TextStyle(fontSize: 12)),
                                  ],
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 16),

                      // GPS info
                      if (_position != null)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppColors.info.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.location_on,
                                  size: 16, color: AppColors.info),
                              const SizedBox(width: 8),
                              Text(
                                'Lokasi: ${_position!.latitude.toStringAsFixed(5)}, ${_position!.longitude.toStringAsFixed(5)}',
                                style: const TextStyle(fontSize: 11),
                              ),
                            ],
                          ),
                        ),

                      const SizedBox(height: 16),

                      // Input jumlah
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
                        child: ElevatedButton.icon(
                          onPressed: _submitting ? null : _submit,
                          icon: _submitting
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.save),
                          label: Text(
                              _submitting ? 'MENYIMPAN...' : 'SIMPAN PEMBAYARAN'),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}
