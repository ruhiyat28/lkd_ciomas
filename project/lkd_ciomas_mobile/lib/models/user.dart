class User {
  final int id;
  final String username;
  final String namaLengkap;
  final String role;
  final String roleLabel;
  final String? kodeDesa;
  final int? nasabahId;
  final String? tandaTangan;

  User({
    required this.id,
    required this.username,
    required this.namaLengkap,
    required this.role,
    required this.roleLabel,
    this.kodeDesa,
    this.nasabahId,
    this.tandaTangan,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      username: json['username'] as String? ?? '',
      namaLengkap: json['nama_lengkap'] as String? ?? '',
      role: json['role'] as String? ?? '',
      roleLabel: json['role_label'] as String? ?? '',
      kodeDesa: json['kode_desa'] as String?,
      nasabahId: json['nasabah_id'] as int?,
      tandaTangan: json['tanda_tangan'] as String?,
    );
  }

  bool get isNasabah => role == 'nasabah';
  bool get isPenagih => role == 'penagih';
  bool get isVerifikator => role == 'verifikator';
  bool get isKader => role == 'kader_desa';
  bool get isAdmin => role == 'admin';
  bool get isManajer => role == 'manajer_lkd';

  bool get canWritePembayaran =>
      ['admin', 'manajer_lkd', 'keuangan', 'kredit', 'tata_usaha', 'kasir',
       'kader_desa', 'penagih', 'staf'].contains(role);

  bool get canWritePinjaman =>
      ['admin', 'manajer_lkd', 'kredit', 'verifikator', 'staf',
       'kader_desa'].contains(role);

  bool get canWriteNasabah =>
      ['admin', 'manajer_lkd', 'kredit', 'tata_usaha', 'staf',
       'kader_desa'].contains(role);

  bool get canEditDelete =>
      ['admin', 'manajer_lkd', 'staf'].contains(role);
}
