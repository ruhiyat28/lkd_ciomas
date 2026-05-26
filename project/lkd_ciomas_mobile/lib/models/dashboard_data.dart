class DashboardData {
  final int totalNasabahAktif;
  final int nasabahCalon;
  final int pinjamanAktif;
  final int totalOutstanding;
  final int totalPenyaluran;
  final int pendingPengajuan;
  final int pembayaranHariIni;
  final int totalBayarHariIni;
  final int nasabahNunggak;
  final List<RekapDesa> rekapDesa;
  final RekeningRingkasan? rekening;
  final bool hasActiveLoan;
  final int? activeLoanId;
  final List<Pengumuman>? pengumuman;
  final int pendingAjuanDokumen;

  DashboardData({
    required this.totalNasabahAktif,
    required this.nasabahCalon,
    required this.pinjamanAktif,
    required this.totalOutstanding,
    required this.totalPenyaluran,
    required this.pendingPengajuan,
    required this.pembayaranHariIni,
    required this.totalBayarHariIni,
    required this.nasabahNunggak,
    required this.rekapDesa,
    this.rekening,
    this.hasActiveLoan = false,
    this.activeLoanId,
    this.pengumuman,
    this.pendingAjuanDokumen = 0,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    return DashboardData(
      totalNasabahAktif: json['total_nasabah_aktif'] as int? ?? 0,
      nasabahCalon: json['nasabah_calon'] as int? ?? 0,
      pinjamanAktif: json['pinjaman_aktif'] as int? ?? 0,
      totalOutstanding: json['total_outstanding'] as int? ?? 0,
      totalPenyaluran: json['total_penyaluran'] as int? ?? 0,
      pendingPengajuan: json['pending_pengajuan'] as int? ?? 0,
      pembayaranHariIni: json['pembayaran_hari_ini'] as int? ?? 0,
      totalBayarHariIni: json['total_bayar_hari_ini'] as int? ?? 0,
      nasabahNunggak: json['nasabah_nunggak'] as int? ?? 0,
      rekapDesa: (json['rekap_desa'] as List?)
              ?.map((e) => RekapDesa.fromJson(e))
              .toList() ??
          [],
      rekening: json['rekening'] != null
          ? RekeningRingkasan.fromJson(json['rekening'])
          : null,
      hasActiveLoan: json['has_active_loan'] as bool? ?? false,
      activeLoanId: json['active_loan_id'] as int?,
      pengumuman: json['pengumuman'] != null
          ? (json['pengumuman'] as List)
              .map((e) => Pengumuman.fromJson(e))
              .toList()
          : null,
      pendingAjuanDokumen: json['pending_ajuan_dokumen'] as int? ?? 0,
    );
  }
}

class RekapDesa {
  final String nama;
  final int total;
  final int outstanding;

  RekapDesa({
    required this.nama,
    required this.total,
    required this.outstanding,
  });

  factory RekapDesa.fromJson(Map<String, dynamic> json) {
    return RekapDesa(
      nama: json['nama'] as String? ?? '',
      total: json['total'] as int? ?? 0,
      outstanding: json['outstanding'] as int? ?? 0,
    );
  }
}

class RekeningRingkasan {
  final String noRekening;
  final int saldoPokok;
  final int saldoWajib;
  final int saldoSukarela;
  final int totalSaldo;

  RekeningRingkasan({
    required this.noRekening,
    required this.saldoPokok,
    required this.saldoWajib,
    required this.saldoSukarela,
    required this.totalSaldo,
  });

  factory RekeningRingkasan.fromJson(Map<String, dynamic> json) {
    return RekeningRingkasan(
      noRekening: json['no_rekening'] as String? ?? '',
      saldoPokok: json['saldo_pokok'] as int? ?? 0,
      saldoWajib: json['saldo_wajib'] as int? ?? 0,
      saldoSukarela: json['saldo_sukarela'] as int? ?? 0,
      totalSaldo: json['total_saldo'] as int? ?? 0,
    );
  }
}

class Pengumuman {
  final int id;
  final String judul;
  final String isi;
  final String tipe;
  final String createdAt;

  Pengumuman({
    required this.id,
    required this.judul,
    required this.isi,
    required this.tipe,
    required this.createdAt,
  });

  factory Pengumuman.fromJson(Map<String, dynamic> json) {
    return Pengumuman(
      id: json['id'] as int,
      judul: json['judul'] as String? ?? '',
      isi: json['isi'] as String? ?? '',
      tipe: json['tipe'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}
