from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User, Nasabah, RekeningTabungan, db
from ..utils.helpers import save_file, get_next_nasabah_id, validate_password, generate_random_password
from config import Config
from datetime import datetime
import uuid
import logging
import time

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Simple in-memory rate limiter for login attempts
_login_attempts = {}
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX = 5       # max attempts per window

def _check_rate_limit(identifier):
    """Check if login attempts exceed rate limit. Returns True if allowed."""
    now = time.time()
    attempts = _login_attempts.get(identifier, [])
    # Remove old attempts outside window
    attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    _login_attempts[identifier] = attempts
    if len(attempts) >= RATE_LIMIT_MAX:
        return False
    attempts.append(now)
    return True

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Rate limiting
        client_ip = request.remote_addr
        if not _check_rate_limit(f"login_{client_ip}_{username}"):
            flash('Terlalu banyak percobaan login. Silakan tunggu beberapa menit.', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username, aktif=True).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            logger.info('User logged in: %s from %s', username, request.remote_addr)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Username atau password salah.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pw = request.form.get('old_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')
        
        if not current_user.check_password(old_pw):
            flash('Password lama salah.', 'danger')
        elif new_pw != confirm_pw:
            flash('Konfirmasi password baru tidak cocok.', 'danger')
        else:
            # Menggunakan kebijakan password dari config jika ada
            min_len = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
            req_upper = current_app.config.get('PASSWORD_REQUIRE_UPPER', True)
            req_digit = current_app.config.get('PASSWORD_REQUIRE_DIGIT', True)
            req_special = current_app.config.get('PASSWORD_REQUIRE_SPECIAL', True)
            
            # Jika admin/staf, mungkin kebijakan lebih longgar (opsional)
            # Namun untuk keseragaman, gunakan validate_password
            pw_errors = validate_password(new_pw, min_len, req_upper, req_digit, req_special)
            
            if pw_errors:
                for e in pw_errors:
                    flash(e, 'danger')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                logger.info('User %s changed password', current_user.username)
                flash('Password berhasil diubah.', 'success')
                return redirect(url_for('main.dashboard'))
                
    return render_template('auth/change_password.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Pendaftaran mandiri oleh masyarakat sebagai calon nasabah."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # ── 1. Validasi akun ──────────────────────────────────────
        username = request.form.get('username', '').strip().lower()
        nama     = request.form.get('nama', '').strip().upper()
        password = request.form.get('password', '')
        pw_conf  = request.form.get('password_confirm', '')
        no_hp    = request.form.get('no_hp', '').strip()

        errors = []
        if len(username) < 4:
            errors.append('Username minimal 4 karakter.')
        if User.query.filter_by(username=username).first():
            errors.append(f'Username "{username}" sudah digunakan.')
        
        # Password validation with policy
        pw_errors = validate_password(
            password,
            min_length=current_app.config.get('PASSWORD_MIN_LENGTH', 8),
            require_upper=current_app.config.get('PASSWORD_REQUIRE_UPPER', True),
            require_digit=current_app.config.get('PASSWORD_REQUIRE_DIGIT', True),
            require_special=current_app.config.get('PASSWORD_REQUIRE_SPECIAL', True),
        )
        errors.extend(pw_errors)
        if password != pw_conf:
            errors.append('Password dan konfirmasi tidak cocok.')
        if not nama:
            errors.append('Nama lengkap wajib diisi.')

        # ── 2. Validasi data pribadi ──────────────────────────────
        nik        = request.form.get('nik', '').strip()
        kode_desa  = request.form.get('kode_desa', '').strip()
        if not nik or len(nik) != 16:
            errors.append('NIK harus 16 digit.')
        if Nasabah.query.filter_by(nik=nik).first():
            errors.append(f'NIK {nik} sudah terdaftar.')
        if not kode_desa:
            errors.append('Pilih desa terlebih dahulu.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/register.html', desa_list=Config.DESA_LIST)

        nama_desa = dict(Config.DESA_LIST).get(kode_desa, '')
        nasabah_id = get_next_nasabah_id(kode_desa)

        try:
            tgl_lahir = datetime.strptime(
                request.form.get('tanggal_lahir', ''), '%Y-%m-%d').date()
        except Exception:
            tgl_lahir = None

        # ── 3. Buat Nasabah (status = calon) ─────────────────────
        nasabah = Nasabah(
            nasabah_id     = nasabah_id,
            jenis          = 'perorangan',
            kode_desa      = kode_desa,
            nama_desa      = nama_desa,
            nama           = nama,
            nik            = nik,
            tempat_lahir   = request.form.get('tempat_lahir', '').upper(),
            tanggal_lahir  = tgl_lahir,
            jenis_kelamin  = request.form.get('jenis_kelamin', ''),
            alamat         = request.form.get('alamat', ''),
            no_hp          = no_hp,
            pekerjaan      = request.form.get('pekerjaan', ''),
            nama_pasangan  = request.form.get('nama_pasangan', '').upper(),
            status         = 'calon',
            keterangan_status = 'Pendaftaran mandiri via website. Menunggu verifikasi admin.',
        )

        # Upload dokumen
        prefix = nasabah_id.replace('-', '')
        for field, subfolder, force_portrait in [
            ('foto', 'foto', True), ('ktp', 'ktp', False), ('kk', 'kk', False),
            ('surat_usaha', 'sku', False), ('bukti_penghasilan', 'penghasilan', False),
            ('jaminan', 'jaminan', False),
        ]:
            new_f = save_file(request.files.get(field), subfolder, prefix, force_portrait=force_portrait)
            if new_f:
                setattr(nasabah, field, new_f)

        db.session.add(nasabah)
        db.session.flush()

        # Auto-buat rekening tabungan
        rek = RekeningTabungan(
            nasabah_id=nasabah.id,
            no_rekening=f"TAB-{nasabah_id}",
        )
        db.session.add(rek)

        # ── 4. Buat User (role = nasabah, linked to nasabah) ─────
        user = User(
            username      = username,
            nama_lengkap  = nama,
            role          = 'nasabah',
            aktif         = True,
            nasabah_id_fk = nasabah.id,
        )
        user.set_password(password)
        # Set created_by on nasabah after we have the user
        db.session.add(user)
        db.session.flush()
        nasabah.created_by = user.id

        db.session.commit()

        flash(
            f'Pendaftaran berhasil! ID Nasabah Anda: {nasabah_id}. '
            f'Silakan login dengan username "{username}". '
            f'Data Anda akan diverifikasi oleh admin.',
            'success'
        )
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', desa_list=Config.DESA_LIST)
