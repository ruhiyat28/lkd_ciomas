from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ...models import db, Pinjaman, Nasabah, hitung_angsuran_bulat
from config import Config
from . import api_bp, get_current_user
from datetime import date, datetime, timezone
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/pinjaman', methods=['GET'])
@jwt_required()
def list_pinjaman():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')
    search = request.args.get('q', '')
    nasabah_id = request.args.get('nasabah_id', type=int)

    q = Pinjaman.query

    if user.is_kader():
        q = q.join(Nasabah).filter(Nasabah.kode_desa == user.kode_desa)
    elif user.is_nasabah():
        q = q.filter_by(nasabah_id_fk=user.nasabah_id_fk)
    elif nasabah_id:
        q = q.filter_by(nasabah_id_fk=nasabah_id)

    if status:
        if status == 'aktif':
            q = q.filter_by(status='cair')
        else:
            q = q.filter_by(status=status)

    if search:
        q = q.filter(Pinjaman.spk.ilike(f'%{search}%'))

    q = q.order_by(Pinjaman.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    result = []
    for p in pagination.items:
        kolek, kolek_label = ('', '')
        if p.status == 'cair':
            kolek, kolek_label = p.get_kolektibilitas()
        pokok_bayar, jasa_bayar = p.get_realisasi_pembayaran()
        tunggak_pokok, tunggak_jasa, bulan_nunggak = p.get_tunggakan()

        result.append({
            'id': p.id,
            'spk': p.spk,
            'jenis_pinjaman': p.jenis_pinjaman,
            'nasabah_id': p.nasabah_id_fk,
            'nasabah': p.nasabah.nama if p.nasabah else '',
            'nasabah_nasabah_id': p.nasabah.nasabah_id if p.nasabah else '',
            'no_hp': p.nasabah.no_hp if p.nasabah else '',
            'no_hp_pasangan': p.nasabah.no_hp_pasangan if p.nasabah else '',
            'jumlah_pinjaman': p.jumlah_pinjaman,
            'jasa_persen': p.jasa_persen,
            'tenor': p.tenor,
            'status': p.status,
            'tanggal_pengajuan': str(p.tanggal_pengajuan) if p.tanggal_pengajuan else '',
            'tanggal_cair': str(p.tanggal_cair) if p.tanggal_cair else '',
            'angsuran_pokok': p.angsuran_pokok,
            'angsuran_jasa': p.angsuran_jasa,
            'angsuran_total': p.angsuran_total,
            'saldo_pokok': p.get_saldo_pokok(),
            'pokok_terbayar': pokok_bayar,
            'jasa_terbayar': jasa_bayar,
            'tunggakan_pokok': tunggak_pokok,
            'tunggakan_jasa': tunggak_jasa,
            'bulan_nunggak': bulan_nunggak,
            'kolektibilitas': kolek,
            'kolektibilitas_label': kolek_label,
            'tujuan': p.tujuan or '',
            'created_at': str(p.created_at) if p.created_at else '',
        })

    return jsonify(success=True, data=result, pagination={
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    })


@api_bp.route('/pinjaman/<int:id>', methods=['GET'])
@jwt_required()
def detail_pinjaman(id):
    user = get_current_user()
    p = db.session.get(Pinjaman, id)
    if not p:
        return jsonify(success=False, message='Pinjaman tidak ditemukan'), 404

    if user.is_kader() and p.nasabah.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403
    if user.is_nasabah() and p.nasabah_id_fk != user.nasabah_id_fk:
        return jsonify(success=False, message='Forbidden'), 403

    pokok_bayar, jasa_bayar = p.get_realisasi_pembayaran()
    kolek, kolek_label = ('', '')
    if p.status == 'cair':
        kolek, kolek_label = p.get_kolektibilitas()
    tunggak_pokok, tunggak_jasa, bulan_nunggak = p.get_tunggakan()
    jadwal = p.get_jadwal_angsuran()

    data = {
        'id': p.id,
        'spk': p.spk,
        'jenis_pinjaman': p.jenis_pinjaman,
        'nasabah': {
            'id': p.nasabah.id,
            'nasabah_id': p.nasabah.nasabah_id,
            'nama': p.nasabah.nama,
            'nik': p.nasabah.nik,
            'kode_desa': p.nasabah.kode_desa,
            'nama_desa': p.nasabah.nama_desa,
        },
        'jumlah_pinjaman': p.jumlah_pinjaman,
        'jasa_persen': p.jasa_persen,
        'tenor': p.tenor,
        'tujuan': p.tujuan or '',
        'status': p.status,
        'tanggal_pengajuan': str(p.tanggal_pengajuan) if p.tanggal_pengajuan else '',
        'tanggal_acc': str(p.tanggal_acc) if p.tanggal_acc else '',
        'tanggal_cair': str(p.tanggal_cair) if p.tanggal_cair else '',
        'tanggal_mulai_angsuran': str(p.tanggal_mulai_angsuran) if p.tanggal_mulai_angsuran else '',
        'angsuran_pokok': p.angsuran_pokok,
        'angsuran_jasa': p.angsuran_jasa,
        'angsuran_total': p.angsuran_total,
        'angsuran_terakhir_pokok': p.angsuran_terakhir_pokok,
        'saldo_pokok': p.get_saldo_pokok(),
        'pokok_terbayar': pokok_bayar,
        'jasa_terbayar': jasa_bayar,
        'kolektibilitas': kolek,
        'kolektibilitas_label': kolek_label,
        'tunggakan_pokok': tunggak_pokok,
        'tunggakan_jasa': tunggak_jasa,
        'bulan_nunggak': bulan_nunggak,
        'jadwal_angsuran': [{
            'ke': j['ke'],
            'tanggal': str(j['tanggal']),
            'pokok': j['pokok'],
            'jasa': j['jasa'],
            'total': j['total'],
            'lunas': j['lunas'],
            'terlambat': j['terlambat'],
        } for j in jadwal],
        'created_at': str(p.created_at) if p.created_at else '',
    }

    return jsonify(success=True, data=data)


@api_bp.route('/pinjaman/hitung-angsuran', methods=['POST'])
@jwt_required()
def hitung_angsuran():
    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    jumlah = int(data.get('jumlah', 0))
    tenor = int(data.get('tenor', 0))
    jasa_persen = float(data.get('jasa_persen', 1.5))

    if tenor not in Config.TENOR_OPTIONS:
        return jsonify(success=False, message=f'Tenor tidak valid. Pilihan: {Config.TENOR_OPTIONS}'), 400
    if jumlah <= 0:
        return jsonify(success=False, message='Jumlah pinjaman harus lebih dari 0'), 400

    hasil = hitung_angsuran_bulat(jumlah, tenor, jasa_persen)
    return jsonify(success=True, data=hasil)


@api_bp.route('/pinjaman', methods=['POST'])
@jwt_required()
def create_pinjaman():
    user = get_current_user()

    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    if user.is_nasabah():
        nasabah = user.nasabah
        if not nasabah:
            return jsonify(success=False, message='Akun nasabah tidak memiliki data nasabah'), 400
        if nasabah.status != 'aktif':
            return jsonify(success=False, message='Akun nasabah belum aktif'), 400
    elif user.can_write_pinjaman():
        try:
            nasabah_id = int(data['nasabah_id']) if data.get('nasabah_id') is not None else None
        except (ValueError, TypeError):
            nasabah_id = None
        if not nasabah_id:
            return jsonify(success=False, message='nasabah_id required'), 400
        nasabah = db.session.get(Nasabah, nasabah_id)
        if not nasabah:
            return jsonify(success=False, message='Nasabah tidak ditemukan'), 404
        if user.is_kader() and nasabah.kode_desa != user.kode_desa:
            return jsonify(success=False, message='Forbidden'), 403
    else:
        return jsonify(success=False, message='Forbidden'), 403

    jumlah = int(data.get('jumlah', 0))
    tenor = int(data.get('tenor', 0))
    jasa_persen = float(data.get('jasa_persen', 1.5))
    jenis_pinjaman = data.get('jenis_pinjaman', 'reguler')
    tujuan = data.get('tujuan', '')

    angsuran = hitung_angsuran_bulat(jumlah, tenor, jasa_persen)

    max_id = db.session.query(db.func.max(Pinjaman.id)).scalar() or 0
    spk = Config.format_spk(date.today().year, max_id + 1)

    pinjaman = Pinjaman(
        spk=spk,
        jenis_pinjaman=jenis_pinjaman,
        nasabah_id_fk=nasabah.id,
        jumlah_pinjaman=jumlah,
        jasa_persen=jasa_persen,
        tenor=tenor,
        tujuan=tujuan,
        tanggal_pengajuan=date.today(),
        status='pengajuan',
        angsuran_pokok=angsuran['pokok'],
        angsuran_jasa=angsuran['jasa'],
        angsuran_total=angsuran['total'],
        angsuran_terakhir_pokok=angsuran['pokok_terakhir'],
        created_by=user.id,
    )

    db.session.add(pinjaman)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal membuat pinjaman')
        return jsonify(success=False, message=f'Gagal membuat pinjaman: {str(e)}'), 500

    return jsonify(success=True, message='Pinjaman berhasil diajukan', data={
        'id': pinjaman.id,
        'spk': pinjaman.spk,
    }), 201


@api_bp.route('/pinjaman/<int:id>/verifikasi', methods=['PUT'])
@jwt_required()
def verifikasi_pinjaman(id):
    user = get_current_user()
    if not (user.is_verifikator() or user.is_admin() or user.is_manajer() or user.is_kredit()):
        return jsonify(success=False, message='Forbidden'), 403

    p = db.session.get(Pinjaman, id)
    if not p:
        return jsonify(success=False, message='Pinjaman tidak ditemukan'), 404

    if p.status not in ('cek_dokumen', 'verifikasi'):
        return jsonify(success=False, message=f'Status pinjaman "{p.status}" tidak bisa diverifikasi'), 400

    if user.is_kader() and p.nasabah.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Data wajib diisi'), 400

    rekomendasi = data.get('rekomendasi', '').strip()
    if rekomendasi not in ('layak', 'tidak_layak'):
        return jsonify(success=False, message='Rekomendasi harus "layak" atau "tidak_layak"'), 400

    p.rekomendasi = rekomendasi
    p.hasil_kunjungan = data.get('catatan', '')
    p.verified_by = user.id
    p.verified_at = datetime.now(timezone.utc)

    if rekomendasi == 'layak':
        p.status = 'acc_direktur'
    else:
        p.status = 'ditolak'
        p.jumlah_penolakan = (p.jumlah_penolakan or 0) + 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f'Gagal menyimpan verifikasi: {str(e)}'), 500

    return jsonify(success=True, message=f'Verifikasi tersimpan: {rekomendasi}', data={
        'status': p.status,
        'rekomendasi': p.rekomendasi,
    })



