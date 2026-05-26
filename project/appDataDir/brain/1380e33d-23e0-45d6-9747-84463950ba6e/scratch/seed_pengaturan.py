from app import create_app
from app.models import db, Pengaturan

app = create_app()
with app.app_context():
    Pengaturan.seed_defaults()
    db.session.commit()
    print("Pengaturan default berhasil dipulihkan.")
