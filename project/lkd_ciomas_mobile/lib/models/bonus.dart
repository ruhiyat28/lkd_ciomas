class BonusData {
  final List<BonusItem> items;
  final int totalBonus;
  final int totalDiklaim;
  final int totalSemua;

  BonusData({
    required this.items,
    required this.totalBonus,
    required this.totalDiklaim,
    required this.totalSemua,
  });

  factory BonusData.fromJson(Map<String, dynamic> json) {
    return BonusData(
      items: (json['items'] as List?)
              ?.map((e) => BonusItem.fromJson(e))
              .toList() ??
          [],
      totalBonus: json['total_bonus'] as int? ?? 0,
      totalDiklaim: json['total_diklaim'] as int? ?? 0,
      totalSemua: json['total_semua'] as int? ?? 0,
    );
  }
}

class BonusItem {
  final int id;
  final int? pembayaranId;
  final int? tahunTunggakan;
  final int? jumlahBayar;
  final double persenBonus;
  final int jumlahBonus;
  final String status;
  final String? tanggalHitung;
  final String? tanggalKlaim;
  final String tipe;

  BonusItem({
    required this.id,
    this.pembayaranId,
    this.tahunTunggakan,
    this.jumlahBayar,
    required this.persenBonus,
    required this.jumlahBonus,
    required this.status,
    this.tanggalHitung,
    this.tanggalKlaim,
    required this.tipe,
  });

  factory BonusItem.fromJson(Map<String, dynamic> json) {
    return BonusItem(
      id: json['id'] as int,
      pembayaranId: json['pembayaran_id'] as int?,
      tahunTunggakan: json['tahun_tunggakan'] as int?,
      jumlahBayar: json['jumlah_bayar'] as int?,
      persenBonus: (json['persen_bonus'] as num?)?.toDouble() ?? 0,
      jumlahBonus: json['jumlah_bonus'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      tanggalHitung: json['tanggal_hitung'] as String?,
      tanggalKlaim: json['tanggal_klaim'] as String?,
      tipe: json['tipe'] as String? ?? '',
    );
  }
}
