import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/auth/auth_repository.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final user = auth.user;

    if (user == null) {
      return const Scaffold(body: Center(child: Text('Silakan login')));
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Profil')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
        children: [
          // Header card
          Container(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 22),
            decoration: BoxDecoration(
              gradient: AppColors.cardGradient,
              borderRadius: BorderRadius.circular(20),
              boxShadow: AppShadows.brand,
            ),
            child: Row(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.18),
                    shape: BoxShape.circle,
                    border: Border.all(
                        color: Colors.white.withValues(alpha: 0.3), width: 2),
                  ),
                  child: Center(
                    child: Text(
                      user.namaLengkap.isNotEmpty
                          ? user.namaLengkap[0].toUpperCase()
                          : '?',
                      style: const TextStyle(
                          fontSize: 26,
                          color: Colors.white,
                          fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.namaLengkap,
                        style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            color: Colors.white),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          user.roleLabel,
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 11,
                              fontWeight: FontWeight.w600),
                        ),
                      ),
                      if (user.kodeDesa != null) ...[
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Icon(Icons.place_rounded,
                                color: Colors.white.withValues(alpha: 0.85),
                                size: 14),
                            const SizedBox(width: 4),
                            Text('Desa: ${user.kodeDesa}',
                                style: TextStyle(
                                    color:
                                        Colors.white.withValues(alpha: 0.85),
                                    fontSize: 12)),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Nasabah info
          if (auth.nasabah != null) ...[
            _SectionTitle('Data Nasabah'),
            const SizedBox(height: 10),
            _Card(
              child: Column(
                children: [
                  _InfoRow(label: 'ID Nasabah', value: auth.nasabah!.nasabahId),
                  const _SoftDivider(),
                  _InfoRow(label: 'NIK', value: auth.nasabah!.nik),
                  const _SoftDivider(),
                  _InfoRow(label: 'No. HP', value: auth.nasabah!.noHp),
                  const _SoftDivider(),
                  _InfoRow(label: 'Alamat', value: auth.nasabah!.alamat),
                  const _SoftDivider(),
                  _InfoRow(
                      label: 'Status',
                      value: auth.nasabah!.isAktif ? 'Aktif' : 'Calon'),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          _SectionTitle('Pengaturan'),
          const SizedBox(height: 10),
          _Card(
            child: Column(
              children: [
                _MenuTile(
                  icon: Icons.lock_outline_rounded,
                  iconColor: AppColors.primary,
                  title: 'Ganti Password',
                  onTap: () => context.push('/change-password'),
                ),
                if (user.isPenagih || user.isKader) ...[
                  const _SoftDivider(),
                  _MenuTile(
                    icon: Icons.emoji_events_outlined,
                    iconColor: AppColors.accent,
                    title: 'Bonus Saya',
                    onTap: () => context.push('/bonus-saya'),
                  ),
                ],
                if (user.isNasabah) ...[
                  const _SoftDivider(),
                  _MenuTile(
                    icon: Icons.storefront_outlined,
                    iconColor: AppColors.success,
                    title: 'Daftar Jadi Penjual UMKM',
                    onTap: () => context.push('/umkm/daftar-penjual'),
                  ),
                ],
                const _SoftDivider(),
                _MenuTile(
                  icon: Icons.info_outline_rounded,
                  iconColor: AppColors.info,
                  title: 'Versi Aplikasi',
                  trailing: const Text('1.0.0',
                      style: TextStyle(
                          color: AppColors.textSecondary,
                          fontWeight: FontWeight.w600)),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () async {
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (c) => AlertDialog(
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16)),
                    title: const Text('Keluar'),
                    content:
                        const Text('Apakah Anda yakin ingin keluar?'),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(c, false),
                          child: const Text('Batal')),
                      TextButton(
                          onPressed: () => Navigator.pop(c, true),
                          child: const Text('Keluar',
                              style:
                                  TextStyle(color: AppColors.error))),
                    ],
                  ),
                );
                if (confirm == true) {
                  await ref.read(authProvider.notifier).logout();
                  // Router will redirect via refreshListenable
                }
              },
              icon: const Icon(Icons.logout_rounded,
                  color: AppColors.error),
              label: const Text('Keluar',
                  style: TextStyle(color: AppColors.error)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.error, width: 1.4),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Card extends StatelessWidget {
  final Widget child;
  const _Card({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: child,
    );
  }
}

class _SoftDivider extends StatelessWidget {
  const _SoftDivider();
  @override
  Widget build(BuildContext context) =>
      const Divider(height: 0, indent: 16, endIndent: 16);
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
            color: AppColors.textPrimary),
      );
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(label,
                style: const TextStyle(
                    fontSize: 12.5, color: AppColors.textSecondary)),
          ),
          Expanded(
            child: Text(
              value.isEmpty ? '-' : value,
              style: const TextStyle(
                  fontSize: 13.5, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _MenuTile extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final Widget? trailing;
  final VoidCallback? onTap;

  const _MenuTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    this.trailing,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(title,
                  style: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w600)),
            ),
            if (trailing != null)
              trailing!
            else if (onTap != null)
              const Icon(Icons.chevron_right_rounded,
                  color: AppColors.textHint),
          ],
        ),
      ),
    );
  }
}
