"""
Safe database migration — idempotent, runs on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run_migrations(engine):
    with engine.connect() as conn:
        _add_col(conn, 'pembayaran', 'status_acc', "VARCHAR(20) DEFAULT NULL")
        _add_col(conn, 'pembayaran', 'acc_by',    "INTEGER")
        _add_col(conn, 'pembayaran', 'acc_at',    "TIMESTAMP")
        _add_cascade_fk(conn, 'transaksi_tabungan', 'pembayaran_id', 'pembayaran', 'id')
        _add_col(conn, 'nasabah',  'jenis',             "VARCHAR(15) NOT NULL DEFAULT 'perorangan'")
        _add_col(conn, 'nasabah',  'status',            "VARCHAR(20) DEFAULT 'aktif'")
        _add_col(conn, 'nasabah',  'keterangan_status',  "TEXT")
        _add_col(conn, 'pinjaman', 'jenis_pinjaman',     "VARCHAR(10) NOT NULL DEFAULT 'reguler'")
        _add_col(conn, 'pinjaman', 'foto_kunjungan',     "VARCHAR(100)")
        _add_col(conn, 'pinjaman', 'verified_by',        "INTEGER")
        _add_col(conn, 'pinjaman', 'verified_at',        "TIMESTAMP")
        _add_col(conn, 'pinjaman', 'acc_by',             "INTEGER")
        _add_col(conn, 'pinjaman', 'catatan_direktur',   "TEXT")
        _add_col(conn, 'pinjaman', 'tanggal_spk',        "DATE")
        # _add_col(conn, 'akun_coa', 'level4_only',        "BOOLEAN DEFAULT FALSE")
        _add_col(conn, 'anggota_kelompok', 'ktp',      "VARCHAR(256)")
        _add_col(conn, 'anggota_kelompok', 'kk',       "VARCHAR(256)")
        _add_col(conn, 'pinjaman', 'surat_tanggung_renteng', "VARCHAR(256)")
        _add_col(conn, 'pinjaman', 'surat_ijin_keluarga',    "VARCHAR(256)")
        _add_col(conn, 'pemeriksaan_dokumen', 'surat_tanggung_renteng_valid', "BOOLEAN DEFAULT FALSE")
        _add_col(conn, 'pemeriksaan_dokumen', 'surat_ijin_keluarga_valid',    "BOOLEAN DEFAULT FALSE")
        _add_col(conn, 'pemeriksaan_dokumen', 'nama_verifikator',  "VARCHAR(128)")
        _add_col(conn, 'pemeriksaan_dokumen', 'nomor_urut',        "INTEGER")
        _add_col(conn, 'pemeriksaan_dokumen', 'nomor_surat',       "VARCHAR(50)")
        _add_col(conn, 'users',    'nasabah_id_fk',     "INTEGER")
        _add_col(conn, 'users',    'created_at',        "TIMESTAMP")
        _add_col(conn, 'users',    'kode_desa',         "VARCHAR(5)")
        _add_col(conn, 'users',    'tanda_tangan',      "VARCHAR(255)")
        _add_col(conn, 'nasabah',  'tanda_tangan',      "VARCHAR(255)")
        _add_col(conn, 'nasabah',  'surat_tanggung_renteng_nasabah', "VARCHAR(256)")
        _add_col(conn, 'nasabah',  'surat_ijin_keluarga_nasabah',    "VARCHAR(256)")
        _add_col(conn, 'rekening_pembayaran', 'created_by', "INTEGER")
        _add_col(conn, 'pengumuman', 'nasabah_id_fk', "INTEGER")
        _add_col(conn, 'pengumuman', 'expires_at',    "TIMESTAMP")

        # Tabel baru
        _create_table(conn, 'pengaturan', """CREATE TABLE pengaturan (
            id SERIAL PRIMARY KEY,
            kunci VARCHAR(100) UNIQUE NOT NULL,
            nilai TEXT,
            keterangan VARCHAR(255),
            updated_at TIMESTAMP
        )""")
        _create_table(conn, 'saldo_awal', """CREATE TABLE saldo_awal (
            id SERIAL PRIMARY KEY,
            akun_id INTEGER NOT NULL,
            tanggal DATE NOT NULL,
            debit BIGINT DEFAULT 0,
            kredit BIGINT DEFAULT 0,
            keterangan TEXT,
            created_at TIMESTAMP,
            created_by INTEGER
        )""")
        _create_table(conn, 'pengumuman', """CREATE TABLE pengumuman (
            id SERIAL PRIMARY KEY,
            judul VARCHAR(200) NOT NULL,
            isi TEXT NOT NULL,
            tipe VARCHAR(20) DEFAULT 'info',
            target VARCHAR(20) DEFAULT 'semua',
            aktif BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP,
            created_by INTEGER
        )""")
        _create_table(conn, 'ajuan_dokumen', """CREATE TABLE ajuan_dokumen (
            id SERIAL PRIMARY KEY,
            nasabah_id INTEGER NOT NULL,
            dokumen VARCHAR(50) NOT NULL,
            alasan TEXT,
            status VARCHAR(20) DEFAULT 'menunggu',
            tanggal_ajuan TIMESTAMP,
            tanggal_respon TIMESTAMP,
            admin_id INTEGER,
            catatan_admin TEXT
        )""")
        _create_index(conn, 'idx_ajuan_dokumen_nasabah', 'ajuan_dokumen', 'nasabah_id')
        _create_index(conn, 'idx_ajuan_dokumen_status', 'ajuan_dokumen', 'status')
        
        _create_table(conn, 'pengajuan_penjual', """CREATE TABLE pengajuan_penjual (
            id SERIAL PRIMARY KEY,
            nasabah_id INTEGER NOT NULL,
            nama_usaha VARCHAR(128) NOT NULL,
            jenis_usaha VARCHAR(100),
            deskripsi TEXT,
            no_hp_usaha VARCHAR(20),
            alamat_usaha TEXT,
            status VARCHAR(20) DEFAULT 'menunggu',
            tanggal_ajuan TIMESTAMP,
            tanggal_respon TIMESTAMP,
            admin_id INTEGER,
            catatan_admin TEXT
        )""")
        _create_index(conn, 'idx_pengajuan_penjual_nasabah', 'pengajuan_penjual', 'nasabah_id')
        _create_index(conn, 'idx_pengajuan_penjual_status', 'pengajuan_penjual', 'status')
        
        _create_table(conn, 'produk_umkm', """CREATE TABLE produk_umkm (
            id SERIAL PRIMARY KEY,
            penjual_id INTEGER NOT NULL,
            nama_produk VARCHAR(128) NOT NULL,
            deskripsi TEXT,
            kategori VARCHAR(50),
            harga BIGINT NOT NULL,
            stok INTEGER DEFAULT 0,
            satuan VARCHAR(20) DEFAULT 'pcs',
            gambar VARCHAR(256),
            aktif BOOLEAN DEFAULT TRUE,
            tanggal_dibuat TIMESTAMP,
            tanggal_diperbarui TIMESTAMP
        )""")
        _create_index(conn, 'idx_produk_umkm_penjual', 'produk_umkm', 'penjual_id')
        _create_index(conn, 'idx_produk_umkm_aktif', 'produk_umkm', 'aktif')
        _create_index(conn, 'idx_produk_umkm_kategori', 'produk_umkm', 'kategori')
        
        _create_table(conn, 'pesanan_umkm', """CREATE TABLE pesanan_umkm (
            id SERIAL PRIMARY KEY,
            nomor_pesanan VARCHAR(30) UNIQUE NOT NULL,
            pembeli_id INTEGER NOT NULL,
            penjual_id INTEGER NOT NULL,
            tanggal_pesanan TIMESTAMP,
            tanggal_diproses TIMESTAMP,
            tanggal_selesai TIMESTAMP,
            status VARCHAR(30) DEFAULT 'menunggu',
            catatan_pembeli TEXT,
            catatan_penjual TEXT,
            total_harga BIGINT NOT NULL
        )""")
        _create_index(conn, 'idx_pesanan_umkm_pembeli', 'pesanan_umkm', 'pembeli_id')
        _create_index(conn, 'idx_pesanan_umkm_penjual', 'pesanan_umkm', 'penjual_id')
        _create_index(conn, 'idx_pesanan_umkm_status', 'pesanan_umkm', 'status')
        _create_index(conn, 'idx_pesanan_umkm_nomor', 'pesanan_umkm', 'nomor_pesanan')
        
        _create_table(conn, 'detail_pesanan_umkm', """CREATE TABLE detail_pesanan_umkm (
            id SERIAL PRIMARY KEY,
            pesanan_id INTEGER NOT NULL,
            produk_id INTEGER NOT NULL,
            jumlah INTEGER NOT NULL,
            harga_satuan BIGINT NOT NULL,
            subtotal BIGINT NOT NULL
        )""")
        _create_index(conn, 'idx_detail_pesanan_umkm_pesanan', 'detail_pesanan_umkm', 'pesanan_id')
        _create_index(conn, 'idx_detail_pesanan_umkm_produk', 'detail_pesanan_umkm', 'produk_id')

        # Tabel pemeriksaan dokumen
        _create_table(conn, 'pemeriksaan_dokumen', """CREATE TABLE pemeriksaan_dokumen (
            id SERIAL PRIMARY KEY,
            pinjaman_id INTEGER NOT NULL UNIQUE,
            pemeriksa_id INTEGER NOT NULL,
            tanggal_pemeriksaan DATE,
            foto_valid BOOLEAN DEFAULT FALSE,
            ktp_valid BOOLEAN DEFAULT FALSE,
            kk_valid BOOLEAN DEFAULT FALSE,
            surat_usaha_valid BOOLEAN DEFAULT FALSE,
            bukti_penghasilan_valid BOOLEAN DEFAULT FALSE,
            jaminan_valid BOOLEAN DEFAULT FALSE,
            catatan_pemeriksa TEXT,
            hasil VARCHAR(20),
            created_at TIMESTAMP
        )""")
        _create_index(conn, 'idx_pemeriksaan_dokumen_pinjaman', 'pemeriksaan_dokumen', 'pinjaman_id')

        # Performance indexes
        _create_index(conn, 'idx_users_username',       'users',    'username')
        _create_index(conn, 'idx_users_role',            'users',    'role')
        _create_index(conn, 'idx_users_aktif',           'users',    'aktif')
        _create_index(conn, 'idx_users_kode_desa',       'users',    'kode_desa')
        _create_index(conn, 'idx_nasabah_nasabah_id',    'nasabah',  'nasabah_id')
        _create_index(conn, 'idx_nasabah_kode_desa',     'nasabah',  'kode_desa')
        _create_index(conn, 'idx_nasabah_jenis',         'nasabah',  'jenis')
        _create_index(conn, 'idx_nasabah_status',        'nasabah',  'status')
        _create_index(conn, 'idx_pinjaman_status',       'pinjaman', 'status')
        _create_index(conn, 'idx_pembayaran_tanggal',    'pembayaran', 'tanggal_bayar')
        _create_index(conn, 'idx_jurnal_tanggal',        'jurnal_umum', 'tanggal')

        conn.commit()


def _add_cascade_fk(conn, table, fk_column, ref_table, ref_column):
    """Set FK to ON DELETE CASCADE if not already set — idempotent."""
    try:
        is_postgres = conn.engine.dialect.name == 'postgresql'
        if not is_postgres:
            return

        row = conn.execute(text(f"""
            SELECT co.conname FROM pg_constraint co
            JOIN information_schema.key_column_usage AS kcu
              ON kcu.constraint_name = co.conname
              AND kcu.table_schema = 'public'
            WHERE co.conrelid = '{table}'::regclass
            AND co.contype = 'f'
            AND kcu.column_name = :col
        """), {"col": fk_column}).fetchone()

        if not row:
            return

        constraint_name = row[0]
        conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {constraint_name}"))
        logger.info('Dropped FK %s on %s', constraint_name, table)

        conn.execute(text(
            f"ALTER TABLE {table} ADD CONSTRAINT {table}_{fk_column}_fkey "
            f"FOREIGN KEY ({fk_column}) REFERENCES {ref_table}({ref_column}) ON DELETE CASCADE"
        ))
        logger.info('Added CASCADE FK %s.%s → %s.%s', table, fk_column, ref_table, ref_column)
    except Exception as e:
        logger.warning('_add_cascade_fk %s.%s: %s', table, fk_column, e)


def _add_col(conn, table, column, col_def):
    try:
        is_postgres = conn.engine.dialect.name == 'postgresql'
        
        if is_postgres:
            query = text("SELECT column_name FROM information_schema.columns WHERE table_name=:t AND column_name=:c")
            res = conn.execute(query, {"t": table, "c": column}).fetchone()
            exists = res is not None
        else:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            exists = column in [r[1] for r in rows]

        if not exists:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
            logger.info('Added %s.%s', table, column)
    except Exception as e:
        logger.warning('%s.%s: %s', table, column, e)


def _create_table(conn, table, ddl):
    try:
        is_postgres = conn.engine.dialect.name == 'postgresql'
        if is_postgres:
            query = text("SELECT table_name FROM information_schema.tables WHERE table_name=:t")
            res = conn.execute(query, {"t": table}).fetchone()
            exists = res is not None
        else:
            # SQLite
            query = text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            res = conn.execute(query).fetchone()
            exists = res is not None
            
        if not exists:
            conn.execute(text(ddl))
            logger.info('Created table %s', table)
    except Exception as e:
        logger.warning('Table %s: %s', table, e)


def _create_index(conn, idx_name, table, column):
    """Create index if it doesn't exist. Safe for both PostgreSQL and SQLite."""
    try:
        is_postgres = conn.engine.dialect.name == 'postgresql'
        if is_postgres:
            query = text("SELECT indexname FROM pg_indexes WHERE indexname=:idx")
            res = conn.execute(query, {"idx": idx_name}).fetchone()
            exists = res is not None
        else:
            query = text(f"SELECT name FROM sqlite_master WHERE type='index' AND name=:idx")
            res = conn.execute(query, {"idx": idx_name}).fetchone()
            exists = res is not None

        if not exists:
            conn.execute(text(f'CREATE INDEX {idx_name} ON {table} ({column})'))
            logger.info('Created index %s on %s.%s', idx_name, table, column)
    except Exception as e:
        logger.warning('Index %s: %s', idx_name, e)
