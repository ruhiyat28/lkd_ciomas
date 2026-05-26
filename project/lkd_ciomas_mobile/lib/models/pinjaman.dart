class Pinjaman {
  final int id;
  final String spk;
  final String jenisPinjaman;
  final int nasabahId;
  final String nasabah;
  final String nasabahNasabahId;
  final String? noHp;
  final int jumlahPinjaman;
  final double jasaPersen;
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
  final int? tunggakanPokok;
  final int? tunggakanJasa;
  final int? bulanNunggak;
  final String? kolektibilitas;
  final String? kolektibilitasLabel;
  final String? tujuan;
  final String createdAt;
  final List<JadwalAngsuran>? jadwalAngsuran;
  final NasabahRingkasan? nasabahDetail;

  Pinjaman({
    required this.id,
    required this.spk,
    required this.jenisPinjaman,
    required this.nasabahId,
    required this.nasabah,
    required this.nasabahNasabahId,
    this.noHp,
    required this.jumlahPinjaman,
    required this.jasaPersen,
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
    this.tunggakanPokok,
    this.tunggakanJasa,
    this.bulanNunggak,
    this.kolektibilitas,
    this.kolektibilitasLabel,
    this.tujuan,
    this.createdAt = '',
    this.jadwalAngsuran,
    this.nasabahDetail,
  });

  factory Pinjaman.fromJson(Map<String, dynamic> json) {
    return Pinjaman(
      id: json['id'] as int,
      spk: json['spk'] as String? ?? '',
      jenisPinjaman: json['jenis_pinjaman'] as String? ?? '',
      nasabahId: json['nasabah_id'] as int? ?? 0,
      nasabah: json['nasabah'] is String
          ? json['nasabah'] as String
          : (json['nasabah'] is Map<String, dynamic>
              ? (json['nasabah']['nama'] as String? ?? '')
              : ''),
      nasabahNasabahId: json['nasabah_nasabah_id'] as String? ?? '',
      noHp: json['no_hp'] as String?,
      jumlahPinjaman: json['jumlah_pinjaman'] as int? ?? 0,
      jasaPersen: (json['jasa_persen'] as num?)?.toDouble() ?? 1.5,
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
      tunggakanPokok: json['tunggakan_pokok'] as int?,
      tunggakanJasa: json['tunggakan_jasa'] as int?,
      bulanNunggak: json['bulan_nunggak'] as int?,
      kolektibilitas: json['kolektibilitas'] as String?,
      kolektibilitasLabel: json['kolektibilitas_label'] as String?,
      tujuan: json['tujuan'] as String?,
      createdAt: json['created_at'] as String? ?? '',
      jadwalAngsuran: json['jadwal_angsuran'] != null
          ? (json['jadwal_angsuran'] as List)
              .map((e) => JadwalAngsuran.fromJson(e))
              .toList()
          : null,
      nasabahDetail: json['nasabah'] is Map<String, dynamic>
          ? NasabahRingkasan.fromJson(json['nasabah'] as Map<String, dynamic>)
          : (json['nasabah_detail'] is Map<String, dynamic>
              ? NasabahRingkasan.fromJson(
                  json['nasabah_detail'] as Map<String, dynamic>)
              : null),
    );
  }

  bool get isAktif => status == 'cair';
  bool get isLunas => status == 'lunas';
  bool get isPengajuan => status == 'pengajuan';
}

class JadwalAngsuran {
  final int ke;
  final String tanggal;
  final int pokok;
  final int jasa;
  final int total;
  final bool lunas;
  final bool terlambat;

  JadwalAngsuran({
    required this.ke,
    required this.tanggal,
    required this.pokok,
    required this.jasa,
    required this.total,
    required this.lunas,
    required this.terlambat,
  });

  factory JadwalAngsuran.fromJson(Map<String, dynamic> json) {
    return JadwalAngsuran(
      ke: json['ke'] as int? ?? 0,
      tanggal: json['tanggal'] as String? ?? '',
      pokok: json['pokok'] as int? ?? 0,
      jasa: json['jasa'] as int? ?? 0,
      total: json['total'] as int? ?? 0,
      lunas: json['lunas'] as bool? ?? false,
      terlambat: json['terlambat'] as bool? ?? false,
    );
  }
}

class NasabahRingkasan {
  final int id;
  final String nasabahId;
  final String nama;
  final String nik;
  final String kodeDesa;
  final String namaDesa;

  NasabahRingkasan({
    required this.id,
    required this.nasabahId,
    required this.nama,
    required this.nik,
    required this.kodeDesa,
    required this.namaDesa,
  });

  factory NasabahRingkasan.fromJson(Map<String, dynamic> json) {
    return NasabahRingkasan(
      id: json['id'] as int,
      nasabahId: json['nasabah_id'] as String? ?? '',
      nama: json['nama'] as String? ?? '',
      nik: json['nik'] as String? ?? '',
      kodeDesa: json['kode_desa'] as String? ?? '',
      namaDesa: json['nama_desa'] as String? ?? '',
    );
  }
}
