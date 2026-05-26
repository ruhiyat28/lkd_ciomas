class ApiEndpoints {
  ApiEndpoints._();

  static const String baseUrl = 'https://apps.ciomas.web.id/api';

  // Auth
  static const String login = '/auth/login';
  static const String me = '/auth/me';
  static const String changePassword = '/auth/change-password';
  static const String register = '/auth/register';

  // Config
  static const String config = '/config';

  // Dashboard
  static const String dashboard = '/dashboard';

  // Nasabah
  static const String nasabah = '/nasabah';
  static String nasabahDetail(int id) => '/nasabah/$id';
  static String nasabahApprove(int id) => '/nasabah/$id/approve';
  static const String nasabahCount = '/nasabah/count';
  static const String nasabahSaya = '/nasabah/saya';

  // Pinjaman
  static const String pinjaman = '/pinjaman';
  static String pinjamanDetail(int id) => '/pinjaman/$id';
  static const String hitungAngsuran = '/pinjaman/hitung-angsuran';

  // Pembayaran
  static const String pembayaran = '/pembayaran';
  static String pinjamanAngsuran(int id) => '/pinjaman/$id/angsuran';

  // Tabungan
  static const String tabungan = '/tabungan';
  static const String tabunganSetor = '/tabungan/setor';
  static const String tabunganTarik = '/tabungan/tarik';

  // Upload
  static const String upload = '/upload';
  static const String uploadGantiFoto = '/upload/ganti-foto';

  // FCM
  static const String fcmRegister = '/fcm/register';
  static const String fcmUnregister = '/fcm/unregister';

  // Bonus
  static const String bonusSaya = '/bonus/saya';

  // Verifikasi
  static String verifikasiPinjaman(int id) => '/pinjaman/$id/verifikasi';

  // Pembayaran ACC
  static String pembayaranAcc(int id) => '/pembayaran/$id/acc';
  static String pembayaranTolak(int id) => '/pembayaran/$id/tolak';

  // Pengumuman
  static const String pengumuman = '/pengumuman';

  // Media serving
  static String media(String path) => '/media/$path';

  // UMKM
  static const String umkmPenjualStatus = '/umkm/penjual/status';
  static const String umkmPenjualDaftar = '/umkm/penjual/daftar';
  static const String umkmPenjual = '/umkm/penjual';
  static const String umkmPenjualAll = '/umkm/penjual/all';
  static String umkmPenjualProses(int id) => '/umkm/penjual/$id/proses';
  static const String umkmProduk = '/umkm/produk';
  static String umkmProdukDetail(int id) => '/umkm/produk/$id';
  static String umkmProdukGambar(int id) => '/umkm/produk/$id/gambar';
  static const String umkmPesanan = '/umkm/pesanan';
  static String umkmPesananDetail(int id) => '/umkm/pesanan/$id';
  static String umkmPesananStatus(int id) => '/umkm/pesanan/$id/status';
  static String umkmPesananBukti(int id) => '/umkm/pesanan/$id/bukti';
  static String umkmPesananKonfirmasiBayar(int id) => '/umkm/pesanan/$id/konfirmasi-bayar';
  static const String umkmRekening = '/umkm/rekening';
}
