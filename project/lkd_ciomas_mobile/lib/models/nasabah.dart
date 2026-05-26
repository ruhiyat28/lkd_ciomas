class Nasabah {
  final int id;
  final String nasabahId;
  final String jenis;
  final String kodeDesa;
  final String namaDesa;
  final String nama;
  final String nik;
  final String status;
  final String keteranganStatus;
  final String noHp;
  final String alamat;
  final String pekerjaan;
  final String? foto;
  final String? ktp;
  final String? kk;
  final String? suratUsaha;
  final String? buktiPenghasilan;
  final String? jaminan;
  final String? tempatLahir;
  final String? tanggalLahir;
  final String? jenisKelamin;
  final String? namaPasangan;
  final String? nikPasangan;
  final String? noHpPasangan;
  final String? keteranganJaminan;
  final String? tandaTangan;
  final bool? dokumenLengkap;
  final String createdAt;
  final RekeningRingkasan? rekening;
  final List<PinjamanRingkasan>? pinjaman;

  Nasabah({
    required this.id,
    required this.nasabahId,
    required this.jenis,
    required this.kodeDesa,
    required this.namaDesa,
    required this.nama,
    required this.nik,
    required this.status,
    required this.keteranganStatus,
    required this.noHp,
    required this.alamat,
    required this.pekerjaan,
    this.foto,
    this.ktp,
    this.kk,
    this.suratUsaha,
    this.buktiPenghasilan,
    this.jaminan,
    this.tempatLahir,
    this.tanggalLahir,
    this.jenisKelamin,
    this.namaPasangan,
    this.nikPasangan,
    this.noHpPasangan,
    this.keteranganJaminan,
    this.tandaTangan,
    this.dokumenLengkap,
    this.createdAt = '',
    this.rekening,
    this.pinjaman,
  });

  factory Nasabah.fromJson(Map<String, dynamic> json) {
    return Nasabah(
      id: json['id'] as int,
      nasabahId: json['nasabah_id'] as String? ?? '',
      jenis: json['jenis'] as String? ?? '',
      kodeDesa: json['kode_desa'] as String? ?? '',
      namaDesa: json['nama_desa'] as String? ?? '',
      nama: json['nama'] as String? ?? '',
      nik: json['nik'] as String? ?? '',
      status: json['status'] as String? ?? '',
      keteranganStatus: json['keterangan_status'] as String? ?? '',
      noHp: json['no_hp'] as String? ?? '',
      alamat: json['alamat'] as String? ?? '',
      pekerjaan: json['pekerjaan'] as String? ?? '',
      foto: json['foto'] as String?,
      ktp: json['ktp'] as String?,
      kk: json['kk'] as String?,
      suratUsaha: json['surat_usaha'] as String?,
      buktiPenghasilan: json['bukti_penghasilan'] as String?,
      jaminan: json['jaminan'] as String?,
      tempatLahir: json['tempat_lahir'] as String?,
      tanggalLahir: json['tanggal_lahir'] as String?,
      jenisKelamin: json['jenis_kelamin'] as String?,
      namaPasangan: json['nama_pasangan'] as String?,
      nikPasangan: json['nik_pasangan'] as String?,
      noHpPasangan: json['no_hp_pasangan'] as String?,
      keteranganJaminan: json['keterangan_jaminan'] as String?,
      tandaTangan: json['tanda_tangan'] as String?,
      dokumenLengkap: json['dokumen_lengkap'] as bool?,
      createdAt: json['created_at'] as String? ?? '',
      rekening: json['rekening'] != null
          ? RekeningRingkasan.fromJson(json['rekening'])
          : null,
      pinjaman: json['pinjaman'] != null
          ? (json['pinjaman'] as List)
              .map((e) => PinjamanRingkasan.fromJson(e))
              .toList()
          : null,
    );
  }

  bool get isAktif => status == 'aktif';
  bool get isCalon => status == 'calon';
}

class RekeningRingkasan {
  final int id;
  final String noRekening;
  final int saldoPokok;
  final int saldoWajib;
  final int saldoSukarela;
  final int totalSaldo;

  RekeningRingkasan({
    required this.id,
    required this.noRekening,
    required this.saldoPokok,
    required this.saldoWajib,
    required this.saldoSukarela,
    required this.totalSaldo,
  });

  factory RekeningRingkasan.fromJson(Map<String, dynamic> json) {
    return RekeningRingkasan(
      id: json['id'] as int,
      noRekening: json['no_rekening'] as String? ?? '',
      saldoPokok: json['saldo_pokok'] as int? ?? 0,
      saldoWajib: json['saldo_wajib'] as int? ?? 0,
      saldoSukarela: json['saldo_sukarela'] as int? ?? 0,
      totalSaldo: json['total_saldo'] as int? ?? 0,
    );
  }
}

class PinjamanRingkasan {
  final int id;
  final String spk;
  final String jenisPinjaman;
  final int jumlahPinjaman;
  final int tenor;
  final String status;
  final String? tanggalPengajuan;
  final String? tanggalCair;
  final int? angsuranPokok;
  final int? angsuranJasa;
  final int? angsuranTotal;
  final int? saldoPokok;
  final int? pokokTerbayar;
  final int? jasaTerbayar;

  PinjamanRingkasan({
    required this.id,
    required this.spk,
    required this.jenisPinjaman,
    required this.jumlahPinjaman,
    required this.tenor,
    required this.status,
    this.tanggalPengajuan,
    this.tanggalCair,
    this.angsuranPokok,
    this.angsuranJasa,
    this.angsuranTotal,
    this.saldoPokok,
    this.pokokTerbayar,
    this.jasaTerbayar,
  });

  factory PinjamanRingkasan.fromJson(Map<String, dynamic> json) {
    return PinjamanRingkasan(
      id: json['id'] as int,
      spk: json['spk'] as String? ?? '',
      jenisPinjaman: json['jenis_pinjaman'] as String? ?? '',
      jumlahPinjaman: json['jumlah_pinjaman'] as int? ?? 0,
      tenor: json['tenor'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      tanggalPengajuan: json['tanggal_pengajuan'] as String?,
      tanggalCair: json['tanggal_cair'] as String?,
      angsuranPokok: json['angsuran_pokok'] as int?,
      angsuranJasa: json['angsuran_jasa'] as int?,
      angsuranTotal: json['angsuran_total'] as int?,
      saldoPokok: json['saldo_pokok'] as int?,
      pokokTerbayar: json['pokok_terbayar'] as int?,
      jasaTerbayar: json['jasa_terbayar'] as int?,
    );
  }
}
