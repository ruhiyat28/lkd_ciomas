from flask import request, jsonify
from flask_jwt_extended import jwt_required
from ...models import db, Nasabah, AnggotaKelompok, RekeningTabungan, User
from ...utils.helpers import get_next_nasabah_id, save_file
from config import Config
from . import api_bp, get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/nasabah', methods=['GET'])
@jwt_required()
def list_nasabah():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    desa = request.args.get('desa', '')
    status = request.args.get('status', '')
    jenis = request.args.get('jenis', '')
    search = request.args.get('q', '')

    q = Nasabah.query
    if user.is_kader():
        q = q.filter_by(kode_desa=user.kode_desa)
    elif user.is_nasabah():
        q = q.filter_by(id=user.nasabah_id_fk)
    elif desa:
        q = q.filter_by(kode_desa=desa)

    if status:
        q = q.filter_by(status=status)
    if jenis:
        q = q.filter_by(jenis=jenis)
    if search:
        q = q.filter(Nasabah.nama.ilike(f'%{search}%') |
                     Nasabah.nasabah_id.ilike(f'%{search}%') |
                     Nasabah.nik.ilike(f'%{search}%'))

    q = q.order_by(Nasabah.nasabah_id)
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    result = []
    for n in pagination.items:
        result.append(_nasabah_dict(n))

    return jsonify(success=True, data=result, pagination={
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    })


@api_bp.route('/nasabah/count', methods=['GET'])
@jwt_required()
def count_nasabah():
    user = get_current_user()
    q = Nasabah.query
    if user.is_kader():
        q = q.filter_by(kode_desa=user.kode_desa)

    return jsonify(success=True, data={
        'perorangan': q.filter_by(jenis='perorangan', status='aktif').count(),
        'kelompok': q.filter_by(jenis='kelompok', status='aktif').count(),
        'calon': q.filter_by(status='calon').count(),
        'total_aktif': q.filter_by(status='aktif').count(),
    })


@api_bp.route('/nasabah/saya', methods=['GET'])
@jwt_required()
def get_my_nasabah():
    user = get_current_user()
    if not user.is_nasabah() or not user.nasabah:
        return jsonify(success=False, message='Not found'), 404
    n = user.nasabah
    return jsonify(success=True, data={
        'id': n.id,
        'nasabah_id': n.nasabah_id,
        'nama': n.nama,
        'nik': n.nik,
        'nama_desa': n.nama_desa,
        'status': n.status,
        'no_hp': n.no_hp or '',
        'alamat': n.alamat or '',
        'pekerjaan': n.pekerjaan or '',
    })


@api_bp.route('/nasabah/<int:id>', methods=['GET'])
@jwt_required()
def detail_nasabah(id):
    user = get_current_user()
    n = db.session.get(Nasabah, id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404

    if user.is_kader() and n.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403
    if user.is_nasabah() and n.id != user.nasabah_id_fk:
        return jsonify(success=False, message='Forbidden'), 403

    data = _nasabah_dict(n, detail=True)

    if n.jenis == 'kelompok':
        anggota = AnggotaKelompok.query.filter_by(kelompok_id=n.id).order_by(AnggotaKelompok.urut).all()
        data['anggota'] = [{
            'id': a.id,
            'urut': a.urut,
            'nama': a.nama,
            'nik': a.nik or '',
            'jabatan': a.jabatan,
            'no_hp': a.no_hp or '',
            'alamat': a.alamat or '',
        } for a in anggota]

    pinjaman_list = []
    for p in n.pinjaman:
        pokok_terbayar, jasa_terbayar = p.get_realisasi_pembayaran()
        pinjaman_list.append({
            'id': p.id,
            'spk': p.spk,
            'jenis_pinjaman': p.jenis_pinjaman,
            'jumlah_pinjaman': p.jumlah_pinjaman,
            'tenor': p.tenor,
            'status': p.status,
            'tanggal_pengajuan': str(p.tanggal_pengajuan) if p.tanggal_pengajuan else '',
            'tanggal_cair': str(p.tanggal_cair) if p.tanggal_cair else '',
            'angsuran_pokok': p.angsuran_pokok,
            'angsuran_jasa': p.angsuran_jasa,
            'angsuran_total': p.angsuran_total,
            'saldo_pokok': p.get_saldo_pokok(),
            'pokok_terbayar': pokok_terbayar,
            'jasa_terbayar': jasa_terbayar,
        })
    data['pinjaman'] = pinjaman_list

    return jsonify(success=True, data=data)


@api_bp.route('/nasabah', methods=['POST'])
@jwt_required()
def create_nasabah():
    user = get_current_user()
    if not user.can_write_nasabah():
        return jsonify(success=False, message='Forbidden'), 403

    data = request.form.to_dict() if request.form else (request.get_json() or {})
    jenis = data.get('jenis', 'perorangan')
    kode_desa = data.get('kode_desa', '')
    if user.is_kader():
        kode_desa = user.kode_desa

    if not kode_desa:
        return jsonify(success=False, message='Kode desa wajib diisi'), 400

    kode_desa = kode_desa.upper()
    nama_desa = dict(Config.DESA_LIST).get(kode_desa, '')
    if not nama_desa:
        return jsonify(success=False, message='Kode desa tidak valid'), 400

    nasabah_id = get_next_nasabah_id(kode_desa)
    nik = data.get('nik', '').strip()
    if not nik:
        nik = f"NOID-{__import__('uuid').uuid4().hex[:12].upper()}"
    elif Nasabah.query.filter_by(nik=nik).first():
        return jsonify(success=False, message=f'NIK {nik} sudah terdaftar'), 400

    tgl_lahir = None
    tgl_str = data.get('tanggal_lahir', '')
    if tgl_str:
        try:
            tgl_lahir = datetime.strptime(tgl_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    nasabah = Nasabah(
        nasabah_id=nasabah_id,
        jenis=jenis,
        kode_desa=kode_desa,
        nama_desa=nama_desa,
        nama=data.get('nama', '').upper(),
        nik=nik,
        tempat_lahir=data.get('tempat_lahir', '').upper(),
        tanggal_lahir=tgl_lahir,
        jenis_kelamin=data.get('jenis_kelamin', ''),
        alamat=data.get('alamat', ''),
        no_hp=data.get('no_hp', ''),
        pekerjaan=data.get('pekerjaan', ''),
        nama_pasangan=data.get('nama_pasangan', '').upper(),
        nik_pasangan=data.get('nik_pasangan', ''),
        no_hp_pasangan=data.get('no_hp_pasangan', ''),
        keterangan_jaminan=data.get('keterangan_jaminan', ''),
        status='aktif' if not user.is_kader() else 'calon',
        created_by=user.id,
    )

    db.session.add(nasabah)
    db.session.flush()

    rek = RekeningTabungan(nasabah_id=nasabah.id, no_rekening=f"TAB-{nasabah_id}")
    db.session.add(rek)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal menyimpan nasabah')
        return jsonify(success=False, message=f'Gagal menyimpan: {str(e)}'), 500

    return jsonify(success=True, message='Nasabah berhasil ditambahkan', data={
        'id': nasabah.id,
        'nasabah_id': nasabah_id,
    }), 201


@api_bp.route('/nasabah/<int:id>', methods=['PUT'])
@jwt_required()
def update_nasabah(id):
    user = get_current_user()
    n = db.session.get(Nasabah, id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404

    if user.is_kader() and n.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    data = request.form.to_dict() if request.form else (request.get_json() or {})

    if 'nama' in data:
        n.nama = data['nama'].upper()
    if 'nik' in data:
        nik_baru = data['nik'].strip()
        if nik_baru and nik_baru != n.nik:
            if Nasabah.query.filter_by(nik=nik_baru).first():
                return jsonify(success=False, message=f'NIK {nik_baru} sudah terdaftar'), 400
            n.nik = nik_baru
    if 'tempat_lahir' in data:
        n.tempat_lahir = data['tempat_lahir'].upper()
    if 'tanggal_lahir' in data and data['tanggal_lahir']:
        try:
            n.tanggal_lahir = datetime.strptime(data['tanggal_lahir'], '%Y-%m-%d').date()
        except ValueError:
            pass
    if 'jenis_kelamin' in data:
        n.jenis_kelamin = data['jenis_kelamin']
    if 'alamat' in data:
        n.alamat = data['alamat']
    if 'no_hp' in data:
        n.no_hp = data['no_hp']
    if 'pekerjaan' in data:
        n.pekerjaan = data['pekerjaan']
    if 'nama_pasangan' in data:
        n.nama_pasangan = data['nama_pasangan'].upper()
    if 'nik_pasangan' in data:
        n.nik_pasangan = data['nik_pasangan']
    if 'no_hp_pasangan' in data:
        n.no_hp_pasangan = data['no_hp_pasangan']
    if 'keterangan_jaminan' in data:
        n.keterangan_jaminan = data['keterangan_jaminan']
    if 'status' in data:
        n.status = data['status']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal memperbarui nasabah')
        return jsonify(success=False, message=f'Gagal memperbarui: {str(e)}'), 500

    return jsonify(success=True, message='Data nasabah diperbarui')


@api_bp.route('/nasabah/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_nasabah(id):
    user = get_current_user()
    if not user.is_admin():
        return jsonify(success=False, message='Forbidden'), 403

    n = db.session.get(Nasabah, id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404

    if n.pinjaman:
        return jsonify(success=False, message='Tidak dapat menghapus nasabah yang memiliki riwayat pinjaman'), 400

    try:
        related_user = User.query.filter_by(nasabah_id_fk=n.id).first()
        if related_user:
            if n.created_by == related_user.id:
                n.created_by = None
                db.session.flush()
            db.session.delete(related_user)
        if n.rekening:
            from ...models import TransaksiTabungan
            TransaksiTabungan.query.filter_by(rekening_id=n.rekening.id).delete()
            db.session.delete(n.rekening)
        AnggotaKelompok.query.filter_by(kelompok_id=n.id).delete()
        db.session.delete(n)
        db.session.commit()
        return jsonify(success=True, message='Nasabah berhasil dihapus')
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal menghapus nasabah')
        return jsonify(success=False, message=f'Gagal menghapus: {str(e)}'), 500


@api_bp.route('/nasabah/<int:id>/approve', methods=['POST'])
@jwt_required()
def approve_nasabah(id):
    user = get_current_user()
    if not (user.is_admin() or user.is_manajer() or user.is_staf()):
        return jsonify(success=False, message='Forbidden'), 403

    n = db.session.get(Nasabah, id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404

    data = request.get_json() or {}
    action = data.get('action', 'approve')

    if action == 'approve':
        n.status = 'aktif'
        n.keterangan_status = 'Pendaftaran Anda telah disetujui.'
        db.session.commit()
        return jsonify(success=True, message=f'Nasabah {n.nama} telah disetujui')
    elif action == 'reject':
        db.session.delete(n)
        db.session.commit()
        return jsonify(success=True, message='Pendaftaran ditolak')
    else:
        return jsonify(success=False, message='Aksi tidak dikenal'), 400


def _nasabah_dict(n, detail=False):
    d = {
        'id': n.id,
        'nasabah_id': n.nasabah_id,
        'jenis': n.jenis,
        'kode_desa': n.kode_desa,
        'nama_desa': n.nama_desa,
        'nama': n.nama,
        'nik': n.nik,
        'status': n.status,
        'keterangan_status': n.keterangan_status or '',
        'no_hp': n.no_hp or '',
        'alamat': n.alamat or '',
        'pekerjaan': n.pekerjaan or '',
        'foto': n.foto,
        'ktp': n.ktp,
        'kk': n.kk,
        'surat_usaha': n.surat_usaha,
        'bukti_penghasilan': n.bukti_penghasilan,
        'jaminan': n.jaminan,
        'created_at': str(n.created_at) if n.created_at else '',
    }
    if detail:
        d.update({
            'tempat_lahir': n.tempat_lahir or '',
            'tanggal_lahir': str(n.tanggal_lahir) if n.tanggal_lahir else '',
            'jenis_kelamin': n.jenis_kelamin or '',
            'nama_pasangan': n.nama_pasangan or '',
            'nik_pasangan': n.nik_pasangan or '',
            'no_hp_pasangan': n.no_hp_pasangan or '',
            'keterangan_jaminan': n.keterangan_jaminan or '',
            'tanda_tangan': n.tanda_tangan,
            'dokumen_lengkap': n.dokumen_lengkap(),
        })
        if n.rekening:
            d['rekening'] = {
                'id': n.rekening.id,
                'no_rekening': n.rekening.no_rekening,
                'saldo_pokok': n.rekening.saldo_pokok,
                'saldo_wajib': n.rekening.saldo_wajib,
                'saldo_sukarela': n.rekening.saldo_sukarela,
                'total_saldo': n.rekening.total_saldo(),
            }
    return d
