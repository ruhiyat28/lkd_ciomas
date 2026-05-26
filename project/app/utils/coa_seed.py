"""
Chart of Accounts — BUM Desa Bersama LKD
Standar Kepmendesa 136/2022 — 4 Level, 7 Induk Akun
"""

# (kode, nama, level, saldo_normal, bisa_jurnal, parent_kode)
COA_DATA = [
    # ═══════ GOLONGAN 1 — ASET ═══════
    ('1.0.00.00','ASET',1,'debit',False,None),
    # Level 2
    ('1.1.00.00','Aset Lancar',2,'debit',False,'1.0.00.00'),
    ('1.2.00.00','Investasi',2,'debit',False,'1.0.00.00'),
    ('1.3.00.00','Aset Tetap',2,'debit',False,'1.0.00.00'),
    ('1.4.00.00','Aset Tak Berwujud',2,'debit',False,'1.0.00.00'),
    ('1.9.00.00','Aset Lain-lain',2,'debit',False,'1.0.00.00'),
    # Level 3 — Aset Lancar
    ('1.1.01.00','Kas',3,'debit',False,'1.1.00.00'),
    ('1.1.02.00','Setara Kas',3,'debit',False,'1.1.00.00'),
    ('1.1.03.00','Piutang',3,'debit',False,'1.1.00.00'),
    ('1.1.04.00','Penyisihan Piutang',3,'debit',False,'1.1.00.00'),
    ('1.1.05.00','Persediaan',3,'debit',False,'1.1.00.00'),
    ('1.1.06.00','Perlengkapan',3,'debit',False,'1.1.00.00'),
    ('1.1.07.00','Pembayaran Dimuka',3,'debit',False,'1.1.00.00'),
    ('1.1.98.00','Aset Lancar Lainnya',3,'debit',False,'1.1.00.00'),
    ('1.1.99.00','RK Unit',3,'debit',False,'1.1.00.00'),
    # Level 4 — Aset Lancar
    ('1.1.01.01','Kas Tunai',4,'debit',True,'1.1.01.00'),
    ('1.1.01.02','Kas di Bank BRI',4,'debit',True,'1.1.01.00'),
    ('1.1.01.03','Kas di Bank BJB',4,'debit',True,'1.1.01.00'),
    ('1.1.01.98','Kas Kecil',4,'debit',True,'1.1.01.00'),
    ('1.1.02.01','Deposito <= 3 bulan',4,'debit',True,'1.1.02.00'),
    ('1.1.02.99','Setara Kas Lainnya',4,'debit',True,'1.1.02.00'),
    ('1.1.03.01','Piutang Dana Bergulir',4,'debit',True,'1.1.03.00'),
    ('1.1.03.02','Piutang Usaha',4,'debit',True,'1.1.03.00'),
    ('1.1.03.03','Piutang kepada Pegawai',4,'debit',True,'1.1.03.00'),
    ('1.1.03.99','Piutang Lainnya',4,'debit',True,'1.1.03.00'),
    ('1.1.04.01','Penyisihan Piutang DBM Tak Tertagih',4,'kredit',True,'1.1.04.00'),
    ('1.1.04.02','Penyisihan Piutang Tak Tertagih',4,'kredit',True,'1.1.04.00'),
    ('1.1.04.99','Penyisihan Piutang Lainnya Tak Tertagih',4,'kredit',True,'1.1.04.00'),
    ('1.1.05.01','Persediaan Barang Dagangan',4,'debit',True,'1.1.05.00'),
    ('1.1.05.02','Persediaan Bahan Baku',4,'debit',True,'1.1.05.00'),
    ('1.1.05.03','Persediaan Dalam Proses',4,'debit',True,'1.1.05.00'),
    ('1.1.05.04','Persediaan Barang Jadi',4,'debit',True,'1.1.05.00'),
    ('1.1.06.01','Alat Tulis Kantor (ATK)',4,'debit',True,'1.1.06.00'),
    ('1.1.07.01','Sewa dibayar Dimuka',4,'debit',True,'1.1.07.00'),
    ('1.1.07.02','Asuransi Dibayar Dimuka',4,'debit',True,'1.1.07.00'),
    ('1.1.07.03','PPh 25',4,'debit',True,'1.1.07.00'),
    ('1.1.07.04','PPN Masukan',4,'debit',True,'1.1.07.00'),
    ('1.1.98.01','Aset Lancar Lainnya',4,'debit',True,'1.1.98.00'),
    ('1.1.99.01','RK Unit Nila Bioflok',4,'debit',True,'1.1.99.00'),
    ('1.1.99.02','RK Unit Lele',4,'debit',True,'1.1.99.00'),
    ('1.1.99.03','RK Unit Kambing',4,'debit',True,'1.1.99.00'),
    # Level 3 — Investasi
    ('1.2.01.00','Investasi',3,'debit',False,'1.2.00.00'),
    # Level 4 — Investasi
    ('1.2.01.01','Deposito > 3 bulan',4,'debit',True,'1.2.01.00'),
    ('1.2.01.02','Investasi Lainnya',4,'debit',True,'1.2.01.00'),
    # Level 3 — Aset Tetap
    ('1.3.01.00','Tanah',3,'debit',False,'1.3.00.00'),
    ('1.3.02.00','Kendaraan',3,'debit',False,'1.3.00.00'),
    ('1.3.03.00','Peralatan dan Mesin',3,'debit',False,'1.3.00.00'),
    ('1.3.04.00','Meubelair',3,'debit',False,'1.3.00.00'),
    ('1.3.05.00','Gedung dan Bangunan',3,'debit',False,'1.3.00.00'),
    ('1.3.06.00','Konstruksi Dalam Pengerjaan',3,'debit',False,'1.3.00.00'),
    ('1.3.07.00','Akumulasi Penyusutan Aset Tetap',3,'debit',False,'1.3.00.00'),
    ('1.3.99.00','Aset Tetap Lainnya',3,'debit',False,'1.3.00.00'),
    # Level 4 — Aset Tetap
    ('1.3.01.01','Tanah',4,'debit',True,'1.3.01.00'),
    ('1.3.02.01','Kendaraan',4,'debit',True,'1.3.02.00'),
    ('1.3.03.01','Peralatan dan Mesin',4,'debit',True,'1.3.03.00'),
    ('1.3.04.01','Meubelair',4,'debit',True,'1.3.04.00'),
    ('1.3.05.01','Gedung dan Bangunan',4,'debit',True,'1.3.05.00'),
    ('1.3.06.01','Konstruksi Dalam Pengerjaan',4,'debit',True,'1.3.06.00'),
    ('1.3.07.01','Akumulasi Penyusutan Kendaraan',4,'kredit',True,'1.3.07.00'),
    ('1.3.07.02','Akumulasi Penyusutan Peralatan dan mesin',4,'kredit',True,'1.3.07.00'),
    ('1.3.07.03','Akumulasi Penyusutan Meubelair',4,'kredit',True,'1.3.07.00'),
    ('1.3.07.04','Akumulasi Penyusutan Gedung dan Bangunan',4,'kredit',True,'1.3.07.00'),
    ('1.3.99.99','Aset Tetap Lainnya',4,'debit',True,'1.3.99.00'),
    # Level 3 — Aset Tak Berwujud
    ('1.4.01.00','Aset Tak Berwujud',3,'debit',False,'1.4.00.00'),
    ('1.4.02.00','Amortisasi Aset Tak Berwujud',3,'debit',False,'1.4.00.00'),
    # Level 4 — Aset Tak Berwujud
    ('1.4.01.01','Software',4,'debit',True,'1.4.01.00'),
    ('1.4.01.02','Patent',4,'debit',True,'1.4.01.00'),
    ('1.4.01.03','Trademark',4,'debit',True,'1.4.01.00'),
    ('1.4.02.01','Amortisasi Aset Tak Berwujud',4,'kredit',True,'1.4.02.00'),
    # Level 3 — Aset Lain-lain
    ('1.9.01.00','Aset Lain-lain',3,'debit',False,'1.9.00.00'),
    ('1.9.02.00','Penyusutan Aset Lain-lain',3,'debit',False,'1.9.00.00'),
    # Level 4 — Aset Lain-lain
    ('1.9.01.01','Aset Lain-lain',4,'debit',True,'1.9.01.00'),
    ('1.9.02.01','Akumulasi Penyusutan Aset Lain-lain',4,'kredit',True,'1.9.02.00'),

    # ═══════ GOLONGAN 2 — KEWAJIBAN ═══════
    ('2.0.00.00','KEWAJIBAN',1,'kredit',False,None),
    # Level 2
    ('2.1.00.00','Kewajiban Jangka Pendek',2,'kredit',False,'2.0.00.00'),
    ('2.2.00.00','Kewajiban Jangka Panjang',2,'kredit',False,'2.0.00.00'),
    # Level 3 — Kewajiban Jangka Pendek
    ('2.1.01.00','Utang Usaha',3,'kredit',False,'2.1.00.00'),
    ('2.1.02.00','Utang Pajak',3,'kredit',False,'2.1.00.00'),
    ('2.1.03.00','Utang Gaji/Upah dan Tunjangan',3,'kredit',False,'2.1.00.00'),
    ('2.1.04.00','Utang Utilitas',3,'kredit',False,'2.1.00.00'),
    ('2.1.05.00','Utang Kepada Pihak Ketiga Jk. Pendek',3,'kredit',False,'2.1.00.00'),
    ('2.1.99.00','Utang Jk. Pendek Lainnya',3,'kredit',False,'2.1.00.00'),
    # Level 4 — Kewajiban Jangka Pendek
    ('2.1.01.01','Utang Usaha',4,'kredit',True,'2.1.01.00'),
    ('2.1.02.01','PPN Keluaran',4,'kredit',True,'2.1.02.00'),
    ('2.1.02.02','PPh 21',4,'kredit',True,'2.1.02.00'),
    ('2.1.02.03','PPh 23',4,'kredit',True,'2.1.02.00'),
    ('2.1.02.04','PPh 29',4,'kredit',True,'2.1.02.00'),
    ('2.1.03.01','Utang Gaji dan Tunjangan',4,'kredit',True,'2.1.03.00'),
    ('2.1.03.02','Utang Gaji/Upah Karyawan',4,'kredit',True,'2.1.03.00'),
    ('2.1.04.01','Utang Listrik',4,'kredit',True,'2.1.04.00'),
    ('2.1.04.02','Utang Telpon/Internet',4,'kredit',True,'2.1.04.00'),
    ('2.1.04.03','Utang Utilitas Lainnya',4,'kredit',True,'2.1.04.00'),
    ('2.1.05.01','Utang Kepada Pihak Ketiga Jk. pendek',4,'kredit',True,'2.1.05.00'),
    ('2.1.05.99','Utang Kepada Pihak Ketiga Jk. Pendek Lainnya',4,'kredit',True,'2.1.05.00'),
    ('2.1.99.99','Utang Jk. Pendek Lainnya',4,'kredit',True,'2.1.99.00'),
    # Level 3 — Kewajiban Jangka Panjang
    ('2.2.01.00','Utang ke Bank',3,'kredit',False,'2.2.00.00'),
    ('2.2.02.00','Utang Kepada Pihak Ketiga Jk. Panjang',3,'kredit',False,'2.2.00.00'),
    ('2.2.99.00','Utang Kepada Pihak Ketiga Jk. Panjang Lainnya',3,'kredit',False,'2.2.00.00'),
    # Level 4 — Kewajiban Jangka Panjang
    ('2.2.01.01','Utang ke Bank',4,'kredit',True,'2.2.01.00'),
    ('2.2.02.01','Utang Kepada Pihak Ketiga Jk. Panjang',4,'kredit',True,'2.2.02.00'),
    ('2.2.99.99','Utang Kepada Pihak Ketiga Jk. Panjang Lainnya',4,'kredit',True,'2.2.99.00'),

    # ═══════ GOLONGAN 3 — EKUITAS ═══════
    ('3.0.00.00','EKUITAS',1,'kredit',False,None),
    # Level 2
    ('3.1.00.00','Modal Pemilik',2,'kredit',False,'3.0.00.00'),
    ('3.2.00.00','Pengambilan oleh Pemilik',2,'kredit',False,'3.0.00.00'),
    ('3.3.00.00','Saldo Laba',2,'kredit',False,'3.0.00.00'),
    ('3.4.00.00','Modal Donasi/Sumbangan',2,'kredit',False,'3.0.00.00'),
    ('3.8.00.00','RK Pusat',2,'kredit',False,'3.0.00.00'),
    ('3.9.00.00','Ikhtisar Laba Rugi',2,'kredit',False,'3.0.00.00'),
    # Level 3 — Modal Pemilik
    ('3.1.01.00','Penyertaan Modal Desa-Desa',3,'kredit',False,'3.1.00.00'),
    ('3.1.02.00','Penyertaan Modal Masyarakat Desa',3,'kredit',False,'3.1.00.00'),
    # Level 3 — Pengambilan oleh Pemilik
    ('3.2.01.00','Bagi Hasil Penyertaan Modal Desa-Desa',3,'debit',False,'3.2.00.00'),
    ('3.2.02.00','Bagi Hasil Penyertaan Modal Masyarakat',3,'debit',False,'3.2.00.00'),
    # Level 3 — Saldo Laba
    ('3.3.01.00','Saldo Laba',3,'kredit',False,'3.3.00.00'),
    # Level 3 — Modal Donasi/Sumbangan
    ('3.4.01.00','Modal Donasi/Sumbangan',3,'kredit',False,'3.4.00.00'),
    # Level 3 — RK Pusat
    ('3.8.01.00','RK Pusat',3,'kredit',False,'3.8.00.00'),
    # Level 3 — Ikhtisar Laba Rugi
    ('3.9.01.00','Ikhtisar Laba Rugi',3,'kredit',False,'3.9.00.00'),
    # Level 4 — Ekuitas — Modal Pemilik
    ('3.1.01.01','Penyertaan Modal Desa Ujung Tebu',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.02','Penyertaan Modal Desa Cisitu',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.03','Penyertaan Modal Desa Siketug',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.04','Penyertaan Modal Desa Lebak',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.05','Penyertaan Modal Desa Citaman',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.06','Penyertaan Modal Desa Pondok Kahuru',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.07','Penyertaan Modal Desa Sukabares',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.08','Penyertaan Modal Desa Sukadana',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.09','Penyertaan Modal Desa Sukarena',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.10','Penyertaan Modal Desa Cemplang',4,'kredit',True,'3.1.01.00'),
    ('3.1.01.11','Penyertaan Modal Desa Panyaungan Jaya',4,'kredit',True,'3.1.01.00'),
    ('3.1.02.01','Penyertaan Modal Masyarakat DBM eks PNPM MPd',4,'kredit',True,'3.1.02.00'),
    ('3.1.02.02','Penyertaan Modal Masyarakat Desa',4,'kredit',True,'3.1.02.00'),
    # Level 4 — Ekuitas — Pengambilan oleh Pemilik
    ('3.2.01.01','Bagi Hasil Penyertaan Modal Desa Ujung Tebu',4,'debit',True,'3.2.01.00'),
    ('3.2.01.02','Bagi Hasil Penyertaan Modal Desa Cisitu',4,'debit',True,'3.2.01.00'),
    ('3.2.01.03','Bagi Hasil Penyertaan Modal Desa Siketug',4,'debit',True,'3.2.01.00'),
    ('3.2.01.04','Bagi Hasil Penyertaan Modal Desa Lebak',4,'debit',True,'3.2.01.00'),
    ('3.2.01.05','Bagi Hasil Penyertaan Modal Desa Citaman',4,'debit',True,'3.2.01.00'),
    ('3.2.01.06','Bagi Hasil Penyertaan Modal Desa Pondok Kahuru',4,'debit',True,'3.2.01.00'),
    ('3.2.01.07','Bagi Hasil Penyertaan Modal Desa Sukabares',4,'debit',True,'3.2.01.00'),
    ('3.2.01.08','Bagi Hasil Penyertaan Modal Desa Sukadana',4,'debit',True,'3.2.01.00'),
    ('3.2.01.09','Bagi Hasil Penyertaan Modal Desa Sukarena',4,'debit',True,'3.2.01.00'),
    ('3.2.01.10','Bagi Hasil Penyertaan Modal Desa Cemplang',4,'debit',True,'3.2.01.00'),
    ('3.2.01.11','Bagi Hasil Penyertaan Modal Desa Panyaungan Jaya',4,'debit',True,'3.2.01.00'),
    ('3.2.02.01','Bagi Hasil Penyertaan Modal Masyarakat eks DBM PNPM MPd',4,'debit',True,'3.2.02.00'),
    ('3.2.02.02','Bagi Hasil Penyertaan Modal Masyakarat Desa',4,'debit',True,'3.2.02.00'),
    # Level 4 — Ekuitas — Saldo Laba
    ('3.3.01.01','Saldo Laba Tidak Dicadangkan',4,'kredit',True,'3.3.01.00'),
    ('3.3.01.02','Saldo Laba Dicadangkan',4,'kredit',True,'3.3.01.00'),
    # Level 4 — Ekuitas — Modal Donasi/Sumbangan
    ('3.4.01.01','Modal Donasi/Sumbangan',4,'kredit',True,'3.4.01.00'),
    # Level 4 — Ekuitas — RK Pusat
    ('3.8.01.01','RK Pusat',4,'debit',True,'3.8.01.00'),
    # Level 4 — Ekuitas — Ikhtisar Laba Rugi
    ('3.9.01.01','Ikhtisar Laba Rugi',4,'kredit',True,'3.9.01.00'),

    # ═══════ GOLONGAN 4 — PENDAPATAN ═══════
    ('4.0.00.00','PENDAPATAN',1,'kredit',False,None),
    # Level 2
    ('4.1.00.00','Pendapatan Jasa',2,'kredit',False,'4.0.00.00'),
    ('4.2.00.00','Pendapatan Penjualan Barang Dagangan',2,'kredit',False,'4.0.00.00'),
    # Level 3 — Pendapatan Jasa
    ('4.1.01.00','Pendapatan Jasa Dana Bergulir',3,'kredit',False,'4.1.00.00'),
    ('4.1.02.00','Pendapatan Jasa Pelayanan',3,'kredit',False,'4.1.00.00'),
    ('4.1.03.00','Pendapatan Sewa',3,'kredit',False,'4.1.00.00'),
    # Level 3 — Pendapatan Penjualan Barang Dagangan
    ('4.2.01.00','Pendapatan Penjualan Barang Dagangan',3,'kredit',False,'4.2.00.00'),
    # Level 4 — Pendapatan
    ('4.1.01.01','Pendapatan Jasa Dana Bergulir',4,'kredit',True,'4.1.01.00'),
    ('4.1.01.02','Pendapatan Denda',4,'kredit',True,'4.1.01.00'),
    ('4.1.02.01','Pendapatan Jasa Pelayanan',4,'kredit',True,'4.1.02.00'),
    ('4.1.03.01','Pendapatan Sewa Gedung Peralatan',4,'kredit',True,'4.1.03.00'),
    ('4.1.03.02','Pendapatan Sewa Mobil',4,'kredit',True,'4.1.03.00'),
    ('4.1.03.99','Pendapatan Sewa Lainnya',4,'kredit',True,'4.1.03.00'),
    ('4.2.01.01','Pendapatan Penjualan Barang Dagangan',4,'kredit',True,'4.2.01.00'),

    # ═══════ GOLONGAN 5 — HPP ═══════
    ('5.0.00.00','HARGA POKOK PRODUK DAN PENJUALAN',1,'debit',False,None),
    # Level 2
    ('5.1.00.00','Harga Pokok Penjualan Barang Dagangan',2,'debit',False,'5.0.00.00'),
    ('5.2.00.00','Harga Pokok Produksi',2,'debit',False,'5.0.00.00'),
    # Level 3
    ('5.1.01.00','Harga Pokok Penjualan Barang Dagangan',3,'debit',False,'5.1.00.00'),
    ('5.2.01.00','Harga Pokok Produksi',3,'debit',False,'5.2.00.00'),
    # Level 4 — HPP
    ('5.1.01.01','Harga Pokok Penjualan Barang Dagangan',4,'debit',True,'5.1.01.00'),
    ('5.2.01.01','Harga Pokok Produksi',4,'debit',True,'5.2.01.00'),

    # ═══════ GOLONGAN 6 — BEBAN-BEBAN ═══════
    ('6.0.00.00','BEBAN-BEBAN',1,'debit',False,None),
    # Level 2
    ('6.1.00.00','Beban Administrasi dan Umum',2,'debit',False,'6.0.00.00'),
    ('6.2.00.00','Beban Operasional',2,'debit',False,'6.0.00.00'),
    ('6.3.00.00','Beban Pemasaran',2,'debit',False,'6.0.00.00'),
    # Level 3 — Beban Administrasi dan Umum
    ('6.1.01.00','Beban Pegawai Badian Adum',3,'debit',False,'6.1.00.00'),
    ('6.1.02.00','Beban Perlengkapan',3,'debit',False,'6.1.00.00'),
    ('6.1.03.00','Beban Pemeliharaan dan Berbaikan',3,'debit',False,'6.1.00.00'),
    ('6.1.04.00','Beban Utilitas',3,'debit',False,'6.1.00.00'),
    ('6.1.05.00','Beban Sewa dan Asuransi',3,'debit',False,'6.1.00.00'),
    ('6.1.06.00','Beban Kebersihan dan Keamanan',3,'debit',False,'6.1.00.00'),
    ('6.1.07.00','Beban Penyusutan dan Amortisasi',3,'debit',False,'6.1.00.00'),
    ('6.1.99.00','Beban Administrasi dan Umum Lainnya',3,'debit',False,'6.1.00.00'),
    # Level 4 — Beban Administrasi dan Umum
    ('6.1.01.01','Beban Gaji dan Tunjangan',4,'debit',True,'6.1.01.00'),
    ('6.1.02.01','Beban Alat Tulis Kantor (ATK)',4,'debit',True,'6.1.02.00'),
    ('6.1.02.02','Beban Fotocopy',4,'debit',True,'6.1.02.00'),
    ('6.1.07.01','Beban Penyisihan Piutang Dana Bergulir',4,'debit',True,'6.1.07.00'),
    ('6.1.07.02','Beban Penyusutan Kendaraan',4,'debit',True,'6.1.07.00'),
    ('6.1.07.03','Beban Penyusutan Peralatan dan Mesin',4,'debit',True,'6.1.07.00'),
    ('6.1.07.04','Beban Penyusutan Meubelair',4,'debit',True,'6.1.07.00'),
    ('6.1.07.05','Beban Penyusutan Gedung dan Bangunan',4,'debit',True,'6.1.07.00'),
    ('6.1.07.06','Beban Amortisasi Aset Tak Berwujud',4,'debit',True,'6.1.07.00'),
    ('6.1.99.01','Beban Administrasi dan Umum Lainnya',4,'debit',True,'6.1.99.00'),
    # Level 3 — Beban Operasional
    ('6.2.01.00','Beban Pegawai Bagian Operasional',3,'debit',False,'6.2.00.00'),
    ('6.2.02.00','Beban Pemeliharaan dan Perbaikan',3,'debit',False,'6.2.00.00'),
    ('6.2.03.00','Beban Keamanan',3,'debit',False,'6.2.00.00'),
    ('6.2.99.00','Beban Operasional Lainnya',3,'debit',False,'6.2.00.00'),
    # Level 3 — Beban Pemasaran
    ('6.3.01.00','Beban Pegawai Bagian Pemasaran',3,'debit',False,'6.3.00.00'),
    ('6.3.02.00','Beban Iklan dan Promosi',3,'debit',False,'6.3.00.00'),
    ('6.3.99.00','Beban Pemasaran Lainnya',3,'debit',False,'6.3.00.00'),

    # ═══════ GOLONGAN 7 — PENDAPATAN DAN BEBAN LAIN-LAIN ═══════
    ('7.0.00.00','PENDAPATAN DAN BEBAN LAIN-LAIN',1,'kredit',False,None),
    # Level 2
    ('7.1.00.00','Pendapatan Lain-lain',2,'kredit',False,'7.0.00.00'),
    ('7.2.00.00','Beban Lain-lain',2,'debit',False,'7.0.00.00'),
    ('7.3.00.00','Beban Pajak',2,'debit',False,'7.0.00.00'),
    # Level 3 — Pendapatan Lain-lain
    ('7.1.01.00','Pendapatan dari Bank',3,'kredit',False,'7.1.00.00'),
    ('7.1.02.00','Pendapatan Deviden',3,'kredit',False,'7.1.00.00'),
    ('7.1.03.00','Pendapatan Denda',3,'kredit',False,'7.1.00.00'),
    ('7.1.04.00','Pendapatan Iklan',3,'kredit',False,'7.1.00.00'),
    ('7.1.05.00','Pendapatan Penjualan Aset Tetap',3,'kredit',False,'7.1.00.00'),
    ('7.1.99.00','Pendapatan Lain-lain Lainnya',3,'kredit',False,'7.1.00.00'),
    # Level 3 — Beban Lain-lain
    ('7.2.01.00','Beban Bank',3,'debit',False,'7.2.00.00'),
    ('7.2.02.00','Beban Bunga',3,'debit',False,'7.2.00.00'),
    ('7.2.03.00','Beban Denda',3,'debit',False,'7.2.00.00'),
    ('7.2.04.00','Beban Penjualan Aset Tetap',3,'debit',False,'7.2.00.00'),
    ('7.2.99.00','Beban Lain-lain Lainnya',3,'debit',False,'7.2.00.00'),
    # Level 3 — Beban Pajak
    ('7.3.01.00','Beban Pajak',3,'debit',False,'7.3.00.00'),
    # Level 4 — Pendapatan dan Beban Lain-lain
    ('7.1.01.01','Pendapatan Bunga Bank',4,'kredit',True,'7.1.01.00'),
    ('7.1.01.02','Pendapatan Fee',4,'kredit',True,'7.1.01.00'),
    ('7.1.02.01','Pendapatan Deviden',4,'kredit',True,'7.1.02.00'),
    ('7.1.03.01','Pendapatan Denda',4,'kredit',True,'7.1.03.00'),
    ('7.1.04.01','Pendapatan Iklan',4,'kredit',True,'7.1.04.00'),
    ('7.1.05.01','Pendapatan Penjualan Aset Tetap',4,'kredit',True,'7.1.05.00'),
    ('7.1.99.99','Pendapatan Lain-lain Lainnya',4,'kredit',True,'7.1.99.00'),
    ('7.2.01.01','Beban Administrasi Bank',4,'debit',True,'7.2.01.00'),
    ('7.2.02.01','Beban Bunga',4,'debit',True,'7.2.02.00'),
    ('7.2.03.01','Beban Denda',4,'debit',True,'7.2.03.00'),
    ('7.2.04.01','Beban Penjualan Aset Tetap',4,'debit',True,'7.2.04.00'),
    ('7.2.99.99','Beban Lain-lain Lainnya',4,'debit',True,'7.2.99.00'),
    ('7.3.01.01','Beban PPh Final',4,'debit',True,'7.3.01.00'),
]

GOLONGAN_MAP = {
    1:'Aset', 2:'Kewajiban', 3:'Ekuitas',
    4:'Pendapatan', 5:'HPP',
    6:'Beban-Beban', 7:'Pendapatan dan Beban Lain-lain',
}

# Akun kunci auto-jurnal — kode level 4
AKUN_KAS              = '1.1.01.01'
AKUN_KAS_BANK         = '1.1.01.02'
AKUN_PIUTANG_PINJAMAN = '1.1.03.01'
AKUN_CADANGAN_RISIKO  = '1.1.04.01'
AKUN_PENDAPATAN_JASA  = '4.1.01.01'
AKUN_BEBAN_CADANGAN   = '6.1.07.01'


def seed_coa(force=False):
    from app.models import db, AkunCOA
    if force:
        AkunCOA.query.delete()
        db.session.flush()
    elif AkunCOA.query.count() > 0:
        return
    kode_map = {}
    for row in COA_DATA:
        kode, nama, level, saldo_normal, bisa_jurnal, parent_kode = row
        gol = int(kode.split('.')[0])
        a = AkunCOA(
            kode=kode, nama=nama, golongan=gol,
            golongan_nama=GOLONGAN_MAP.get(gol, ''),
            saldo_normal=saldo_normal, level=level,
            bisa_jurnal=bisa_jurnal, aktif=True,
        )
        db.session.add(a)
        kode_map[kode] = a
    db.session.flush()
    for row in COA_DATA:
        kode, _, _, _, _, parent_kode = row
        if parent_kode and parent_kode in kode_map:
            kode_map[kode].parent_id = kode_map[parent_kode].id
    db.session.commit()
    print(f"[seed_coa] {len(COA_DATA)} akun COA seeded (level 1-4)")


def get_akun_by_kode(kode):
    from app.models import AkunCOA
    return AkunCOA.query.filter_by(kode=kode).first()
