from flask import Flask, render_template
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from .models import db, User
from config import Config
from .utils.terbilang import terbilang
from .utils.db_migrate import run_migrations
import os
from datetime import date, timedelta

login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view  = 'auth.login'
    login_manager.login_message = 'Silakan login terlebih dahulu.'
    login_manager.login_message_category = 'warning'

    from .routes.api import jwt
    jwt.init_app(app)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'success': False, 'message': 'Token telah kedaluwarsa'}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'success': False, 'message': 'Token tidak valid'}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'success': False, 'message': 'Token diperlukan'}, 401

    for folder in ['foto','ktp','kk','sku','penghasilan','jaminan','jaminan_docs','umkm','logo','anggota_ktp','anggota_kk','surat_tanggung_renteng','surat_ijin_keluarga']:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], folder), exist_ok=True)

    app.jinja_env.globals['terbilang'] = terbilang
    app.jinja_env.globals['now']       = date.today()
    app.jinja_env.globals['today_str'] = date.today().strftime('%Y-%m-%d')
    app.jinja_env.globals['desa_list'] = config_class.DESA_LIST

    # Custom Jinja2 tests
    app.jinja_env.tests['startswith'] = lambda value, prefix: str(value).startswith(str(prefix))
    
    # Custom Jinja2 filters
    app.jinja_env.filters['number_format'] = lambda x: f"{x:,}".replace(',', '.') if x else '0'

    # Global error handler — standalone template, doesn't need the session
    @app.errorhandler(500)
    def handle_500(e):
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template('errors/500.html'), 500

    # Signature QR code generator for templates
    @app.context_processor
    def inject_qr_generator():
        from .models import User
        from .utils.helpers import generate_signature_qr as _gen_qr
        def get_role_signature_qr(role_key):
            """Lookup user by role_key in Pengaturan and return QR of their signature."""
            from .models import Pengaturan
            name = Pengaturan.get(role_key)
            if name:
                user = User.query.filter_by(nama_lengkap=name).first()
                if user and user.tanda_tangan:
                    return _gen_qr(user.tanda_tangan)
            return None
        def signature_qr(sig_filename):
            if sig_filename:
                return _gen_qr(sig_filename)
            return None
        return dict(signature_qr=signature_qr, get_role_signature_qr=get_role_signature_qr)

    @app.context_processor
    def inject_global_data():
        from .models import Pengaturan, Nasabah, Pinjaman
        from flask import session
        try:
            data_pengaturan = {p.kunci: p.nilai for p in Pengaturan.query.all()}
            
            notif_cleared_at = None
            if 'notif_cleared_at' in session:
                try:
                    from datetime import datetime
                    notif_cleared_at = datetime.fromisoformat(session['notif_cleared_at'])
                except Exception:
                    notif_cleared_at = None
            
            def get_calon_nasabah_count():
                query = Nasabah.query.filter_by(status='calon')
                if notif_cleared_at:
                    query = query.filter(Nasabah.created_at > notif_cleared_at)
                return query.count()
            
            def get_pending_pengajuan_count():
                query = Pinjaman.query.filter(
                    Pinjaman.status == 'pengajuan'
                )
                if notif_cleared_at:
                    query = query.filter(Pinjaman.created_at > notif_cleared_at)
                return query.count()

            def get_kader_payment_count():
                from .models import User, Pembayaran
                from datetime import date
                try:
                    return Pembayaran.query.join(User, Pembayaran.created_by == User.id).filter(
                        User.role == 'kader_desa',
                        Pembayaran.tanggal_bayar == date.today()
                    ).count()
                except Exception: return 0

            def get_pengajuan_tarik_count():
                from .models import PengajuanPenarikan
                try:
                    query = PengajuanPenarikan.query.filter_by(status='menunggu')
                    if notif_cleared_at:
                        query = query.filter(PengajuanPenarikan.created_at > notif_cleared_at)
                    return query.count()
                except Exception: return 0
                
            def get_pending_dokumen_count():
                from .models import AjuanDokumen
                try:
                    query = AjuanDokumen.query.filter_by(status='menunggu')
                    if notif_cleared_at:
                        query = query.filter(AjuanDokumen.tanggal_ajuan > notif_cleared_at)
                    return query.count()
                except Exception: return 0
                
            def get_umkm_penjual_count():
                from .models import PengajuanPenjual
                try:
                    query = PengajuanPenjual.query.filter_by(status='menunggu')
                    if notif_cleared_at:
                        query = query.filter(PengajuanPenjual.tanggal_ajuan > notif_cleared_at)
                    return query.count()
                except Exception: return 0
                
            def get_umkm_pesanan_count():
                from .models import PesananUMKM
                try:
                    query = PesananUMKM.query.filter_by(status='menunggu')
                    if notif_cleared_at:
                        query = query.filter(PesananUMKM.tanggal_pesanan > notif_cleared_at)
                    return query.count()
                except Exception: return 0
                
            def get_pending_bonus_count():
                from .models import BonusPetugas
                try:
                    return BonusPetugas.query.filter_by(status='menunggu_klaim').count()
                except Exception: return 0

            def get_pending_acc_pembayaran_count():
                from .models import Pembayaran
                try:
                    return Pembayaran.query.filter_by(status_acc='menunggu').count()
                except Exception: return 0

            return dict(
                pengaturan=data_pengaturan,
                get_calon_nasabah_count=get_calon_nasabah_count,
                get_pending_pengajuan_count=get_pending_pengajuan_count,
                get_kader_payment_count=get_kader_payment_count,
                get_pengajuan_tarik_count=get_pengajuan_tarik_count,
                get_pending_dokumen_count=get_pending_dokumen_count,
                get_umkm_penjual_count=get_umkm_penjual_count,
                get_umkm_pesanan_count=get_umkm_pesanan_count,
                get_pending_bonus_count=get_pending_bonus_count,
                get_pending_acc_pembayaran_count=get_pending_acc_pembayaran_count,
            )
        except Exception:
            return dict(pengaturan={}, get_calon_nasabah_count=lambda: 0, get_pending_pengajuan_count=lambda: 0)

    # Register blueprints
    from .routes.auth          import auth_bp
    from .routes.nasabah       import nasabah_bp
    from .routes.pinjaman      import pinjaman_bp
    from .routes.pembayaran    import pembayaran_bp
    from .routes.laporan       import laporan_bp
    from .routes.user_mgmt     import user_bp
    from .routes.main          import main_bp
    from .routes.import_export import import_export_bp
    from .routes.tabungan      import tabungan_bp
    from .routes.jaminan       import jaminan_bp
    from .routes.akuntansi     import akuntansi_bp
    from .routes.pengaturan    import pengaturan_bp
    from .routes.umkm          import umkm_bp
    from .routes.bonus         import bonus_bp
    from .routes.pemeriksaan   import pemeriksaan_bp
    from .routes.api           import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(nasabah_bp,       url_prefix='/nasabah')
    app.register_blueprint(pinjaman_bp,      url_prefix='/pinjaman')
    app.register_blueprint(pembayaran_bp,    url_prefix='/pembayaran')
    app.register_blueprint(laporan_bp,       url_prefix='/laporan')
    app.register_blueprint(user_bp,          url_prefix='/users')
    app.register_blueprint(main_bp)
    app.register_blueprint(import_export_bp, url_prefix='/import-export')
    app.register_blueprint(tabungan_bp,      url_prefix='/tabungan')
    app.register_blueprint(jaminan_bp,       url_prefix='/jaminan')
    app.register_blueprint(akuntansi_bp,     url_prefix='/akuntansi')
    app.register_blueprint(pengaturan_bp,    url_prefix='/pengaturan')
    app.register_blueprint(umkm_bp)
    app.register_blueprint(bonus_bp, url_prefix='/bonus')
    app.register_blueprint(pemeriksaan_bp, url_prefix='/pemeriksaan')
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()
        run_migrations(db.engine)
        _seed_admin(app)
        _seed_pengaturan(app)

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def _seed_admin(app):
    with app.app_context():
        try:
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', nama_lengkap='Administrator', role='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
        except Exception:
            db.session.rollback()


def _seed_pengaturan(app):
    with app.app_context():
        try:
            from .models import Pengaturan
            Pengaturan.seed_defaults()
        except Exception:
            db.session.rollback()
