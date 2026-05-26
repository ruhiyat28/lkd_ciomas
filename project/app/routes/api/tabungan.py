from flask import request, jsonify
from flask_jwt_extended import jwt_required
from ...models import db, Nasabah, RekeningTabungan, TransaksiTabungan
from . import api_bp, get_current_user
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/tabungan', methods=['GET'])
@jwt_required()
def get_tabungan():
    user = get_current_user()
    nasabah_id = request.args.get('nasabah_id', type=int)

    if user.is_nasabah():
        nasabah_id = user.nasabah_id_fk

    if not nasabah_id:
        return jsonify(success=False, message='Parameter nasabah_id diperlukan'), 400

    n = db.session.get(Nasabah, nasabah_id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404
    if user.is_kader() and n.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    rek = n.rekening
    if not rek:
        return jsonify(success=False, message='Rekening tidak ditemukan'), 404

    transaksi = TransaksiTabungan.query.filter_by(rekening_id=rek.id)\
        .order_by(TransaksiTabungan.tanggal.desc(), TransaksiTabungan.created_at.desc())\
        .limit(50).all()

    has_active_loan = rek.punya_pinjaman_aktif()

    return jsonify(success=True, data={
        'id': rek.id,
        'no_rekening': rek.no_rekening,
        'nasabah_id': n.id,
        'nasabah_nama': n.nama,
        'saldo_pokok': rek.saldo_pokok,
        'saldo_wajib': rek.saldo_wajib,
        'saldo_sukarela': rek.saldo_sukarela,
        'total_saldo': rek.total_saldo(),
        'saldo_bisa_tarik': rek.saldo_bisa_tarik(),
        'punya_pinjaman_aktif': has_active_loan,
        'transaksi': [{
            'id': t.id,
            'tanggal': str(t.tanggal),
            'jenis': t.jenis,
            'kategori': t.kategori,
            'jumlah': t.jumlah,
            'keterangan': t.keterangan or '',
            'no_bukti': t.no_bukti or '',
        } for t in transaksi],
    })


@api_bp.route('/tabungan/setor', methods=['POST'])
@jwt_required()
def setor_tabungan():
    user = get_current_user()
    if not user.can_write_pembayaran():
        return jsonify(success=False, message='Forbidden'), 403

    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    try:
        nasabah_id = int(data['nasabah_id']) if data.get('nasabah_id') is not None else None
    except (ValueError, TypeError):
        nasabah_id = None
    kategori = data.get('kategori', 'sukarela')
    try:
        jumlah = int(data.get('jumlah', 0))
    except (ValueError, TypeError):
        jumlah = 0
    tanggal_str = data.get('tanggal', '')
    keterangan = data.get('keterangan', '')

    if not nasabah_id or jumlah <= 0:
        return jsonify(success=False, message='nasabah_id dan jumlah wajib diisi'), 400
    if kategori not in ('pokok', 'wajib', 'sukarela'):
        return jsonify(success=False, message='Kategori tidak valid'), 400

    n = db.session.get(Nasabah, nasabah_id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404
    if user.is_kader() and n.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    rek = n.rekening
    if not rek:
        return jsonify(success=False, message='Rekening tidak ditemukan'), 404

    try:
        tgl = datetime.strptime(tanggal_str, '%Y-%m-%d').date() if tanggal_str else date.today()
    except ValueError:
        tgl = date.today()

    if kategori == 'pokok':
        rek.saldo_pokok += jumlah
    elif kategori == 'wajib':
        rek.saldo_wajib += jumlah
    else:
        rek.saldo_sukarela += jumlah

    no_bukti = f"TAB/{tgl.year}/{tgl.month:02d}/{TransaksiTabungan.query.filter(TransaksiTabungan.tanggal == tgl).count() + 1:04d}"

    transaksi = TransaksiTabungan(
        rekening_id=rek.id,
        tanggal=tgl,
        jenis='setor',
        kategori=kategori,
        jumlah=jumlah,
        keterangan=keterangan or f'Setoran {kategori}',
        no_bukti=no_bukti,
        created_by=user.id,
    )
    db.session.add(transaksi)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal menyetor tabungan')
        return jsonify(success=False, message=f'Gagal menyetor: {str(e)}'), 500

    return jsonify(success=True, message=f'Setoran {kategori} berhasil', data={
        'id': transaksi.id,
        'no_bukti': no_bukti,
        'saldo_pokok': rek.saldo_pokok,
        'saldo_wajib': rek.saldo_wajib,
        'saldo_sukarela': rek.saldo_sukarela,
    }), 201


@api_bp.route('/tabungan/tarik', methods=['POST'])
@jwt_required()
def tarik_tabungan():
    user = get_current_user()
    if not user.can_write_pembayaran():
        return jsonify(success=False, message='Forbidden'), 403

    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    try:
        nasabah_id = int(data['nasabah_id']) if data.get('nasabah_id') is not None else None
    except (ValueError, TypeError):
        nasabah_id = None
    kategori = data.get('kategori', 'sukarela')
    try:
        jumlah = int(data.get('jumlah', 0))
    except (ValueError, TypeError):
        jumlah = 0
    tanggal_str = data.get('tanggal', '')
    keterangan = data.get('keterangan', '')

    if not nasabah_id or jumlah <= 0:
        return jsonify(success=False, message='nasabah_id dan jumlah wajib diisi'), 400
    if kategori not in ('pokok', 'wajib', 'sukarela'):
        return jsonify(success=False, message='Kategori tidak valid'), 400

    n = db.session.get(Nasabah, nasabah_id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404
    if user.is_kader() and n.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    rek = n.rekening
    if not rek:
        return jsonify(success=False, message='Rekening tidak ditemukan'), 404

    if kategori == 'pokok':
        if rek.saldo_pokok < jumlah:
            return jsonify(success=False, message='Saldo pokok tidak mencukupi'), 400
        if not rek.saldo_bisa_tarik():
            return jsonify(success=False, message='Tidak bisa tarik saldo pokok jika ada pinjaman aktif'), 400
        rek.saldo_pokok -= jumlah
    elif kategori == 'wajib':
        if rek.saldo_wajib < jumlah:
            return jsonify(success=False, message='Saldo wajib tidak mencukupi'), 400
        if not rek.saldo_bisa_tarik():
            return jsonify(success=False, message='Tidak bisa tarik saldo wajib jika ada pinjaman aktif'), 400
        rek.saldo_wajib -= jumlah
    else:
        if rek.saldo_sukarela < jumlah:
            return jsonify(success=False, message='Saldo sukarela tidak mencukupi'), 400
        rek.saldo_sukarela -= jumlah

    try:
        tgl = datetime.strptime(tanggal_str, '%Y-%m-%d').date() if tanggal_str else date.today()
    except ValueError:
        tgl = date.today()

    no_bukti = f"TAB/{tgl.year}/{tgl.month:02d}/{TransaksiTabungan.query.filter(TransaksiTabungan.tanggal == tgl).count() + 1:04d}"

    transaksi = TransaksiTabungan(
        rekening_id=rek.id,
        tanggal=tgl,
        jenis='tarik',
        kategori=kategori,
        jumlah=jumlah,
        keterangan=keterangan or f'Penarikan {kategori}',
        no_bukti=no_bukti,
        created_by=user.id,
    )
    db.session.add(transaksi)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal menarik tabungan')
        return jsonify(success=False, message=f'Gagal menarik: {str(e)}'), 500

    return jsonify(success=True, message=f'Penarikan {kategori} berhasil', data={
        'id': transaksi.id,
        'no_bukti': no_bukti,
        'saldo_pokok': rek.saldo_pokok,
        'saldo_wajib': rek.saldo_wajib,
        'saldo_sukarela': rek.saldo_sukarela,
    }), 201
