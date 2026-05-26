class RekeningTabungan {
  final int id;
  final String noRekening;
  final int nasabahId;
  final String nasabahNama;
  final int saldoPokok;
  final int saldoWajib;
  final int saldoSukarela;
  final int totalSaldo;
  final int saldoBisaTarik;
  final bool punyaPinjamanAktif;
  final List<TransaksiTabungan>? transaksi;

  RekeningTabungan({
    required this.id,
    required this.noRekening,
    required this.nasabahId,
    required this.nasabahNama,
    required this.saldoPokok,
    required this.saldoWajib,
    required this.saldoSukarela,
    required this.totalSaldo,
    required this.saldoBisaTarik,
    required this.punyaPinjamanAktif,
    this.transaksi,
  });

  factory RekeningTabungan.fromJson(Map<String, dynamic> json) {
    return RekeningTabungan(
      id: json['id'] as int,
      noRekening: json['no_rekening'] as String? ?? '',
      nasabahId: json['nasabah_id'] as int? ?? 0,
      nasabahNama: json['nasabah_nama'] as String? ?? '',
      saldoPokok: json['saldo_pokok'] as int? ?? 0,
      saldoWajib: json['saldo_wajib'] as int? ?? 0,
      saldoSukarela: json['saldo_sukarela'] as int? ?? 0,
      totalSaldo: json['total_saldo'] as int? ?? 0,
      saldoBisaTarik: json['saldo_bisa_tarik'] as int? ?? 0,
      punyaPinjamanAktif: json['punya_pinjaman_aktif'] as bool? ?? false,
      transaksi: json['transaksi'] != null
          ? (json['transaksi'] as List)
              .map((e) => TransaksiTabungan.fromJson(e))
              .toList()
          : null,
    );
  }
}

class TransaksiTabungan {
  final int id;
  final String tanggal;
  final String jenis;
  final String kategori;
  final int jumlah;
  final String keterangan;
  final String noBukti;

  TransaksiTabungan({
    required this.id,
    required this.tanggal,
    required this.jenis,
    required this.kategori,
    required this.jumlah,
    required this.keterangan,
    required this.noBukti,
  });

  factory TransaksiTabungan.fromJson(Map<String, dynamic> json) {
    return TransaksiTabungan(
      id: json['id'] as int,
      tanggal: json['tanggal'] as String? ?? '',
      jenis: json['jenis'] as String? ?? '',
      kategori: json['kategori'] as String? ?? '',
      jumlah: json['jumlah'] as int? ?? 0,
      keterangan: json['keterangan'] as String? ?? '',
      noBukti: json['no_bukti'] as String? ?? '',
    );
  }
}
