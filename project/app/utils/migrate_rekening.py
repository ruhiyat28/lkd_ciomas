"""
Jalankan sekali untuk membuat rekening tabungan bagi nasabah lama yang belum punya.
Usage: python3 migrate_rekening.py (dari folder /opt/lkd_ciomas)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.models import db, Nasabah, RekeningTabungan

app = create_app()
with app.app_context():
    nasabah_list = Nasabah.query.all()
    buat = 0
    for n in nasabah_list:
        if not RekeningTabungan.query.filter_by(nasabah_id=n.id).first():
            rek = RekeningTabungan(
                nasabah_id  = n.id,
                no_rekening = f"TAB-{n.nasabah_id}",
            )
            db.session.add(rek)
            buat += 1
    db.session.commit()
    print(f"Rekening dibuat: {buat} dari {len(nasabah_list)} nasabah")
