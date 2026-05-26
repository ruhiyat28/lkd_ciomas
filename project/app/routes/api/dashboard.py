from flask import jsonify
from flask_jwt_extended import jwt_required
from ...models import db, Nasabah, Pinjaman, Pembayaran, Pengaturan, Pengumuman
from ...models import RekeningTabungan, AjuanDokumen
from . import api_bp, get_current_user
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import func


@api_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    user = get_current_user()
    today = date.today()

    q_nasabah = Nasabah.query
    q_pinjaman = Pinjaman.query
    q_pembayaran = Pembayaran.query

    if user.is_kader():
        q_nasabah = q_nasabah.filter_by(kode_desa=user.kode_desa)
        q_pinjaman = q_pinjaman.join(Nasabah).filter(Nasabah.kode_desa == user.kode_desa)
        q_pembayaran = q_pembayaran.join(Pinjaman).join(Nasabah).filter(Nasabah.kode_desa == user.kode_desa)
    elif user.is_nasabah():
        q_nasabah = q_nasabah.filter_by(id=user.nasabah_id_fk)
        q_pinjaman = q_pinjaman.filter_by(nasabah_id_fk=user.nasabah_id_fk)
        q_pembayaran = q_pembayaran.join(Pinjaman).filter(Pinjaman.nasabah_id_fk == user.nasabah_id_fk)

    total_nasabah = q_nasabah.filter_by(status='aktif').count()
    nasabah_calon = q_nasabah.filter_by(status='calon').count()

    pinjaman_aktif_list = q_pinjaman.filter_by(status='cair').all()
    pinjaman_aktif_count = len(pinjaman_aktif_list)
    total_outstanding = sum(p.get_saldo_pokok() for p in pinjaman_aktif_list)

    pinjaman_all = q_pinjaman.filter(Pinjaman.status.in_(['cair', 'lunas'])).all()
    total_penyaluran = sum(p.jumlah_pinjaman for p in pinjaman_all)

    pending_pengajuan = q_pinjaman.filter(
        Pinjaman.status.in_(['pengajuan', 'cek_dokumen', 'verifikasi', 'acc_direktur'])
    ).count()

    pembayaran_today = q_pembayaran.filter(
        Pembayaran.tanggal_bayar == today
    ).all()
    total_bayar_today = sum(p.jumlah_bayar for p in pembayaran_today)
    bayar_today_count = len(pembayaran_today)

    nunggak_count = 0
    for p in pinjaman_aktif_list:
        _, _, bn = p.get_tunggakan()
        if bn > 0:
            nunggak_count += 1

    desa_data = {}
    for n in q_nasabah.all():
        d = n.nama_desa or n.kode_desa
        if d not in desa_data:
            desa_data[d] = {'nama': d, 'total': 0, 'outstanding': 0}
        desa_data[d]['total'] += 1
    for p in pinjaman_aktif_list:
        d = p.nasabah.nama_desa or p.nasabah.kode_desa
        if d in desa_data:
            desa_data[d]['outstanding'] += p.get_saldo_pokok()
    rekap_desa = sorted(desa_data.values(), key=lambda x: x['outstanding'], reverse=True)

    rekening = None
    has_active_loan = False
    active_pinjaman = None
    pengumuman_aktif = []
    pending_ajuan_count = 0
    if user.is_nasabah() and user.nasabah:
        n = user.nasabah
        if n.rekening:
            rekening = {
                'no_rekening': n.rekening.no_rekening,
                'saldo_pokok': n.rekening.saldo_pokok,
                'saldo_wajib': n.rekening.saldo_wajib,
                'saldo_sukarela': n.rekening.saldo_sukarela,
                'total_saldo': n.rekening.total_saldo(),
            }
        active_pinjaman = Pinjaman.query.filter_by(
            nasabah_id_fk=n.id, status='cair'
        ).first()
        has_active_loan = active_pinjaman is not None
        now = datetime.now(timezone.utc)
        pengumuman_aktif = Pengumuman.query.filter(
            Pengumuman.aktif == True,
            db.or_(
                Pengumuman.target == 'semua',
                Pengumuman.nasabah_id_fk == n.id
            ),
            db.or_(Pengumuman.expires_at == None, Pengumuman.expires_at > now)
        ).order_by(Pengumuman.created_at.desc()).limit(5).all()
        pending_ajuan_count = AjuanDokumen.query.filter_by(
            nasabah_id=n.id, status='menunggu'
        ).count()

    return jsonify(success=True, data={
        'today': str(today),
        'total_nasabah_aktif': total_nasabah,
        'nasabah_calon': nasabah_calon,
        'pinjaman_aktif': pinjaman_aktif_count,
        'total_outstanding': total_outstanding,
        'total_penyaluran': total_penyaluran,
        'pending_pengajuan': pending_pengajuan,
        'pembayaran_hari_ini': bayar_today_count,
        'total_bayar_hari_ini': total_bayar_today,
        'nasabah_nunggak': nunggak_count,
        'rekap_desa': rekap_desa,
        'rekening': rekening,
        'has_active_loan': has_active_loan,
        'active_loan_id': active_pinjaman.id if active_pinjaman else None,
        'pengumuman': [{
            'id': p.id,
            'judul': p.judul,
            'isi': p.isi,
            'tipe': p.tipe,
            'created_at': str(p.created_at) if p.created_at else '',
        } for p in pengumuman_aktif],
        'pending_ajuan_dokumen': pending_ajuan_count,
    })
