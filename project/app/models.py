from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import math

db = SQLAlchemy()


# ─────────────────────────────────────────────────────────────
# Fungsi standalone — bisa dipanggil dari routes, import, dll
# ─────────────────────────────────────────────────────────────
def hitung_angsuran_bulat(jumlah, tenor, jasa_persen):
    """
    Hitung angsuran dengan pembulatan ke atas kelipatan 100.

    Contoh: pinjam 5.000.000 / 12 bulan @ 1,5%
        pokok_raw      = 5.000.000 / 12 = 416.666,67
        pokok_bulat    = ceil(416.666,67 / 100) * 100 = 416.700   ← dibulatkan ke atas
        jasa_bulat     = 5.000.000 * 1,5% = 75.000
        total/bln      = 416.700 + 75.000 = 491.700
        pokok_terakhir = 5.000.000 - (416.700 * 11) = 416.300     ← menggenapkan
        total_terakhir = 416.300 + 75.000 = 491.300

    Return dict:
        pokok          → angsuran pokok per bulan (sudah bulat)
        jasa           → jasa per bulan (flat dari pokok awal)
        total          → pokok + jasa per bulan
        pokok_terakhir → angsuran pokok bulan terakhir (penggenap)
        total_terakhir → pokok_terakhir + jasa
    """
    jumlah    = int(jumlah)
    tenor     = int(tenor)
    jasa_pct  = float(jasa_persen)

    if tenor <= 0 or jumlah <= 0:
        return {'pokok': 0, 'jasa': 0, 'total': 0, 'pokok_terakhir': 0, 'total_terakhir': 0}

    # Bulatkan pokok ke atas kelipatan 100
    pokok_raw   = jumlah / tenor
    pokok_bulat = math.ceil(pokok_raw / 100) * 100

    # Jasa flat (bulatkan ke Rp terdekat, tidak ke 100)
    jasa_bulat  = round(jumlah * jasa_pct / 100)

    # Angsuran terakhir menggenapkan sisa pokok
    # Pastikan tidak negatif (edge case: jumlah < pokok_bulat * (tenor-1))
    pokok_terakhir = jumlah - pokok_bulat * (tenor - 1)
    if pokok_terakhir <= 0:
        # Kalau terjadi: distribusikan ulang dengan bulatkan ke bawah
        pokok_bulat    = math.floor(pokok_raw / 100) * 100
        pokok_terakhir = jumlah - pokok_bulat * (tenor - 1)

    return {
        'pokok'         : pokok_bulat,
        'jasa'          : jasa_bulat,
        'total'         : pokok_bulat + jasa_bulat,
        'pokok_terakhir': pokok_terakhir,
        'total_terakhir': pokok_terakhir + jasa_bulat,
    }


def hitung_angsuran_terakhir(jumlah, angsuran_pokok, tenor):
    """
    Dipakai saat import: user memberi angsuran_pokok manual,
    sistem menghitung angsuran terakhir agar total = jumlah.

    Contoh: jumlah=5.000.000, angsuran_pokok=416.700, tenor=12
        pokok_terakhir = 5.000.000 - (416.700 * 11) = 416.300
    """
    jumlah         = int(jumlah)
    angsuran_pokok = int(angsuran_pokok)
    tenor          = int(tenor)
    if tenor <= 1:
        return jumlah
    pokok_terakhir = jumlah - angsuran_pokok * (tenor - 1)
    # Validasi: tidak boleh negatif atau lebih besar dari 2x angsuran normal
    if pokok_terakhir <= 0:
        pokok_terakhir = angsuran_pokok  # fallback
    return pokok_terakhir


# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False, index=True)
    nama_lengkap  = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='kredit', index=True)
    kode_desa     = db.Column(db.String(5), nullable=True, index=True)  # Untuk role kader_desa
    aktif         = db.Column(db.Boolean, default=True, index=True)
    nasabah_id_fk = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tanda_tangan  = db.Column(db.String(255), nullable=True)
    pembina_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

# Relationship
    nasabah = db.relationship('Nasabah', backref='user_account', uselist=False, 
                     foreign_keys='User.nasabah_id_fk')
    pembina = db.relationship('User', remote_side='User.id', backref='kader_binaan',
                      foreign_keys='User.pembina_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Roles: admin, manajer_lkd, kredit, keuangan, tata_usaha, verifikator, penagih, kasir, staf, kader_desa
    def is_admin(self):        return self.role == 'admin'
    def is_kasir(self):        return self.role == 'kasir'
    def is_staf(self):         return self.role == 'staf'
    def is_kredit(self):       return self.role == 'kredit'
    def is_keuangan(self):     return self.role == 'keuangan'
    def is_tu(self):           return self.role == 'tata_usaha'
    def is_manajer(self):      return self.role == 'manajer_lkd'
    def is_verifikator(self):  return self.role == 'verifikator'
    def is_penagih(self):      return self.role == 'penagih'
    def is_nasabah(self):      return self.role == 'nasabah'
    def is_kader(self):        return self.role == 'kader_desa'

    ROLE_LABELS = {
        'admin'       : 'Admin / Direktur',
        'manajer_lkd' : 'Manajer LKD',
        'kredit'      : 'Bagian Kredit',
        'keuangan'    : 'Bagian Keuangan',
        'tata_usaha'  : 'Tata Usaha',
        'verifikator' : 'Verifikator',
        'penagih'     : 'Penagih',
        'kasir'       : 'Kasir',
        'staf'        : 'Staf',
        'nasabah'     : 'Nasabah',
        'kader_desa'  : 'Kader Desa',
    }

    def role_label(self):
        return self.ROLE_LABELS.get(self.role, self.role)

    def can_write_nasabah(self):
        return self.role in ('admin','manajer_lkd','kredit','tata_usaha', 'staf', 'kader_desa')

    def can_write_pinjaman(self):
        return self.role in ('admin','manajer_lkd','kredit','verifikator', 'staf', 'kader_desa')

    def can_write_pembayaran(self):
        return self.role in ('admin','manajer_lkd','keuangan','kredit','tata_usaha', 'kasir', 'kader_desa', 'penagih', 'staf')

    def can_view_akuntansi(self):
        return self.role in ('admin','manajer_lkd','keuangan', 'kasir')

    def can_edit_delete(self):
        return self.role in ('admin','manajer_lkd','staf')

    def can_penagihan(self):
        return self.role in ('admin','manajer_lkd','kredit','penagih', 'staf', 'kader_desa')

    def can_acc_pembayaran(self):
        if self.role in ('admin', 'manajer_lkd', 'keuangan'):
            return True
        if self.id is None:
            return False
        return len([k for k in self.kader_binaan if k.id != self.id]) > 0

    def bisa_acc_pembayaran_ini(self, pembayaran):
        if self.role in ('admin', 'manajer_lkd', 'keuangan'):
            return True
        dari = User.query.get(pembayaran.created_by)
        if dari and dari.pembina_id == self.id:
            return True
        return False


class Nasabah(db.Model):
    __tablename__ = 'nasabah'
    id                  = db.Column(db.Integer, primary_key=True)
    nasabah_id          = db.Column(db.String(20), unique=True, nullable=False, index=True)
    jenis               = db.Column(db.String(15), nullable=False, default='perorangan', index=True)  # perorangan / kelompok
    kode_desa           = db.Column(db.String(5), nullable=False, index=True)
    nama_desa           = db.Column(db.String(64), nullable=False)
    nama                = db.Column(db.String(128), nullable=False)
    nik                 = db.Column(db.String(50), unique=True, nullable=False)
    tempat_lahir        = db.Column(db.String(64))
    tanggal_lahir       = db.Column(db.Date)
    jenis_kelamin       = db.Column(db.String(10))
    alamat              = db.Column(db.Text)
    no_hp               = db.Column(db.String(20))
    pekerjaan           = db.Column(db.String(64))
    nama_pasangan       = db.Column(db.String(128))
    nik_pasangan        = db.Column(db.String(20))
    no_hp_pasangan      = db.Column(db.String(20))
    foto                = db.Column(db.String(256))
    ktp                 = db.Column(db.String(256))
    kk                  = db.Column(db.String(256))
    surat_usaha         = db.Column(db.String(256))
    bukti_penghasilan   = db.Column(db.String(256))
    jaminan             = db.Column(db.String(256))
    surat_tanggung_renteng_nasabah = db.Column(db.String(256))
    surat_ijin_keluarga_nasabah    = db.Column(db.String(256))
    keterangan_jaminan  = db.Column(db.Text)
    status              = db.Column(db.String(20), default='aktif', index=True)  # aktif / calon
    keterangan_status   = db.Column(db.Text)  # Pesan dari admin (misal: minta upload berkas)
    tanda_tangan        = db.Column(db.String(255), nullable=True)
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by          = db.Column(db.Integer, db.ForeignKey('users.id'))

    pinjaman = db.relationship('Pinjaman', backref='nasabah', lazy=True)

    def dokumen_lengkap(self):
        return all([self.foto, self.ktp, self.kk,
                    self.surat_usaha, self.bukti_penghasilan, self.jaminan])

    def dokumen_status(self):
        return {
            'Pas Photo'                  : self.foto,
            'KTP'                        : self.ktp,
            'Kartu Keluarga'             : self.kk,
            'Surat Keterangan Usaha/Kerja': self.surat_usaha,
            'Bukti Penghasilan'          : self.bukti_penghasilan,
            'Jaminan'                    : self.jaminan,
        }


class Pinjaman(db.Model):
    __tablename__ = 'pinjaman'
    id                      = db.Column(db.Integer, primary_key=True)
    spk                     = db.Column(db.String(30), unique=True, nullable=False)
    jenis_pinjaman          = db.Column(db.String(10), nullable=False, default='reguler')  # reguler / spp
    nasabah_id_fk           = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False)
    jumlah_pinjaman         = db.Column(db.BigInteger, nullable=False)
    jasa_persen             = db.Column(db.Float, nullable=False, default=1.5)
    tenor                   = db.Column(db.Integer, nullable=False)
    tujuan                  = db.Column(db.Text)
    tanggal_pengajuan       = db.Column(db.Date, default=date.today)
    status                  = db.Column(db.String(30), default='pengajuan', index=True)
    jumlah_penolakan        = db.Column(db.Integer, default=0)
    tanggal_kunjungan       = db.Column(db.Date)
    petugas_kunjungan       = db.Column(db.String(128))
    hasil_kunjungan         = db.Column(db.Text)
    foto_kunjungan          = db.Column(db.String(100))
    rekomendasi             = db.Column(db.String(10))
    tanggal_acc             = db.Column(db.Date)
    catatan_direktur        = db.Column(db.Text)
    tanggal_cair            = db.Column(db.Date)
    tanggal_mulai_angsuran  = db.Column(db.Date)
    angsuran_pokok          = db.Column(db.BigInteger)
    angsuran_jasa           = db.Column(db.BigInteger)
    angsuran_total          = db.Column(db.BigInteger)
    angsuran_terakhir_pokok = db.Column(db.BigInteger)
    created_at              = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by              = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_by             = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at             = db.Column(db.DateTime)
    acc_by                  = db.Column(db.Integer, db.ForeignKey('users.id'))
    tanggal_spk             = db.Column(db.Date)
    surat_tanggung_renteng  = db.Column(db.String(256))
    surat_ijin_keluarga     = db.Column(db.String(256))

    pembayaran = db.relationship('Pembayaran', backref='pinjaman', lazy=True,
                                 cascade='all, delete-orphan',
                                 order_by='Pembayaran.tanggal_bayar')
    detail_spp = db.relationship('DetailSPP', backref='pinjaman', lazy=True,
                                 cascade='all, delete-orphan',
                                 order_by='DetailSPP.urut')
    jaminan_bpkb = db.relationship('JaminanBPKB', backref='pinjaman_terkait', lazy=True, cascade='all, delete-orphan')
    jaminan_shm  = db.relationship('JaminanSHM', backref='pinjaman_terkait', lazy=True, cascade='all, delete-orphan')
    jaminan_lain = db.relationship('JaminanLain', backref='pinjaman_terkait', lazy=True, cascade='all, delete-orphan')

    def hitung_angsuran(self):
        """Delegasi ke fungsi standalone hitung_angsuran_bulat."""
        return hitung_angsuran_bulat(
            jumlah=self.jumlah_pinjaman,
            tenor=self.tenor,
            jasa_persen=self.jasa_persen,
        )

    def get_jadwal_angsuran(self):
        if not self.tanggal_mulai_angsuran:
            return []
        jadwal = []
        from dateutil.relativedelta import relativedelta
        total_pokok_bayar, _ = self.get_realisasi_pembayaran()
        kum_pokok = 0
        today = date.today()
        for i in range(self.tenor):
            tgl    = self.tanggal_mulai_angsuran + relativedelta(months=i)
            is_last = (i == self.tenor - 1)
            pokok  = self.angsuran_terakhir_pokok if is_last else self.angsuran_pokok
            jasa   = self.angsuran_jasa
            kum_pokok += pokok
            lunas = total_pokok_bayar >= kum_pokok
            terlambat = (not lunas) and (tgl < today)
            jadwal.append({
                'ke'     : i + 1,
                'tanggal': tgl,
                'pokok'  : pokok,
                'jasa'   : jasa,
                'total'  : pokok + jasa,
                'lunas'  : lunas,
                'terlambat': terlambat,
            })
        return jadwal

    def get_realisasi_pembayaran(self):
        total_pokok = sum(p.bayar_pokok for p in self.pembayaran)
        total_jasa  = sum(p.bayar_jasa  for p in self.pembayaran)
        return total_pokok, total_jasa

    def get_saldo_pokok(self):
        total_pokok, _ = self.get_realisasi_pembayaran()
        return self.jumlah_pinjaman - total_pokok

    def get_tunggakan(self):
        if self.status != 'cair':
            return 0, 0, 0
        today  = date.today()
        jadwal = self.get_jadwal_angsuran()
        total_pokok_bayar, total_jasa_bayar = self.get_realisasi_pembayaran()

        total_pokok_jth = 0
        total_jasa_jth  = 0
        for j in jadwal:
            if j['tanggal'] <= today:
                total_pokok_jth += j['pokok']
                total_jasa_jth  += j['jasa']

        tunggak_pokok = max(0, total_pokok_jth - total_pokok_bayar)
        tunggak_jasa  = max(0, total_jasa_jth  - total_jasa_bayar)

        bulan_nunggak = 0
        if tunggak_pokok > 0 and self.angsuran_pokok:
            bulan_nunggak = math.ceil(tunggak_pokok / self.angsuran_pokok)

        return tunggak_pokok, tunggak_jasa, bulan_nunggak

    def get_kolektibilitas(self):
        _, _, bulan_nunggak = self.get_tunggakan()
        if bulan_nunggak == 0:   return 1, "Lancar"
        elif bulan_nunggak <= 2: return 2, "Kurang Lancar"
        elif bulan_nunggak <= 4: return 3, "Diragukan"
        elif bulan_nunggak <= 6: return 4, "Macet Ringan"
        else:                    return 5, "Macet"

    def get_target_angsuran(self):
        today  = date.today()
        jadwal = self.get_jadwal_angsuran()
        target_pokok = target_jasa = 0
        for j in jadwal:
            if j['tanggal'] <= today:
                target_pokok += j['pokok']
                target_jasa  += j['jasa']
        return target_pokok, target_jasa


class Pembayaran(db.Model):
    __tablename__ = 'pembayaran'
    id           = db.Column(db.Integer, primary_key=True)
    no_kuitansi  = db.Column(db.String(30), unique=True, nullable=False)
    pinjaman_id  = db.Column(db.Integer, db.ForeignKey('pinjaman.id', ondelete='CASCADE'), nullable=False)
    tanggal_bayar= db.Column(db.Date, default=date.today, index=True)
    jumlah_bayar = db.Column(db.BigInteger, nullable=False)
    bayar_pokok  = db.Column(db.BigInteger, default=0)
    bayar_jasa   = db.Column(db.BigInteger, default=0)
    angsuran_ke  = db.Column(db.Integer)
    keterangan   = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by   = db.Column(db.Integer, db.ForeignKey('users.id'))
    status_acc   = db.Column(db.String(20), default=None)  # None/kosong=langsung valid, 'menunggu'=butuh acc, 'diterima'=sudah di-acc, 'ditolak'=ditolak
    acc_by       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    acc_at       = db.Column(db.DateTime, nullable=True)
    transaksi_tabungan = db.relationship('TransaksiTabungan', backref='pembayaran', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Pembayaran {self.no_kuitansi}>'


# ─────────────────────────────────────────────────────────────
# TABUNGAN
# ─────────────────────────────────────────────────────────────
class RekeningTabungan(db.Model):
    """Setiap nasabah punya 1 rekening dengan 3 jenis saldo."""
    __tablename__ = 'rekening_tabungan'
    id          = db.Column(db.Integer, primary_key=True)
    nasabah_id  = db.Column(db.Integer, db.ForeignKey('nasabah.id'), unique=True, nullable=False)
    no_rekening = db.Column(db.String(30), unique=True, nullable=False)
    # Saldo per jenis (dalam Rupiah)
    saldo_pokok    = db.Column(db.BigInteger, default=0)   # tidak bisa tarik jika ada pinjaman aktif
    saldo_wajib    = db.Column(db.BigInteger, default=0)   # tidak bisa tarik jika ada pinjaman aktif
    saldo_sukarela = db.Column(db.BigInteger, default=0)   # bebas ditarik
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    nasabah     = db.relationship('Nasabah', backref=db.backref('rekening', uselist=False))
    transaksi   = db.relationship('TransaksiTabungan', backref='rekening', lazy=True,
                                  order_by='TransaksiTabungan.tanggal')

    def punya_pinjaman_aktif(self):
        return any(p.status == 'cair' for p in self.nasabah.pinjaman)

    def total_saldo(self):
        return self.saldo_pokok + self.saldo_wajib + self.saldo_sukarela

    def saldo_bisa_tarik(self, untuk_angsuran=False):
        """Saldo yang bisa ditarik:
        - Sukarela: selalu bisa
        - Pokok+Wajib: hanya jika tidak ada pinjaman aktif, ATAU untuk tambahan angsuran
        """
        saldo = self.saldo_sukarela
        if tidak_ada_pinjaman := not self.punya_pinjaman_aktif():
            saldo += self.saldo_pokok + self.saldo_wajib
        elif untuk_angsuran:
            saldo += self.saldo_pokok + self.saldo_wajib
        return saldo


class TransaksiTabungan(db.Model):
    __tablename__ = 'transaksi_tabungan'
    id           = db.Column(db.Integer, primary_key=True)
    rekening_id  = db.Column(db.Integer, db.ForeignKey('rekening_tabungan.id', ondelete='CASCADE'), nullable=False)
    tanggal      = db.Column(db.Date, default=date.today)
    jenis        = db.Column(db.String(10), nullable=False)   # 'setor' / 'tarik'
    kategori     = db.Column(db.String(15), nullable=False)   # 'pokok' / 'wajib' / 'sukarela'
    jumlah       = db.Column(db.BigInteger, nullable=False)
    keterangan   = db.Column(db.Text)
    no_bukti     = db.Column(db.String(30))
    # Jika tarik untuk angsuran, simpan referensi pembayaran
    pembayaran_id = db.Column(db.Integer, db.ForeignKey('pembayaran.id', ondelete='CASCADE'), nullable=True)
    created_by   = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class PengajuanPenarikan(db.Model):
    __tablename__ = 'pengajuan_penarikan'
    id           = db.Column(db.Integer, primary_key=True)
    rekening_id  = db.Column(db.Integer, db.ForeignKey('rekening_tabungan.id'), nullable=False)
    tanggal      = db.Column(db.Date, default=date.today)
    jumlah       = db.Column(db.BigInteger, nullable=False)
    keterangan   = db.Column(db.Text)
    status       = db.Column(db.String(20), default='menunggu') # menunggu / disetujui / ditolak
    alasan_tolak = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    rekening = db.relationship('RekeningTabungan', backref=db.backref('pengajuan_penarikan_list', lazy=True, cascade='all, delete-orphan'))


# ─────────────────────────────────────────────────────────────
# JAMINAN
# ─────────────────────────────────────────────────────────────
class JaminanBPKB(db.Model):
    __tablename__ = 'jaminan_bpkb'
    id              = db.Column(db.Integer, primary_key=True)
    nasabah_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False)
    # Kepemilikan
    kepemilikan     = db.Column(db.String(20), nullable=False, default='milik_sendiri')  # milik_sendiri / milik_orang_lain
    surat_kuasa     = db.Column(db.String(256))   # upload jika milik orang lain
    # Data pemilik
    nama_pemilik    = db.Column(db.String(128), nullable=False)
    alamat_pemilik  = db.Column(db.Text)
    # Data kendaraan
    jenis_kendaraan = db.Column(db.String(10))    # Mobil / Motor
    merk            = db.Column(db.String(64))
    tipe            = db.Column(db.String(64))
    nomor_polisi    = db.Column(db.String(20))
    nomor_rangka    = db.Column(db.String(50))
    nomor_mesin     = db.Column(db.String(50))
    tahun_pembuatan = db.Column(db.Integer)
    # Pinjaman terkait (opsional)
    pinjaman_id     = db.Column(db.Integer, db.ForeignKey('pinjaman.id', ondelete='CASCADE'), nullable=True)
    keterangan      = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))
    nasabah         = db.relationship('Nasabah', backref=db.backref('jaminan_bpkb_list', lazy=True))


class JaminanSHM(db.Model):
    __tablename__ = 'jaminan_shm'
    id              = db.Column(db.Integer, primary_key=True)
    nasabah_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False)
    nama_pemilik    = db.Column(db.String(128), nullable=False)
    alamat_pemilik  = db.Column(db.Text)
    lokasi_lahan    = db.Column(db.Text)
    luas_lahan      = db.Column(db.String(50))    # m² atau Ha, simpan sebagai string fleksibel
    nib             = db.Column(db.String(50))    # Nomor Identifikasi Bidang
    tahun_penerbitan= db.Column(db.Integer)
    pinjaman_id     = db.Column(db.Integer, db.ForeignKey('pinjaman.id', ondelete='CASCADE'), nullable=True)
    keterangan      = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))
    nasabah         = db.relationship('Nasabah', backref=db.backref('jaminan_shm_list', lazy=True))


class JaminanLain(db.Model):
    __tablename__ = 'jaminan_lain'
    id              = db.Column(db.Integer, primary_key=True)
    nasabah_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False)
    jenis_jaminan   = db.Column(db.String(100), nullable=False)
    nomor_jaminan   = db.Column(db.String(100))
    nama_pemilik    = db.Column(db.String(128))
    alamat_pemilik  = db.Column(db.Text)
    keterangan      = db.Column(db.Text)
    pinjaman_id     = db.Column(db.Integer, db.ForeignKey('pinjaman.id', ondelete='CASCADE'), nullable=True)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))
    nasabah         = db.relationship('Nasabah', backref=db.backref('jaminan_lain_list', lazy=True))


# ─────────────────────────────────────────────────────────────
# KELOMPOK — Anggota & Detail SPP
# ─────────────────────────────────────────────────────────────
class AnggotaKelompok(db.Model):
    """Anggota dari nasabah bertipe KELOMPOK."""
    __tablename__ = 'anggota_kelompok'
    id          = db.Column(db.Integer, primary_key=True)
    kelompok_id = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False)
    urut        = db.Column(db.Integer, default=1)          # nomor urut dalam kelompok
    nama        = db.Column(db.String(128), nullable=False)
    nik         = db.Column(db.String(20))
    jabatan     = db.Column(db.String(30), default='anggota')  # ketua / sekretaris / bendahara / anggota
    no_hp       = db.Column(db.String(20))
    alamat      = db.Column(db.Text)
    ktp         = db.Column(db.String(256))
    kk          = db.Column(db.String(256))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    kelompok = db.relationship('Nasabah',
                               backref=db.backref('anggota', lazy=True,
                                                  cascade='all, delete-orphan',
                                                  order_by='AnggotaKelompok.urut'))


class DetailSPP(db.Model):
    """Rincian pinjaman per anggota dalam satu SPP kelompok."""
    __tablename__ = 'detail_spp'
    id          = db.Column(db.Integer, primary_key=True)
    pinjaman_id = db.Column(db.Integer, db.ForeignKey('pinjaman.id', ondelete='CASCADE'), nullable=False)
    urut        = db.Column(db.Integer, default=1)
    nama_anggota= db.Column(db.String(128), nullable=False)
    nik_anggota = db.Column(db.String(20))
    jumlah      = db.Column(db.BigInteger, nullable=False)   # porsi pinjaman anggota ini
    keterangan  = db.Column(db.String(256))



# ─────────────────────────────────────────────────────────────
# PEMERIKSAAN DOKUMEN PENGAJUAN
# ─────────────────────────────────────────────────────────────
class PemeriksaanDokumen(db.Model):
    __tablename__ = 'pemeriksaan_dokumen'
    id                      = db.Column(db.Integer, primary_key=True)
    pinjaman_id             = db.Column(db.Integer, db.ForeignKey('pinjaman.id', ondelete='CASCADE'), nullable=False, unique=True)
    pemeriksa_id            = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tanggal_pemeriksaan     = db.Column(db.Date, default=date.today)

    foto_valid              = db.Column(db.Boolean, default=False)
    ktp_valid               = db.Column(db.Boolean, default=False)
    kk_valid                = db.Column(db.Boolean, default=False)
    surat_usaha_valid       = db.Column(db.Boolean, default=False)
    bukti_penghasilan_valid = db.Column(db.Boolean, default=False)
    jaminan_valid           = db.Column(db.Boolean, default=False)
    surat_tanggung_renteng_valid = db.Column(db.Boolean, default=False)
    surat_ijin_keluarga_valid    = db.Column(db.Boolean, default=False)

    catatan_pemeriksa       = db.Column(db.Text)
    nama_verifikator        = db.Column(db.String(128))
    nomor_urut              = db.Column(db.Integer)
    nomor_surat             = db.Column(db.String(50))
    hasil                   = db.Column(db.String(20))
    created_at              = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    pinjaman  = db.relationship('Pinjaman', backref=db.backref('pemeriksaan', uselist=False, cascade='all, delete-orphan'))
    pemeriksa = db.relationship('User', foreign_keys=[pemeriksa_id])

    DOKUMEN_FIELDS = [
        ('foto', 'Pas Foto'),
        ('ktp', 'KTP'),
        ('kk', 'Kartu Keluarga'),
        ('surat_usaha', 'Surat Keterangan Usaha/Kerja'),
        ('bukti_penghasilan', 'Bukti Penghasilan'),
        ('jaminan', 'Jaminan'),
    ]

    DOKUMEN_KELOMPOK_FIELDS = [
        ('surat_tanggung_renteng', 'Surat Pernyataan Tanggung Renteng'),
        ('surat_ijin_keluarga', 'Surat Keterangan Ijin Keluarga Dekat'),
    ]


# ─────────────────────────────────────────────────────────────
# PENGATURAN LEMBAGA
# ─────────────────────────────────────────────────────────────
class Pengaturan(db.Model):
    """Key-value store untuk pengaturan sistem."""
    __tablename__ = 'pengaturan'
    id          = db.Column(db.Integer, primary_key=True)
    kunci       = db.Column(db.String(100), unique=True, nullable=False)
    nilai       = db.Column(db.Text)
    keterangan  = db.Column(db.String(255))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @staticmethod
    def get(kunci, default=''):
        p = db.session.query(Pengaturan).filter_by(kunci=kunci).first()
        return p.nilai if p and p.nilai else default

    @staticmethod
    def set(kunci, nilai, keterangan=''):
        p = db.session.query(Pengaturan).filter_by(kunci=kunci).first()
        if p:
            p.nilai = nilai
            p.updated_at = datetime.now(timezone.utc)
        else:
            p = Pengaturan(kunci=kunci, nilai=nilai, keterangan=keterangan)
            db.session.add(p)

    @staticmethod
    def seed_defaults():
        defaults = {
            'nama_lembaga'      : ('BUM DESA BERSAMA UPK CIOMAS LKD', 'Nama lembaga'),
            'alamat'            : ('Jl. Raya Ciomas Km.1 Serang 42164', 'Alamat'),
            'telp'              : ('(0254)7823984', 'Telepon'),
            'wa'                : ('081324771060', 'WhatsApp'),
            'email'             : ('', 'Email'),
            'direktur'          : ('', 'Nama Direktur'),
            'manajer_lkd'       : ('', 'Manajer LKD'),
            'kabag_kredit'      : ('', 'Kepala Bagian Kredit'),
            'kabag_keuangan'    : ('', 'Kepala Bagian Keuangan'),
            'kabag_tu'          : ('', 'Kepala Bagian Tata Usaha'),
            'kasir'             : ('', 'Kasir'),
            'staf'              : ('', 'Staf'),
            'wa_pengirim'       : ('', 'Nomor WA pengirim tagihan (format: 628xxx)'),
            'wa_api_key'        : ('', 'API Key WhatsApp Gateway (opsional)'),
            'bonus_persen'      : ('{"2022": 20, "2023": 10, "2024": 5, "2025": 2}', 'Persentase bonus petugas per tahun tunggakan (JSON)'),
            'bonus_pembina_persen': ('20', 'Persentase potong bonus untuk pembina'),
            'tutup_buku': ('{}', 'Tahun-tahun yang sudah ditutup (JSON)'),
        }
        for k, (v, ket) in defaults.items():
            if not db.session.query(Pengaturan).filter_by(kunci=k).first():
                db.session.add(Pengaturan(kunci=k, nilai=v, keterangan=ket))
        db.session.commit()


# ─────────────────────────────────────────────────────────────
# AKUNTANSI — COA, Jurnal, Buku Besar, Aset
# ─────────────────────────────────────────────────────────────
class AkunCOA(db.Model):
    """Chart of Accounts — Bagan Akun Standar BUM Desa (Kepmendesa 136/2022)."""
    __tablename__ = 'akun_coa'
    id              = db.Column(db.Integer, primary_key=True)
    kode            = db.Column(db.String(20), unique=True, nullable=False)
    nama            = db.Column(db.String(150), nullable=False)
    # Golongan: 1=Aset, 2=Liabilitas, 3=Ekuitas, 4=Pendapatan, 5=Beban
    golongan        = db.Column(db.Integer, nullable=False)
    golongan_nama   = db.Column(db.String(50))
    # Tipe: debit / kredit (saldo normal)
    saldo_normal    = db.Column(db.String(6), default='debit')  # debit/kredit
    level           = db.Column(db.Integer, default=1)          # 1=heading, 2=sub, 3=detail
    parent_id       = db.Column(db.Integer, db.ForeignKey('akun_coa.id'), nullable=True)
    aktif           = db.Column(db.Boolean, default=True)
    keterangan      = db.Column(db.Text)
    # Flag: apakah akun ini bisa di-input jurnal manual
    bisa_jurnal     = db.Column(db.Boolean, default=True)

    children = db.relationship('AkunCOA', backref=db.backref('parent', remote_side='AkunCOA.id'), lazy=True)
    jurnal_detail = db.relationship('JurnalDetail', backref='akun', lazy=True, cascade='all, delete-orphan')
    saldo_awal = db.relationship('SaldoAwal', backref='akun', lazy=True, cascade='all, delete-orphan')

    def get_saldo(self, tgl_dari=None, tgl_sampai=None, exclude_tipe=None):
        """Hitung saldo akun dari saldo_awal + jurnal."""
        from sqlalchemy import func

        # ── Saldo Awal ─────────────────────────────────────────
        sa_debit = sa_kredit = 0
        if tgl_dari is None:
            q_sa = db.session.query(
                func.sum(SaldoAwal.debit).label('sd'),
                func.sum(SaldoAwal.kredit).label('sk')
            ).filter(SaldoAwal.akun_id == self.id)
            if tgl_sampai:
                q_sa = q_sa.filter(SaldoAwal.tanggal <= tgl_sampai)
            res_sa = q_sa.first()
            sa_debit = res_sa.sd or 0
            sa_kredit = res_sa.sk or 0

        # ── Jurnal ─────────────────────────────────────────────
        q = db.session.query(
            func.sum(JurnalDetail.debit).label('total_debit'),
            func.sum(JurnalDetail.kredit).label('total_kredit')
        ).join(JurnalUmum).filter(
            JurnalDetail.akun_id == self.id,
            JurnalUmum.status == 'posted'
        )
        if tgl_dari:
            q = q.filter(JurnalUmum.tanggal >= tgl_dari)
        if tgl_sampai:
            q = q.filter(JurnalUmum.tanggal <= tgl_sampai)
        if exclude_tipe:
            q = q.filter(~JurnalUmum.tipe.in_(exclude_tipe))
        
        result = q.first()
        total_debit  = (result.total_debit  or 0) + sa_debit
        total_kredit = (result.total_kredit or 0) + sa_kredit

        if self.saldo_normal == 'debit':
            return total_debit - total_kredit
        else:
            return total_kredit - total_debit


class JurnalUmum(db.Model):
    """Header jurnal umum."""
    __tablename__ = 'jurnal_umum'
    id              = db.Column(db.Integer, primary_key=True)
    no_jurnal       = db.Column(db.String(30), unique=True, nullable=False)
    tanggal         = db.Column(db.Date, nullable=False, default=date.today, index=True)
    keterangan      = db.Column(db.Text, nullable=False)
    referensi       = db.Column(db.String(50))   # SPK/KWT/dll untuk auto-jurnal
    tipe            = db.Column(db.String(20), default='manual')  # manual/pencairan/angsuran/tabungan
    status          = db.Column(db.String(10), default='posted')  # draft/posted
    total_debit     = db.Column(db.BigInteger, default=0)
    total_kredit    = db.Column(db.BigInteger, default=0)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))

    detail = db.relationship('JurnalDetail', backref='jurnal', lazy=True,
                             cascade='all, delete-orphan', order_by='JurnalDetail.id')


class JurnalDetail(db.Model):
    """Baris jurnal (debit/kredit per akun)."""
    __tablename__ = 'jurnal_detail'
    id          = db.Column(db.Integer, primary_key=True)
    jurnal_id   = db.Column(db.Integer, db.ForeignKey('jurnal_umum.id', ondelete='CASCADE'), nullable=False)
    akun_id     = db.Column(db.Integer, db.ForeignKey('akun_coa.id', ondelete='CASCADE'), nullable=False)
    keterangan  = db.Column(db.String(255))
    debit       = db.Column(db.BigInteger, default=0)
    kredit      = db.Column(db.BigInteger, default=0)


class Aset(db.Model):
    """Manajemen Aset Tetap."""
    __tablename__ = 'aset'
    id              = db.Column(db.Integer, primary_key=True)
    kode_aset       = db.Column(db.String(30), unique=True)
    nama            = db.Column(db.String(150), nullable=False)
    kategori        = db.Column(db.String(50))   # Tanah/Bangunan/Kendaraan/Inventaris/dll
    tanggal_perolehan = db.Column(db.Date)
    nilai_perolehan = db.Column(db.BigInteger, default=0)
    umur_ekonomis   = db.Column(db.Integer, default=0)  # tahun
    nilai_buku      = db.Column(db.BigInteger, default=0)
    akumulasi_penyusutan = db.Column(db.BigInteger, default=0)
    lokasi          = db.Column(db.String(150))
    kondisi         = db.Column(db.String(20), default='baik')  # baik/rusak_ringan/rusak_berat
    keterangan      = db.Column(db.Text)
    aktif           = db.Column(db.Boolean, default=True)
    akun_id         = db.Column(db.Integer, db.ForeignKey('akun_coa.id', ondelete='CASCADE'), nullable=True)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))

    mutasi_list = db.relationship('AsetMutasi', backref='aset', lazy=True, cascade='all, delete-orphan')


class SaldoAwal(db.Model):
    """Saldo awal per akun (biasanya di awal tahun)."""
    __tablename__ = 'saldo_awal'
    id          = db.Column(db.Integer, primary_key=True)
    akun_id     = db.Column(db.Integer, db.ForeignKey('akun_coa.id', ondelete='CASCADE'), nullable=False)
    tanggal     = db.Column(db.Date, nullable=False, default=date.today)
    debit       = db.Column(db.BigInteger, default=0)
    kredit      = db.Column(db.BigInteger, default=0)
    keterangan  = db.Column(db.String(255), default='Saldo Awal')
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'))


class Pengumuman(db.Model):
    """Pengumuman / Informasi dari BUM Desa Bersama ke nasabah (atau semua)."""
    __tablename__ = 'pengumuman'
    id          = db.Column(db.Integer, primary_key=True)
    judul       = db.Column(db.String(200), nullable=False)
    isi         = db.Column(db.Text, nullable=False)
    tipe        = db.Column(db.String(20), default='info')   # info / penting / pengumuman
    target      = db.Column(db.String(20), default='semua')  # semua / nasabah_spesifik
    nasabah_id_fk = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=True)
    aktif       = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at  = db.Column(db.DateTime, nullable=True)
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'))

    nasabah = db.relationship('Nasabah', backref='pengumuman_list')


class AjuanDokumen(db.Model):
    """Pengajuan perubahan dokumen dari nasabah."""
    __tablename__ = 'ajuan_dokumen'
    id              = db.Column(db.Integer, primary_key=True)
    nasabah_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False, index=True)
    dokumen         = db.Column(db.String(50), nullable=False)  # foto, ktp, kk, surat_usaha, bukti_penghasilan, jaminan
    alasan          = db.Column(db.Text)
    status          = db.Column(db.String(20), default='menunggu', index=True)  # menunggu / disetujui / ditolak
    tanggal_ajuan   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tanggal_respon  = db.Column(db.DateTime)
    admin_id        = db.Column(db.Integer, db.ForeignKey('users.id'))
    catatan_admin   = db.Column(db.Text)
    
    nasabah = db.relationship('Nasabah', backref=db.backref('ajuan_dokumen_list', lazy=True))
    admin = db.relationship('User', foreign_keys=[admin_id])
    
    STATUS_LABELS = {
        'menunggu': 'Menunggu',
        'disetujui': 'Disetujui',
        'ditolak': 'Ditolak'
    }
    
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)


class PengajuanPenjual(db.Model):
    """Pengajuan nasabah untuk menjadi penjual UMKM."""
    __tablename__ = 'pengajuan_penjual'
    id              = db.Column(db.Integer, primary_key=True)
    nasabah_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False, index=True)
    nama_usaha      = db.Column(db.String(128), nullable=False)
    jenis_usaha     = db.Column(db.String(100))
    deskripsi       = db.Column(db.Text)
    no_hp_usaha     = db.Column(db.String(20))
    alamat_usaha    = db.Column(db.Text)
    status          = db.Column(db.String(20), default='menunggu', index=True)  # menunggu / disetujui / ditolak
    tanggal_ajuan   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tanggal_respon  = db.Column(db.DateTime)
    admin_id        = db.Column(db.Integer, db.ForeignKey('users.id'))
    catatan_admin   = db.Column(db.Text)
    
    nasabah = db.relationship('Nasabah', backref=db.backref('pengajuan_penjual_list', lazy=True))
    admin = db.relationship('User', foreign_keys=[admin_id])
    
    STATUS_LABELS = {
        'menunggu': 'Menunggu',
        'disetujui': 'Disetujui',
        'ditolak': 'Ditolak'
    }
    
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)


class ProdukUMKM(db.Model):
    """Produk UMKM yang dijual oleh nasabah penjual."""
    __tablename__ = 'produk_umkm'
    id              = db.Column(db.Integer, primary_key=True)
    penjual_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False, index=True)
    nama_produk     = db.Column(db.String(128), nullable=False)
    deskripsi       = db.Column(db.Text)
    kategori        = db.Column(db.String(50))  # makanan / minuman / kerajinan / pertanian / lainnya
    harga           = db.Column(db.BigInteger, nullable=False)
    stok            = db.Column(db.Integer, default=0)
    satuan          = db.Column(db.String(20), default='pcs')  # pcs / kg / liter / dll
    gambar          = db.Column(db.String(256))
    aktif           = db.Column(db.Boolean, default=True, index=True)
    tanggal_dibuat  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tanggal_diperbarui = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    penjual = db.relationship('Nasabah', backref=db.backref('produk_umkm_list', lazy=True))
    
    KATEGORI_LABELS = {
        'makanan': 'Makanan',
        'minuman': 'Minuman',
        'kerajinan': 'Kerajinan',
        'pertanian': 'Pertanian',
        'peternakan': 'Peternakan',
        'fashion': 'Fashion',
        'lainnya': 'Lainnya'
    }
    
    def kategori_label(self):
        return self.KATEGORI_LABELS.get(self.kategori, self.kategori)


class PesananUMKM(db.Model):
    """Pesanan produk UMKM dari nasabah pembeli."""
    __tablename__ = 'pesanan_umkm'
    id              = db.Column(db.Integer, primary_key=True)
    nomor_pesanan   = db.Column(db.String(30), unique=True, nullable=False, index=True)
    pembeli_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False, index=True)
    penjual_id      = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False, index=True)
    tanggal_pesanan = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tanggal_diproses = db.Column(db.DateTime)
    tanggal_selesai = db.Column(db.DateTime)
    status          = db.Column(db.String(30), default='menunggu', index=True)  # menunggu / diproses / dikirim / selesai / dibatalkan
    catatan_pembeli = db.Column(db.Text)
    catatan_penjual = db.Column(db.Text)
    total_harga     = db.Column(db.BigInteger, nullable=False)
    # Status Pembayaran
    status_pembayaran = db.Column(db.String(20), default='belum_bayar', index=True)  # belum_bayar / lunas / dibatalkan
    tanggal_lunas    = db.Column(db.DateTime)
    metode_pembayaran = db.Column(db.String(50))  # transfer / tunai / saldo_tabungan
    bukti_pembayaran = db.Column(db.String(256))
    # Info Pengiriman
    kurir            = db.Column(db.String(50))
    nomor_resi       = db.Column(db.String(100))
    tanggal_kirim    = db.Column(db.DateTime)
    alamat_pengiriman = db.Column(db.Text)
    # Catatan Admin
    catatan_admin    = db.Column(db.Text)
    updated_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    pembeli = db.relationship('Nasabah', foreign_keys=[pembeli_id], backref=db.backref('pesanan_pembeli_list', lazy=True))
    penjual = db.relationship('Nasabah', foreign_keys=[penjual_id], backref=db.backref('pesanan_penjual_list', lazy=True))
    
    STATUS_LABELS = {
        'menunggu': 'Menunggu',
        'diproses': 'Diproses',
        'dikirim': 'Dikirim',
        'selesai': 'Selesai',
        'dibatalkan': 'Dibatalkan'
    }
    
    PEMBAYARAN_LABELS = {
        'belum_bayar': 'Belum Bayar',
        'menunggu_konfirmasi': 'Menunggu Konfirmasi',
        'lunas': 'Lunas',
        'gagal': 'Gagal',
        'dibatalkan': 'Dibatalkan'
    }
    
    METODE_PEMBAYARAN_LABELS = {
        'transfer_bank': 'Transfer Bank',
        'bca': 'BCA',
        'bri': 'BRI',
        'bni': 'BNI',
        'mandiri': 'Mandiri',
        'bsi': 'BSI',
        'dana': 'DANA',
        'ovo': 'OVO',
        'gopay': 'GoPay',
        'shopee_pay': 'ShopeePay',
        'link_aja': 'LinkAja',
        'cod': 'COD (Bayar di Tempat)',
    }
    
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)
    
    def status_pembayaran_label(self):
        return self.PEMBAYARAN_LABELS.get(self.status_pembayaran, self.status_pembayaran)
    
    def metode_pembayaran_label(self):
        return self.METODE_PEMBAYARAN_LABELS.get(self.metode_pembayaran, self.metode_pembayaran)


class DetailPesananUMKM(db.Model):
    """Detail item dalam pesanan UMKM."""
    __tablename__ = 'detail_pesanan_umkm'
    id              = db.Column(db.Integer, primary_key=True)
    pesanan_id      = db.Column(db.Integer, db.ForeignKey('pesanan_umkm.id', ondelete='CASCADE'), nullable=False)
    produk_id       = db.Column(db.Integer, db.ForeignKey('produk_umkm.id'), nullable=False)
    jumlah          = db.Column(db.Integer, nullable=False)
    harga_satuan    = db.Column(db.BigInteger, nullable=False)
    subtotal        = db.Column(db.BigInteger, nullable=False)
    
    pesanan = db.relationship('PesananUMKM', backref=db.backref('detail_list', lazy=True, cascade='all, delete-orphan'))
    produk = db.relationship('ProdukUMKM', backref=db.backref('detail_pesanan_list', lazy=True))


class RekeningPembayaran(db.Model):
    """Rekening bank/e-wallet untuk pembayaran pesanan."""
    __tablename__ = 'rekening_pembayaran'
    id              = db.Column(db.Integer, primary_key=True)
    nama_bank       = db.Column(db.String(50), nullable=False)  # BRI, BCA, BNI, DANA, OVO, dll
    nama_rekening   = db.Column(db.String(100), nullable=False)
    nomor_rekening  = db.Column(db.String(50), nullable=False)
    aktif           = db.Column(db.Boolean, default=True)
    urutan          = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))


class AsetMutasi(db.Model):
    """Mutasi perpindahan aset antar lokasi."""
    __tablename__ = 'aset_mutasi'
    id          = db.Column(db.Integer, primary_key=True)
    aset_id     = db.Column(db.Integer, db.ForeignKey('aset.id'), nullable=False)
    dari_lokasi = db.Column(db.String(128))
    ke_lokasi   = db.Column(db.String(128))
    tanggal     = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    keterangan  = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'))


class OpnameAset(db.Model):
    """Hasil opname aset (per-item per-tanggal)."""
    __tablename__ = 'opname_aset'
    id               = db.Column(db.Integer, primary_key=True)
    aset_id          = db.Column(db.Integer, db.ForeignKey('aset.id'), nullable=False, index=True)
    tanggal_opname   = db.Column(db.Date, nullable=False, index=True)
    kondisi_catatan  = db.Column(db.String(20))
    kondisi_fisik    = db.Column(db.String(20))
    status           = db.Column(db.String(30), default='sesuai')  # sesuai, kondisi_berubah, hilang
    catatan          = db.Column(db.Text)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by       = db.Column(db.Integer, db.ForeignKey('users.id'))

    aset = db.relationship('Aset', backref=db.backref('opname_records', lazy=True))

class BonusPetugas(db.Model):
    __tablename__ = 'bonus_petugas'
    id              = db.Column(db.Integer, primary_key=True)
    pembayaran_id   = db.Column(db.Integer, db.ForeignKey('pembayaran.id', ondelete='CASCADE'), nullable=False)
    petugas_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tahun_tunggakan= db.Column(db.Integer, nullable=False)  # tahun jatuh tempo
    jumlah_bayar  = db.Column(db.BigInteger, nullable=False)
    persen_bonus   = db.Column(db.Float, nullable=False)
    jumlah_bonus  = db.Column(db.BigInteger, nullable=False)
    status         = db.Column(db.String(20), default='belum_diklaim')  # belum_diklaim / menunggu_klaim / diklaim / dibatalkan
    tanggal_hitung= db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tanggal_klaim  = db.Column(db.DateTime, nullable=True)
    diklaim_oleh   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    pembayaran = db.relationship('Pembayaran', backref=db.backref('bonus_list', lazy=True))
    petugas    = db.relationship('User', foreign_keys=[petugas_id], backref=db.backref('bonus_list', lazy=True))
    diklaim_oleh_user = db.relationship('User', foreign_keys=[diklaim_oleh])

    DEFAULT_BONUS = {2022: 20.0, 2023: 10.0, 2024: 5.0, 2025: 2.0}

    @staticmethod
    def get_persen_bonus(tahun_tunggakan):
        """Cari persentase bonus berdasarkan tahun tunggakan.
        
        Logika: cari entri tahun terkecil yang >= tahun_tunggakan.
        Contoh map: {2022:20, 2023:10, 2024:5, 2025:2}
        - tunggakan tahun 2022 → 20% (cocok dengan 2022)
        - tunggakan tahun 2023 → 10%
        - tunggakan tahun 2021 → 20% (fallback ke terkecil)
        - tunggakan tahun 2026 → 2%  (fallback ke terbesar)
        """
        import json
        p = db.session.query(Pengaturan).filter_by(kunci='bonus_persen').first()
        json_str = p.nilai if p and p.nilai else ''
        
        try:
            if json_str:
                percentage_map = json.loads(json_str)
            else:
                percentage_map = {str(k): v for k, v in BonusPetugas.DEFAULT_BONUS.items()}
            
            if not percentage_map:
                return 2.0
            
            # Urutkan ascending (terkecil ke terbesar)
            sorted_items = sorted(percentage_map.items(), key=lambda x: int(x[0]))
            
            # Cari entri pertama (terkecil) yang >= tahun_tunggakan
            for tahun_key, persen in sorted_items:
                if int(tahun_key) >= tahun_tunggakan:
                    return float(persen)
            
            # Jika tidak ada yang cocok (tahun_tunggakan > semua entri),
            # gunakan persentase dari tahun terbesar (nilai paling kecil/terakhir)
            return float(sorted_items[-1][1])
        except Exception:
            return 2.0

    @staticmethod
    def hitung_bonus(pembayaran, petugas_id):
        pin = pembayaran.pinjaman
        if not pin or not pin.tanggal_mulai_angsuran:
            return None
        if pin.status != 'cair':
            return None
        
        angsuran_ke = pembayaran.angsuran_ke or 1
        jadwal = pin.get_jadwal_angsuran()
        if angsuran_ke <= len(jadwal):
            tahun_jatuh_tempo = jadwal[angsuran_ke - 1]['tanggal'].year
        else:
            tahun_jatuh_tempo = pin.tanggal_mulai_angsuran.year
        
        persen = BonusPetugas.get_persen_bonus(tahun_jatuh_tempo)
        jumlah = pembayaran.jumlah_bayar
        bonus = int(jumlah * persen / 100)
        
        if bonus < 100:
            return None
        
        bp = BonusPetugas(
            pembayaran_id=pembayaran.id,
            petugas_id=petugas_id,
            tahun_tunggakan=tahun_jatuh_tempo,
            jumlah_bayar=jumlah,
            persen_bonus=persen,
            jumlah_bonus=bonus,
        )
        return bp

    @staticmethod
    def buat_bonus_pembina(pembayaran_id, kader_id, jumlah_bonus_kader):
        """Buat record bonus untuk pembina berdasarkan pengaturan."""
        kader = User.query.get(kader_id)
        if not kader or not kader.pembina_id:
            return None
        
        p = db.session.query(Pengaturan).filter_by(kunci='bonus_pembina_persen').first()
        persen_pembina = float(p.nilai) if p and p.nilai else 20.0
        
        jumlah_pembina = int(jumlah_bonus_kader * persen_pembina / 100)
        if jumlah_pembina < 100:
            return None
        
        bp = BonusPembina(
            pembayaran_id=pembayaran_id,
            kader_id=kader_id,
            pembina_id=kader.pembina_id,
            jumlah_bonus_kader=jumlah_bonus_kader,
            persen_potongan=persen_pembina,
            jumlah_bonus_pembina=jumlah_pembina,
            status='belum_diklaim'
        )
        return bp


class BonusPembina(db.Model):
    __tablename__ = 'bonus_pembina'
    id                   = db.Column(db.Integer, primary_key=True)
    pembayaran_id        = db.Column(db.Integer, db.ForeignKey('pembayaran.id', ondelete='CASCADE'), nullable=False)
    kader_id            = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pembina_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    jumlah_bonus_kader  = db.Column(db.BigInteger, nullable=False)
    persen_potongan     = db.Column(db.Float, nullable=False, default=20)
    jumlah_bonus_pembina= db.Column(db.BigInteger, nullable=False)
    status              = db.Column(db.String(20), default='belum_diklaim')  # belum_diklaim / menunggu_klaim / diklaim
    tanggal_hitung      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tanggal_klaim       = db.Column(db.DateTime, nullable=True)

    pembayaran = db.relationship('Pembayaran', backref=db.backref('bonus_pembina_list', lazy=True))
    kader      = db.relationship('User', foreign_keys=[kader_id], backref=db.backref('bonus_untuk_pembina', lazy=True))
    pembina    = db.relationship('User', foreign_keys=[pembina_id], backref=db.backref('bonus_dari_kader', lazy=True))


# ─────────────────────────────────────────────────────────────
# FCM / PUSH NOTIFICATION
# ─────────────────────────────────────────────────────────────
class FCMToken(db.Model):
    """Firebase Cloud Messaging token untuk push notification ke Android."""
    __tablename__ = 'fcm_tokens'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token       = db.Column(db.String(512), unique=True, nullable=False)
    platform    = db.Column(db.String(20), default='android')
    aktif       = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('fcm_tokens', lazy=True))


def get_next_no_pesanan_umkm():
    from datetime import date
    today = date.today()
    prefix = f"INV-{today.strftime('%Y%m')}-"
    last = PesananUMKM.query.filter(PesananUMKM.nomor_pesanan.like(f'{prefix}%'))\
        .order_by(PesananUMKM.nomor_pesanan.desc()).first()
    if last:
        try:
            seq = int(last.nomor_pesanan.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"

# === END OF MODELS ===
