from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ...models import db, User, Nasabah, RekeningTabungan
from ...utils.helpers import validate_password, get_next_nasabah_id
from config import Config
from . import api_bp, get_current_user
from datetime import timedelta, datetime
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    fcm_token = data.get('fcm_token', '')

    if not username or not password:
        return jsonify(success=False, message='Username dan password wajib diisi'), 400

    user = User.query.filter_by(username=username, aktif=True).first()
    if not user or not user.check_password(password):
        return jsonify(success=False, message='Username atau password salah'), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            'role': user.role,
            'nama': user.nama_lengkap,
        },
        expires_delta=timedelta(days=30)
    )

    if fcm_token:
        try:
            from ...models import FCMToken
            existing = FCMToken.query.filter_by(token=fcm_token).first()
            if existing:
                existing.user_id = user.id
            else:
                db.session.add(FCMToken(token=fcm_token, user_id=user.id))
            db.session.commit()
        except Exception:
            db.session.rollback()

    user_data = {
        'id': user.id,
        'username': user.username,
        'nama_lengkap': user.nama_lengkap,
        'role': user.role,
        'role_label': user.role_label(),
        'kode_desa': user.kode_desa,
        'nasabah_id': user.nasabah_id_fk,
    }

    return jsonify(success=True, data={
        'token': access_token,
        'user': user_data,
    })


@api_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def me():
    user = get_current_user()
    if not user:
        return jsonify(success=False, message='User not found'), 404

    nasabah = None
    rekening = None
    if user.nasabah_id_fk:
        n = db.session.get(Nasabah, user.nasabah_id_fk)
        if n:
            nasabah = {
                'id': n.id,
                'nasabah_id': n.nasabah_id,
                'nama': n.nama,
                'nik': n.nik,
                'jenis': n.jenis,
                'kode_desa': n.kode_desa,
                'nama_desa': n.nama_desa,
                'status': n.status,
                'no_hp': n.no_hp or '',
                'alamat': n.alamat or '',
                'foto': n.foto,
                'ktp': n.ktp,
                'kk': n.kk,
                'surat_usaha': n.surat_usaha,
                'bukti_penghasilan': n.bukti_penghasilan,
                'jaminan': n.jaminan,
                'tempat_lahir': n.tempat_lahir or '',
                'tanggal_lahir': str(n.tanggal_lahir) if n.tanggal_lahir else '',
                'jenis_kelamin': n.jenis_kelamin or '',
                'pekerjaan': n.pekerjaan or '',
            }
            if n.rekening:
                r = n.rekening
                rekening = {
                    'id': r.id,
                    'no_rekening': r.no_rekening,
                    'saldo_pokok': r.saldo_pokok,
                    'saldo_wajib': r.saldo_wajib,
                    'saldo_sukarela': r.saldo_sukarela,
                    'total_saldo': r.total_saldo(),
                }

    return jsonify(success=True, data={
        'user': {
            'id': user.id,
            'username': user.username,
            'nama_lengkap': user.nama_lengkap,
            'role': user.role,
            'role_label': user.role_label(),
            'kode_desa': user.kode_desa,
            'tanda_tangan': user.tanda_tangan,
        },
        'nasabah': nasabah,
        'rekening': rekening,
    })


@api_bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')

    if not user.check_password(old_pw):
        return jsonify(success=False, message='Password lama salah'), 400

    pw_errors = validate_password(new_pw)
    if pw_errors:
        return jsonify(success=False, message='; '.join(pw_errors)), 400

    user.set_password(new_pw)
    db.session.commit()
    logger.info('User %s changed password via API', user.username)
    return jsonify(success=True, message='Password berhasil diubah')


@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    username = data.get('username', '').strip().lower()
    nama = data.get('nama', '').strip().upper()
    password = data.get('password', '')
    nik = data.get('nik', '').strip()
    no_hp = data.get('no_hp', '').strip()
    kode_desa = data.get('kode_desa', '').strip()
    alamat = data.get('alamat', '')
    tempat_lahir = data.get('tempat_lahir', '')
    tanggal_lahir = data.get('tanggal_lahir', '')
    jenis_kelamin = data.get('jenis_kelamin', '')
    pekerjaan = data.get('pekerjaan', '')
    nama_pasangan = data.get('nama_pasangan', '').upper()

    errors = []
    if len(username) < 4:
        errors.append('Username minimal 4 karakter')
    if User.query.filter_by(username=username).first():
        errors.append(f'Username "{username}" sudah digunakan')
    pw_errors = validate_password(password)
    errors.extend(pw_errors)
    if not nik or len(nik) != 16:
        errors.append('NIK harus 16 digit')
    if Nasabah.query.filter_by(nik=nik).first():
        errors.append(f'NIK {nik} sudah terdaftar')
    if not kode_desa:
        errors.append('Pilih desa')
    if not nama:
        errors.append('Nama wajib diisi')

    if errors:
        return jsonify(success=False, message='; '.join(errors)), 400

    kode_desa_upper = kode_desa.upper()
    nama_desa = dict(Config.DESA_LIST).get(kode_desa_upper, '')
    if not nama_desa:
        return jsonify(success=False, message='Kode desa tidak valid'), 400

    nasabah_id = get_next_nasabah_id(kode_desa_upper)
    tgl_lahir = None
    if tanggal_lahir:
        try:
            tgl_lahir = datetime.strptime(tanggal_lahir, '%Y-%m-%d').date()
        except ValueError:
            pass

    try:
        nasabah = Nasabah(
            nasabah_id=nasabah_id,
            jenis='perorangan',
            kode_desa=kode_desa_upper,
            nama_desa=nama_desa,
            nama=nama,
            nik=nik,
            tempat_lahir=tempat_lahir.upper(),
            tanggal_lahir=tgl_lahir,
            jenis_kelamin=jenis_kelamin,
            alamat=alamat,
            no_hp=no_hp,
            pekerjaan=pekerjaan,
            nama_pasangan=nama_pasangan,
            status='calon',
            keterangan_status='Pendaftaran via aplikasi. Menunggu verifikasi admin.',
        )

        db.session.add(nasabah)
        db.session.flush()

        rek = RekeningTabungan(
            nasabah_id=nasabah.id,
            no_rekening=f"TAB-{nasabah_id}",
        )
        db.session.add(rek)

        user = User(
            username=username,
            nama_lengkap=nama,
            role='nasabah',
            aktif=True,
            nasabah_id_fk=nasabah.id,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        nasabah.created_by = user.id

        db.session.commit()
        logger.info('New mobile registration: %s (%s)', username, nasabah_id)

        return jsonify(success=True, message=f'Pendaftaran berhasil! ID Nasabah: {nasabah_id}. Menunggu verifikasi admin.', data={
            'nasabah_id': nasabah_id,
            'username': username,
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.exception('Registration failed')
        return jsonify(success=False, message=f'Gagal mendaftar: {str(e)}'), 500
