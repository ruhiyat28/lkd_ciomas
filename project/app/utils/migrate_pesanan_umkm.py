"""
Script migrasi untuk menambahkan field baru ke tabel pesanan_umkm

Run dengan: python3 -m app.utils.migrate_pesanan_umkm
"""

def run_migration():
    import os
    import sys
    from pathlib import Path
    
    # Add project root to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    os.environ.setdefault('FLASK_APP', 'run.py')
    
    from app import create_app
    from app.models import db
    
    app = create_app()
    
    with app.app_context():
        # Add columns if they don't exist (for SQLite)
        conn = db.engine.connect()
        
        # Check if columns exist
        result = conn.execute(db.text("PRAGMA table_info(pesanan_umkm)"))
        existing_cols = [row[1] for row in result]
        
        new_columns = [
            ('status_pembayaran', "VARCHAR(20) DEFAULT 'belum_bayar'"),
            ('tanggal_lunas', 'DATETIME'),
            ('metode_pembayaran', 'VARCHAR(50)'),
            ('bukti_pembayaran', 'VARCHAR(256)'),
            ('kurir', 'VARCHAR(50)'),
            ('nomor_resi', 'VARCHAR(100)'),
            ('tanggal_kirim', 'DATETIME'),
            ('alamat_pengiriman', 'TEXT'),
            ('catatan_admin', 'TEXT'),
            ('updated_at', 'DATETIME'),
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                try:
                    conn.execute(db.text(f"ALTER TABLE pesanan_umkm ADD COLUMN {col_name} {col_type}"))
                    print(f"✓ Added column: {col_name}")
                except Exception as e:
                    print(f"✗ Error adding {col_name}: {e}")
            else:
                print(f"- Column already exists: {col_name}")
        
        conn.close()
        print("\nMigration completed!")

if __name__ == '__main__':
    run_migration()