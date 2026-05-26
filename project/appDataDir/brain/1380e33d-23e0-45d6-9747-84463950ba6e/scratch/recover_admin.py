from app import create_app
from app.models import db, User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', nama_lengkap='Administrator', role='admin')
        db.session.add(admin)
        print("Menciptakan user admin baru.")
    
    admin.set_password('admin123')
    admin.aktif = True
    db.session.commit()
    print("Akun admin berhasil dipulihkan dengan password: admin123")
