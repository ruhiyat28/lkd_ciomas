import os
import sys

# Menambahkan direktori saat ini ke sys.path agar bisa mengimpor app
sys.path.append(os.getcwd())

from app import create_app
from app.models import db, User
from config import Config

def seed_kader():
    app = create_app()
    with app.app_context():
        print("Starting seed for Kader Desa users...")
        
        for kode, nama in Config.DESA_LIST:
            username = f"kader_{kode.lower()}"
            existing = User.query.filter_by(username=username).first()
            
            if not existing:
                user = User(
                    username=username,
                    nama_lengkap=f"KADER DESA {nama}",
                    role='kader_desa',
                    kode_desa=kode,
                    aktif=True
                )
                user.set_password("kader123")  # Password default
                db.session.add(user)
                print(f"Created user: {username} for {nama}")
            else:
                print(f"User {username} already exists.")
        
        try:
            db.session.commit()
            print("Successfully seeded Kader Desa users.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding users: {e}")

if __name__ == "__main__":
    seed_kader()
