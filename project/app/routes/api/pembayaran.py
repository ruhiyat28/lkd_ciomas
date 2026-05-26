from flask import request, jsonify
from flask_jwt_extended import jwt_required
from ...models import db, Pinjaman, Pembayaran, Nasabah, User, BonusPetugas
from ...utils.auto_jurnal import jurnal_pembayaran
from . import api_bp, get_current_user
from datetime import date, datetime, timezone
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/pinjaman/<int:id>/angsuran', methods=['GET'])
@jwt_required()
def jadwal_angsuran(id):
    user = get_current_user()
    p = db.session.get(Pinjaman, id)
    if not p:
        return jsonify(success=False, message='Pinjaman tidak ditemukan'), 404

    if user.is_nasabah() and p.nasabah_id_fk != user.nasabah_id_fk:
        return jsonify(success=False, message='Forbidden'), 403
    if user.is_kader() and p.nasabah.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    jadwal = p.get_jadwal_angsuran()
    total_pokok, total_jasa = p.get_realisasi_pembayaran()

    return jsonify(success=True, data={
        'pinjaman_id': p.id,
        'spk': p.spk,
        'jumlah_pinjaman': p.jumlah_pinjaman,
        'saldo_pokok': p.get_saldo_pokok(),
        'angsuran_pokok': p.angsuran_pokok,
        'angsuran_jasa': p.angsuran_jasa,
        'angsuran_total': p.angsuran_total,
        'pokok_terbayar': total_pokok,
        'jasa_terbayar': total_jasa,
        'jadwal': [{
            'ke': j['ke'],
            'tanggal': str(j['tanggal']),
            'pokok': j['pokok'],
            'jasa': j['jasa'],
            'total': j['total'],
            'lunas': j['lunas'],
            'terlambat': j['terlambat'],
        } for j in jadwal],
    })


@api_bp.route('/pembayaran', methods=['GET'])
@jwt_required()
def list_pembayaran():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pinjaman_id = request.args.get('pinjaman_id', type=int)
    status_acc = request.args.get('status_acc', '').strip()

    q = Pembayaran.query

    if user.is_kader():
        q = q.join(Pinjaman).join(Nasabah).filter(Nasabah.kode_desa == user.kode_desa)
    elif user.is_nasabah():
        q = q.join(Pinjaman).filter(Pinjaman.nasabah_id_fk == user.nasabah_id_fk)

    if pinjaman_id:
        q = q.filter_by(pinjaman_id=pinjaman_id)

    if status_acc:
        q = q.filter_by(status_acc=status_acc)

    q = q.order_by(Pembayaran.tanggal_bayar.desc(), Pembayaran.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    result = []
    for b in pagination.items:
        result.append({
            'id': b.id,
            'no_kuitansi': b.no_kuitansi,
            'pinjaman_id': b.pinjaman_id,
            'spk': b.pinjaman.spk if b.pinjaman else '',
            'nasabah': b.pinjaman.nasabah.nama if b.pinjaman and b.pinjaman.nasabah else '',
            'tanggal_bayar': str(b.tanggal_bayar),
            'jumlah_bayar': b.jumlah_bayar,
            'bayar_pokok': b.bayar_pokok,
            'bayar_jasa': b.bayar_jasa,
            'angsuran_ke': b.angsuran_ke,
            'keterangan': b.keterangan or '',
            'status_acc': b.status_acc or '',
            'created_at': str(b.created_at) if b.created_at else '',
        })

    return jsonify(success=True, data=result, pagination={
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    })


@api_bp.route('/pembayaran', methods=['POST'])
@jwt_required()
def create_pembayaran():
    user = get_current_user()
    if not user.can_write_pembayaran():
        return jsonify(success=False, message='Forbidden'), 403

    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    try:
        pinjaman_id = int(data['pinjaman_id']) if data.get('pinjaman_id') is not None else None
    except (ValueError, TypeError):
        pinjaman_id = None
    try:
        jumlah_bayar = int(data.get('jumlah_bayar', 0))
    except (ValueError, TypeError):
        jumlah_bayar = 0
    tanggal_bayar_str = data.get('tanggal_bayar', '')
    keterangan = data.get('keterangan', '')

    if not pinjaman_id or jumlah_bayar <= 0:
        return jsonify(success=False, message='pinjaman_id dan jumlah_bayar wajib diisi'), 400

    p = db.session.get(Pinjaman, pinjaman_id)
    if not p:
        return jsonify(success=False, message='Pinjaman tidak ditemukan'), 404
    if p.status != 'cair':
        return jsonify(success=False, message='Pinjaman tidak aktif'), 400

    if user.is_kader() and p.nasabah.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    try:
        tgl_bayar = datetime.strptime(tanggal_bayar_str, '%Y-%m-%d').date() if tanggal_bayar_str else date.today()
    except ValueError:
        tgl_bayar = date.today()

    sisa_pokok = p.get_saldo_pokok()
    bayar_pokok = min(jumlah_bayar, sisa_pokok)
    bayar_jasa = jumlah_bayar - bayar_pokok

    jadwal = p.get_jadwal_angsuran()
    angsuran_ke = None
    for j in jadwal:
        if not j['lunas']:
            angsuran_ke = j['ke']
            break

    no_kuitansi = f"KWT-{tgl_bayar.strftime('%Y%m%d')}-{_get_pembayaran_count(tgl_bayar) + 1:04d}"

    pembayaran = Pembayaran(
        no_kuitansi=no_kuitansi,
        pinjaman_id=p.id,
        tanggal_bayar=tgl_bayar,
        jumlah_bayar=jumlah_bayar,
        bayar_pokok=bayar_pokok,
        bayar_jasa=bayar_jasa,
        angsuran_ke=angsuran_ke,
        keterangan=keterangan,
        created_by=user.id,
        status_acc='menunggu' if user.is_kader() else None,
    )

    db.session.add(pembayaran)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal menyimpan pembayaran')
        return jsonify(success=False, message=f'Gagal menyimpan pembayaran: {str(e)}'), 500

    total_pokok, total_jasa = p.get_realisasi_pembayaran()
    if total_pokok >= p.jumlah_pinjaman:
        p.status = 'lunas'
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.exception('Gagal update status lunas')

    return jsonify(success=True, message='Pembayaran berhasil dicatat', data={
        'id': pembayaran.id,
        'no_kuitansi': pembayaran.no_kuitansi,
    }), 201


def _get_pembayaran_count(tgl):
    return Pembayaran.query.filter_by(tanggal_bayar=tgl).count()


@api_bp.route('/pembayaran/<int:id>/acc', methods=['POST'])
@jwt_required()
def acc_pembayaran(id):
    user = get_current_user()
    if not user.is_admin() and not user.is_manajer() and not user.is_keuangan():
        # Pembina juga bisa approve kader binaan
        pb = db.session.get(Pembayaran, id)
        if pb and pb.created_by:
            creator = db.session.get(User, pb.created_by)
            if not creator or creator.pembina_id != user.id:
                return jsonify(success=False, message='Forbidden'), 403
        else:
            return jsonify(success=False, message='Forbidden'), 403

    pb = db.session.get(Pembayaran, id)
    if not pb:
        return jsonify(success=False, message='Pembayaran tidak ditemukan'), 404

    if pb.status_acc != 'menunggu':
        return jsonify(success=False, message=f'Status ACC sudah "{pb.status_acc}"'), 400

    pb.status_acc = 'diterima'
    pb.acc_by = user.id
    pb.acc_at = datetime.now(timezone.utc)

    try:
        from ...models import User as UserModel
        creator = db.session.get(UserModel, pb.created_by) if pb.created_by else None
        if creator and (creator.is_kader() or creator.is_penagih()):
            bonus = BonusPetugas.hitung_bonus(pb, pb.created_by)
            if bonus >= 100:
                bp = BonusPetugas(
                    petugas_id=pb.created_by,
                    pembayaran_id=pb.id,
                    tahun_tunggakan=None,
                    jumlah_bayar=pb.jumlah_bayar,
                    persen_bonus=bonus,
                    jumlah_bonus=bonus,
                )
                db.session.add(bp)
                db.session.flush()
                bonus_pembina = BonusPetugas.buat_bonus_pembina(pb.id, pb.created_by, bonus)
                if bonus_pembina:
                    db.session.add(bonus_pembina)
        jurnal_pembayaran(pb)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f'Gagal ACC: {str(e)}'), 500

    return jsonify(success=True, message='Pembayaran diterima', data={
        'id': pb.id, 'status_acc': 'diterima',
    })


@api_bp.route('/pembayaran/<int:id>/tolak', methods=['POST'])
@jwt_required()
def tolak_pembayaran(id):
    user = get_current_user()
    if not user.is_admin() and not user.is_manajer() and not user.is_keuangan():
        pb = db.session.get(Pembayaran, id)
        if pb and pb.created_by:
            creator = db.session.get(User, pb.created_by)
            if not creator or creator.pembina_id != user.id:
                return jsonify(success=False, message='Forbidden'), 403
        else:
            return jsonify(success=False, message='Forbidden'), 403

    pb = db.session.get(Pembayaran, id)
    if not pb:
        return jsonify(success=False, message='Pembayaran tidak ditemukan'), 404

    if pb.status_acc != 'menunggu':
        return jsonify(success=False, message=f'Status ACC sudah "{pb.status_acc}"'), 400

    pb.status_acc = 'ditolak'
    pb.acc_by = user.id
    pb.acc_at = datetime.now(timezone.utc)

    data = request.get_json() or {}
    if data.get('alasan'):
        pb.keterangan = (pb.keterangan or '') + f'\nDitolak: {data["alasan"]}'

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f'Gagal menolak: {str(e)}'), 500

    return jsonify(success=True, message='Pembayaran ditolak', data={
        'id': pb.id, 'status_acc': 'ditolak',
    })
