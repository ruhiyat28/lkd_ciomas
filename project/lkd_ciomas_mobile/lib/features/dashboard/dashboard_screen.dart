import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/utils/currency_format.dart';
import '../../models/dashboard_data.dart';
import '../../models/user.dart';

final dashboardProvider = FutureProvider<DashboardData?>((ref) async {
  final api = ref.watch(apiClientProvider);
  try {
    final res = await api.get(ApiEndpoints.dashboard);
    return DashboardData.fromJson(res.data['data']);
  } catch (e) {
    return null;
  }
});

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final user = auth.user;
    final dashboardAsync = ref.watch(dashboardProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(dashboardProvider);
          await ref.read(dashboardProvider.future);
        },
        child: dashboardAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _ErrorView(
            onRetry: () => ref.invalidate(dashboardProvider),
          ),
          data: (data) {
            if (data == null) {
              return _ErrorView(
                onRetry: () => ref.invalidate(dashboardProvider),
              );
            }
            return CustomScrollView(
              slivers: [
                _Header(user: user),
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                  sliver: SliverList(
                    delegate: SliverChildListDelegate([
                      _DashboardBody(data: data, user: user),
                    ]),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final VoidCallback onRetry;
  const _ErrorView({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 120),
        const Icon(Icons.cloud_off_rounded,
            size: 64, color: AppColors.textHint),
        const SizedBox(height: 12),
        const Center(
          child: Text('Gagal memuat dashboard',
              style: TextStyle(color: AppColors.textSecondary)),
        ),
        const SizedBox(height: 16),
        Center(
          child: SizedBox(
            width: 180,
            child: OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Coba Lagi'),
            ),
          ),
        ),
      ],
    );
  }
}

class _Header extends StatelessWidget {
  final User? user;
  const _Header({required this.user});

  @override
  Widget build(BuildContext context) {
    final greeting = _greeting();
    final initial =
        (user?.namaLengkap.isNotEmpty == true) ? user!.namaLengkap[0] : '?';

    return SliverAppBar(
      pinned: false,
      floating: false,
      expandedHeight: 0,
      backgroundColor: AppColors.background,
      elevation: 0,
      automaticallyImplyLeading: false,
      toolbarHeight: 70,
      title: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              gradient: AppColors.cardGradientSoft,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Center(
              child: Text(
                initial.toUpperCase(),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(greeting,
                    style: const TextStyle(
                        fontSize: 12, color: AppColors.textSecondary)),
                const SizedBox(height: 2),
                Text(
                  user?.namaLengkap ?? 'Pengguna',
                  style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Notifikasi',
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.notifications_none_rounded,
                  size: 20, color: AppColors.textPrimary),
            ),
            onPressed: () {},
          ),
        ],
      ),
    );
  }

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 11) return 'Selamat Pagi';
    if (h < 15) return 'Selamat Siang';
    if (h < 18) return 'Selamat Sore';
    return 'Selamat Malam';
  }
}

class _DashboardBody extends StatelessWidget {
  final DashboardData data;
  final User? user;
  const _DashboardBody({required this.data, this.user});

  @override
  Widget build(BuildContext context) {
    final isNasabah = user?.isNasabah == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (isNasabah && data.rekening != null) ...[
          _BalanceCard(rek: data.rekening!),
          const SizedBox(height: 20),
          _SectionTitle('Layanan'),
          const SizedBox(height: 12),
          _QuickActionsNasabah(activeLoanId: data.activeLoanId),
        ] else ...[
          _StatGrid(data: data, user: user),
        ],

        // Pinjaman aktif (nasabah)
        if (isNasabah && data.hasActiveLoan && data.activeLoanId != null) ...[
          const SizedBox(height: 20),
          _SectionTitle('Pinjaman Aktif'),
          const SizedBox(height: 10),
          _ActiveLoanCard(loanId: data.activeLoanId!),
        ],

        // Rekap per Desa (admin)
        if (data.rekapDesa.isNotEmpty && user?.isAdmin == true) ...[
          const SizedBox(height: 20),
          _SectionTitle('Outstanding per Desa'),
          const SizedBox(height: 10),
          _RekapDesaList(rekap: data.rekapDesa),
        ],

        // Pengumuman
        if (data.pengumuman != null && data.pengumuman!.isNotEmpty) ...[
          const SizedBox(height: 20),
          _SectionTitle('Pengumuman'),
          const SizedBox(height: 10),
          ...data.pengumuman!.map((p) => _PengumumanTile(p: p)),
        ],
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
        letterSpacing: 0.2,
      ),
    );
  }
}

class _BalanceCard extends StatefulWidget {
  final dynamic rek; // RekeningRingkasan
  const _BalanceCard({required this.rek});

  @override
  State<_BalanceCard> createState() => _BalanceCardState();
}

class _BalanceCardState extends State<_BalanceCard> {
  bool _hidden = false;

  @override
  Widget build(BuildContext context) {
    final rek = widget.rek;
    final saldo = rek.totalSaldo as int;
    final saldoText = _hidden ? '•••••••' : saldo.toCurrencyRp;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(22, 22, 22, 20),
      decoration: BoxDecoration(
        gradient: AppColors.cardGradient,
        borderRadius: BorderRadius.circular(22),
        boxShadow: AppShadows.brand,
      ),
      child: Stack(
        children: [
          Positioned(
            right: -10,
            top: -10,
            child: Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.07),
              ),
            ),
          ),
          Positioned(
            right: 30,
            bottom: -20,
            child: Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.05),
              ),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Saldo Tabungan',
                    style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontSize: 13,
                        fontWeight: FontWeight.w500),
                  ),
                  const Spacer(),
                  InkWell(
                    onTap: () => setState(() => _hidden = !_hidden),
                    borderRadius: BorderRadius.circular(20),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: Icon(
                        _hidden
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
                  fontSize: 30,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.3,
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Icon(Icons.credit_card_rounded,
                      size: 16,
                      color: Colors.white.withValues(alpha: 0.85)),
                  const SizedBox(width: 6),
                  Text(
                    rek.noRekening,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.92),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.1,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickActionsNasabah extends StatelessWidget {
  final int? activeLoanId;
  const _QuickActionsNasabah({this.activeLoanId});

  @override
  Widget build(BuildContext context) {
    final items = [
      _QuickAction(
        icon: Icons.savings_rounded,
        label: 'Tabungan',
        color: AppColors.primary,
        onTap: () => context.push('/tabungan'),
      ),
      _QuickAction(
        icon: Icons.account_balance_rounded,
        label: 'Pinjaman',
        color: AppColors.success,
        onTap: () => context.push('/pinjaman'),
      ),
      _QuickAction(
        icon: Icons.storefront_rounded,
        label: 'UMKM',
        color: AppColors.accent,
        onTap: () => context.push('/umkm/katalog'),
      ),
      _QuickAction(
        icon: Icons.add_circle_outline_rounded,
        label: 'Ajukan',
        color: AppColors.info,
        onTap: () => context.push('/pinjaman/tambah'),
      ),
    ];

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: AppShadows.sm,
      ),
      child: Row(
        children: items
            .map((e) => Expanded(child: _QuickActionTile(action: e)))
            .toList(),
      ),
    );
  }
}

class _QuickAction {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _QuickAction({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });
}

class _QuickActionTile extends StatelessWidget {
  final _QuickAction action;
  const _QuickActionTile({required this.action});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: action.onTap,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: action.color.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(action.icon, color: action.color, size: 22),
            ),
            const SizedBox(height: 8),
            Text(
              action.label,
              style: const TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatGrid extends StatelessWidget {
  final DashboardData data;
  final User? user;
  const _StatGrid({required this.data, this.user});

  @override
  Widget build(BuildContext context) {
    final stats = <_StatItem>[
      _StatItem('Nasabah Aktif', data.totalNasabahAktif,
          Icons.people_alt_rounded, AppColors.primary),
      _StatItem('Pinjaman Aktif', data.pinjamanAktif,
          Icons.account_balance_rounded, AppColors.info),
      _StatItem('Outstanding', data.totalOutstanding,
          Icons.monetization_on_rounded, AppColors.accent),
      _StatItem('Penyaluran', data.totalPenyaluran,
          Icons.trending_up_rounded, AppColors.success),
      if (user?.isAdmin == true) ...[
        _StatItem('Pengajuan', data.pendingPengajuan,
            Icons.pending_actions_rounded, AppColors.warning),
        _StatItem('Nasabah Nunggak', data.nasabahNunggak,
            Icons.warning_amber_rounded, AppColors.error),
      ],
      if (user?.isKader == true) ...[
        _StatItem('Bayar Hari Ini', data.pembayaranHariIni,
            Icons.payments_rounded, AppColors.success,
            onTap: () {}),
        _StatItem('Total Bayar', data.totalBayarHariIni,
            Icons.receipt_rounded, AppColors.info),
      ],
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle('Ringkasan'),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 1.45,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          children: stats.map((s) => _StatTile(item: s)).toList(),
        ),
      ],
    );
  }
}

class _StatItem {
  final String label;
  final int value;
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;
  const _StatItem(this.label, this.value, this.icon, this.color,
      {this.onTap});
}

class _StatTile extends StatelessWidget {
  final _StatItem item;
  const _StatTile({required this.item});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: item.onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: AppShadows.sm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: item.color.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(item.icon, color: item.color, size: 20),
            ),
            const SizedBox(height: 10),
            Text(
              item.label,
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.textSecondary,
                fontWeight: FontWeight.w500,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
            Text(
              item.value.toCurrency,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActiveLoanCard extends StatelessWidget {
  final int loanId;
  const _ActiveLoanCard({required this.loanId});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push('/pinjaman/$loanId'),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: AppShadows.sm,
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(Icons.account_balance_rounded,
                  color: AppColors.accent),
            ),
            const SizedBox(width: 14),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Pinjaman Aktif',
                      style: TextStyle(
                          fontSize: 14, fontWeight: FontWeight.w700)),
                  SizedBox(height: 2),
                  Text('Lihat detail & jadwal angsuran',
                      style: TextStyle(
                          fontSize: 12,
                          color: AppColors.textSecondary)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textHint),
          ],
        ),
      ),
    );
  }
}

class _RekapDesaList extends StatelessWidget {
  final List<RekapDesa> rekap;
  const _RekapDesaList({required this.rekap});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        children: List.generate(rekap.length, (i) {
          final d = rekap[i];
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(d.nama,
                              style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700)),
                          const SizedBox(height: 2),
                          Text('${d.total} nasabah',
                              style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary)),
                        ],
                      ),
                    ),
                    Text(
                      d.outstanding.toCurrencyRp,
                      style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: AppColors.primary),
                    ),
                  ],
                ),
              ),
              if (i < rekap.length - 1)
                const Divider(height: 0, indent: 16, endIndent: 16),
            ],
          );
        }),
      ),
    );
  }
}

class _PengumumanTile extends StatelessWidget {
  final Pengumuman p;
  const _PengumumanTile({required this.p});

  @override
  Widget build(BuildContext context) {
    Color color;
    IconData icon;
    switch (p.tipe) {
      case 'warning':
        color = AppColors.warning;
        icon = Icons.warning_amber_rounded;
        break;
      case 'urgent':
        color = AppColors.error;
        icon = Icons.priority_high_rounded;
        break;
      default:
        color = AppColors.info;
        icon = Icons.campaign_rounded;
    }
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: AppShadows.sm,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(p.judul,
                    style: const TextStyle(
                        fontSize: 13.5, fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(
                  p.isi,
                  style: const TextStyle(
                      fontSize: 12, color: AppColors.textSecondary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
