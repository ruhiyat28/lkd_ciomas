class Validators {
  static String? required(String? value, [String field = 'Field']) {
    if (value == null || value.trim().isEmpty) {
      return '$field wajib diisi';
    }
    return null;
  }

  static String? username(String? value) {
    if (value == null || value.trim().isEmpty) return 'Username wajib diisi';
    if (value.trim().length < 4) return 'Username minimal 4 karakter';
    return null;
  }

  static String? password(String? value) {
    if (value == null || value.isEmpty) return 'Password wajib diisi';
    if (value.length < 6) return 'Password minimal 6 karakter';
    return null;
  }

  static String? nik(String? value) {
    if (value == null || value.trim().isEmpty) return 'NIK wajib diisi';
    if (value.trim().length != 16) return 'NIK harus 16 digit';
    if (!RegExp(r'^\d{16}$').hasMatch(value.trim())) return 'NIK hanya angka';
    return null;
  }

  static String? noHp(String? value) {
    if (value == null || value.trim().isEmpty) return null;
    if (!RegExp(r'^0\d{8,13}$').hasMatch(value.trim())) {
      return 'Nomor HP tidak valid (mulai dengan 0, 9-14 digit)';
    }
    return null;
  }

  static String? jumlahPinjaman(String? value) {
    if (value == null || value.trim().isEmpty) return 'Jumlah wajib diisi';
    final n = int.tryParse(value.replaceAll(RegExp(r'[^0-9]'), ''));
    if (n == null || n <= 0) return 'Jumlah harus lebih dari 0';
    return null;
  }

  static String? kolekTinggi(String? value) {
    if (value == null || value.trim().isEmpty) return 'Tinggi badan wajib diisi';
    final n = int.tryParse(value);
    if (n == null || n < 100 || n > 250) return 'Tinggi tidak valid';
    return null;
  }
}
