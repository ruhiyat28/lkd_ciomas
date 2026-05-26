class Pembayaran {
  final int id;
  final String noKuitansi;
  final int pinjamanId;
  final String spk;
  final String nasabah;
  final String tanggalBayar;
  final int jumlahBayar;
  final int bayarPokok;
  final int bayarJasa;
  final int? angsuranKe;
  final String keterangan;
  final String statusAcc;
  final String createdAt;

  Pembayaran({
    required this.id,
    required this.noKuitansi,
    required this.pinjamanId,
    required this.spk,
    required this.nasabah,
    required this.tanggalBayar,
    required this.jumlahBayar,
    required this.bayarPokok,
    required this.bayarJasa,
    this.angsuranKe,
    required this.keterangan,
    required this.statusAcc,
    required this.createdAt,
  });

  factory Pembayaran.fromJson(Map<String, dynamic> json) {
    return Pembayaran(
      id: json['id'] as int,
      noKuitansi: json['no_kuitansi'] as String? ?? '',
      pinjamanId: json['pinjaman_id'] as int? ?? 0,
      spk: json['spk'] as String? ?? '',
      nasabah: json['nasabah'] as String? ?? '',
      tanggalBayar: json['tanggal_bayar'] as String? ?? '',
      jumlahBayar: json['jumlah_bayar'] as int? ?? 0,
      bayarPokok: json['bayar_pokok'] as int? ?? 0,
      bayarJasa: json['bayar_jasa'] as int? ?? 0,
      angsuranKe: json['angsuran_ke'] as int?,
      keterangan: json['keterangan'] as String? ?? '',
      statusAcc: json['status_acc'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
    );
  }

  bool get isWaiting => statusAcc == 'menunggu';
  bool get isApproved => statusAcc == 'diterima';
  bool get isRejected => statusAcc == 'ditolak';
  bool get isValid => statusAcc.isEmpty || statusAcc == 'diterima';
}

class PembayaranDraft {
  int? pinjamanId;
  int jumlahBayar;
  String? tanggalBayar;
  String? keterangan;
  double? lat;
  double? lng;
  String? offlineKuitansi;

  PembayaranDraft({
    this.pinjamanId,
    this.jumlahBayar = 0,
    this.tanggalBayar,
    this.keterangan,
    this.lat,
    this.lng,
    this.offlineKuitansi,
  });

  Map<String, dynamic> toJson() => {
    'pinjaman_id': pinjamanId,
    'jumlah_bayar': jumlahBayar,
    'tanggal_bayar': tanggalBayar,
    'keterangan': keterangan,
  };
}
