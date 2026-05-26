import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../core/utils/date_format.dart';
import '../../models/tabungan.dart';

final tabunganProvider = FutureProvider<RekeningTabungan?>((ref) async {
  final api = ref.watch(apiClientProvider);
  final auth = ref.watch(authProvider);
  if (auth.nasabah == null) return null;
  try {
    final res = await api.get(ApiEndpoints.tabungan,
        params: {'nasabah_id': auth.nasabah!.id});
    return RekeningTabungan.fromJson(res.data['data']);
  } catch (e) {
    return null;
  }
});

class TabunganScreen extends ConsumerStatefulWidget {
  const TabunganScreen({super.key});

  @override
  ConsumerState<TabunganScreen> createState() => _TabunganScreenState();
}

class _TabunganScreenState extends ConsumerState<TabunganScreen> {
  bool _hidden = false;

  @override
  Widget build(BuildContext context) {
    final tabAsync = ref.watch(tabunganProvider);
    final auth = ref.watch(authProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Tabungan'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(tabunganProvider);
          await ref.read(tabunganProvider.future);
        },
        child: tabAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _error(),
          data: (rek) {
            if (rek == null) {
              return _empty();
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
              children: [
                _SaldoCard(rek: rek, hidden: _hidden, onToggle: () {
                  setState(() => _hidden = !_hidden);
                }),
                const SizedBox(height: 18),
                if (auth.user?.canWritePembayaran == true) ...[
                  _ActionRow(),
                  const SizedBox(height: 18),
                ],
                _BreakdownCard(rek: rek),
                const SizedBox(height: 20),
                const _SectionTitle('Mutasi Terbaru'),
                const SizedBox(height: 10),
                if (rek.transaksi == null || rek.transaksi!.isEmpty)
                  _emptyMutasi()
                else
                  _MutasiList(items: rek.transaksi!),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _error() => ListView(children: [
        const SizedBox(height: 120),
        const Icon(Icons.cloud_off_rounded,
            size: 64, color: AppColors.textHint),
        const SizedBox(height: 12),
        const Center(
          child: Text('Gagal memuat tabungan',
              style: TextStyle(color: AppColors.textSecondary)),
        ),
        const SizedBox(height: 16),
        Center(
          child: SizedBox(
            width: 180,
            child: OutlinedButton.icon(
              onPressed: () => ref.invalidate(tabunganProvider),
              icon: const Icon(Icons.refresh),
              label: const Text('Coba Lagi'),
            ),
          ),
        ),
      ]);

  Widget _empty() => ListView(children: const [
        SizedBox(height: 120),
        Icon(Icons.savings_outlined, size: 64, color: AppColors.textHint),
        SizedBox(height: 12),
        Center(
          child: Text('Tidak ada rekening tabungan',
              style: TextStyle(color: AppColors.textSecondary)),
        ),
      ]);

  Widget _emptyMutasi() => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: AppShadows.sm,
        ),
        child: const Center(
          child: Text('Belum ada transaksi',
              style: TextStyle(color: AppColors.textSecondary)),
        ),
      );
}

class _SaldoCard extends StatelessWidget {
  final RekeningTabungan rek;
  final bool hidden;
  final VoidCallback onToggle;

  const _SaldoCard({
    required this.rek,
    required this.hidden,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final saldoText = hidden ? '•••••••' : rek.totalSaldo.toCurrencyRp;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(22, 22, 22, 22),
      decoration: BoxDecoration(
        gradient: AppColors.cardGradient,
        borderRadius: BorderRadius.circular(22),
        boxShadow: AppShadows.brand,
      ),
      child: Stack(
        children: [
          Positioned(
            right: -20,
            top: -20,
            child: Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.06),
              ),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Total Saldo',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Spacer(),
                  InkWell(
                    onTap: onToggle,
                    borderRadius: BorderRadius.circular(20),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: Icon(
                        hidden
                            ? Icons.visibility_off_rounded
                            : Icons.visibility_rounded,
                        color: Colors.white.withValues(alpha: 0.9),
                        size: 20,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                saldoText,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.2,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.credit_card_rounded,
                        color: Colors.white, size: 16),
                    const SizedBox(width: 6),
                    Text(
                      rek.noRekening,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Text(
                'a.n. ${rek.nasabahNama}',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.85),
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _ActionButton(
            icon: Icons.add_circle_outline_rounded,
            label: 'Setor',
            color: AppColors.success,
            onTap: () => context.push('/tabungan/setor'),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _ActionButton(
            icon: Icons.remove_circle_outline_rounded,
            label: 'Tarik',
            color: AppColors.error,
            onTap: () => context.push('/tabungan/tarik'),
          ),
        ),
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          boxShadow: AppShadows.sm,
        ),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 22),
            ),
            const SizedBox(height: 8),
            Text(label,
                style: const TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }
}

class _BreakdownCard extends StatelessWidget {
  final RekeningTabungan rek;
  const _BreakdownCard({required this.rek});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        children: [
          _row('Saldo Pokok', rek.saldoPokok, color: AppColors.textPrimary),
          const Divider(height: 22),
          _row('Saldo Wajib', rek.saldoWajib, color: AppColors.textPrimary),
          const Divider(height: 22),
          _row('Saldo Sukarela', rek.saldoSukarela,
              color: AppColors.textPrimary),
          const Divider(height: 22),
          _row('Bisa Tarik', rek.saldoBisaTarik,
              color: AppColors.success, bold: true),
        ],
      ),
    );
  }

  Widget _row(String label, int amount, {Color? color, bool bold = false}) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 13,
              color: AppColors.textSecondary,
            ),
          ),
        ),
        Text(
          amount.toCurrencyRp,
          style: TextStyle(
            fontSize: 14,
            fontWeight: bold ? FontWeight.w800 : FontWeight.w700,
            color: color ?? AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}

class _MutasiList extends StatelessWidget {
  final List<TransaksiTabungan> items;
  const _MutasiList({required this.items});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        children: List.generate(items.length, (i) {
          final t = items[i];
          final isSetor = t.jenis == 'setor';
          final color = isSetor ? AppColors.success : AppColors.error;
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(
                        isSetor
                            ? Icons.arrow_downward_rounded
                            : Icons.arrow_upward_rounded,
                        color: color,
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${isSetor ? 'Setoran' : 'Penarikan'} ${t.kategori}',
                            style: const TextStyle(
                                fontSize: 13.5,
                                fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${t.noBukti} · ${formatDateApi(t.tanggal)}',
                            style: const TextStyle(
                                fontSize: 11.5,
                                color: AppColors.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      '${isSetor ? '+' : '-'}${t.jumlah.toCurrencyRp}',
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 13.5,
                        color: color,
                      ),
                    ),
                  ],
                ),
              ),
              if (i < items.length - 1)
                const Divider(height: 0, indent: 14, endIndent: 14),
            ],
          );
        }),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
      );
}
