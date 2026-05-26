from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from ..models import db, BonusPetugas, User, Pembayaran, Pinjaman, Nasabah
from datetime import date, datetime, timedelta

bonus_bp = Blueprint('bonus', __name__)


@bonus_bp.route('/')
@login_required
def index():
    if not current_user.is_admin():
        abort(403)

    tgl_dari_str = request.args.get('dari', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    tgl_sampai_str = request.args.get('sampai', date.today().strftime('%Y-%m-%d'))
    status_filter = request.args.get('status', '')
    petugas_id = request.args.get('petugas_id')

    try:
        d_dari = datetime.strptime(tgl_dari_str, '%Y-%m-%d').date()
        d_sampai = datetime.strptime(tgl_sampai_str, '%Y-%m-%d').date()
    except:
        d_dari = date.today() - timedelta(days=30)
        d_sampai = date.today()

    qr = BonusPetugas.query.join(User, BonusPetugas.petugas_id == User.id).filter(
        BonusPetugas.tanggal_hitung >= d_dari,
        BonusPetugas.tanggal_hitung <= d_sampai + timedelta(days=1),
    )

    if status_filter:
        qr = qr.filter(BonusPetugas.status == status_filter)
    if petugas_id:
        qr = qr.filter(BonusPetugas.petugas_id == int(petugas_id))

    qr = qr.order_by(BonusPetugas.tanggal_hitung.desc())
    bonus_list = qr.all()

    rekap_by_petugas = {}
    for b in bonus_list:
        pid = b.petugas_id
        if pid not in rekap_by_petugas:
            rekap_by_petugas[pid] = {
                'nama': b.petugas.nama_lengkap,
                'total_bonus': 0,
                'total_bayar': 0,
                'jumlah': 0,
            }
        rekap_by_petugas[pid]['total_bonus'] += b.jumlah_bonus
        rekap_by_petugas[pid]['total_bayar'] += b.jumlah_bayar
        rekap_by_petugas[pid]['jumlah'] += 1

    petugas_list = User.query.filter(
        User.role.in_(['kredit', 'kasir', 'penagih', 'kader_desa', 'staf']),
        User.aktif == True
    ).order_by(User.nama_lengkap).all()

    total_bonus = sum(b.jumlah_bonus for b in bonus_list)
    total_bayar = sum(b.jumlah_bayar for b in bonus_list)

    return render_template('bonus/index.html',
        bonus_list=bonus_list,
        rekap_by_petugas=rekap_by_petugas,
        petugas_list=petugas_list,
        total_bonus=total_bonus,
        total_bayar=total_bayar,
        tgl_dari=d_dari,
        tgl_sampai=d_sampai,
        status_filter=status_filter,
        petugas_id=petugas_id,
    )


@bonus_bp.route('/saya')
@login_required
def saya():
    bonus_list = BonusPetugas.query.filter(
        BonusPetugas.petugas_id == current_user.id
    ).order_by(BonusPetugas.tanggal_hitung.desc()).all()

    total_bonus = sum(b.jumlah_bonus for b in bonus_list)
    total_bayar = sum(b.jumlah_bayar for b in bonus_list)
    belum_klaim = sum(b.jumlah_bonus for b in bonus_list if b.status == 'belum_diklaim')
    menunggu = sum(b.jumlah_bonus for b in bonus_list if b.status == 'menunggu_klaim')
    diklaim = sum(b.jumlah_bonus for b in bonus_list if b.status == 'diklaim')

    return render_template('bonus/saya.html',
        bonus_list=bonus_list,
        total_bonus=total_bonus,
        total_bayar=total_bayar,
        belum_klaim=belum_klaim,
        menunggu=menunggu,
        diklaim=diklaim,
    )


@bonus_bp.route('/ajukan', methods=['POST'])
@login_required
def ajukan():
    bonus_ids = request.form.getlist('bonus_ids')
    if not bonus_ids:
        flash('Pilih bonus yang akan diajukan', 'warning')
        return redirect(url_for('bonus.saya'))

    count = 0
    for bid in bonus_ids:
        bp = BonusPetugas.query.get(bid)
        if bp and bp.petugas_id == current_user.id and bp.status == 'belum_diklaim':
            bp.status = 'menunggu_klaim'
            count += 1

    db.session.commit()
    flash(f'{count} bonus diajukan untuk diklaim', 'success')
    return redirect(url_for('bonus.saya'))


@bonus_bp.route('/detail/<int:petugas_id>')
@login_required
def detail(petugas_id):
    if not current_user.is_admin():
        abort(403)

    tgl_dari_str = request.args.get('dari', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    tgl_sampai_str = request.args.get('sampai', date.today().strftime('%Y-%m-%d'))

    try:
        d_dari = datetime.strptime(tgl_dari_str, '%Y-%m-%d').date()
        d_sampai = datetime.strptime(tgl_sampai_str, '%Y-%m-%d').date()
    except:
        d_dari = date.today() - timedelta(days=30)
        d_sampai = date.today()

    bonus_list = BonusPetugas.query.filter(
        BonusPetugas.petugas_id == petugas_id,
        BonusPetugas.tanggal_hitung >= d_dari,
        BonusPetugas.tanggal_hitung <= d_sampai + timedelta(days=1),
    ).order_by(BonusPetugas.tanggal_hitung.desc()).all()

    petugas = User.query.get_or_404(petugas_id)
    total_bonus = sum(b.jumlah_bonus for b in bonus_list)
    total_bayar = sum(b.jumlah_bayar for b in bonus_list)

    return render_template('bonus/detail.html',
        bonus_list=bonus_list,
        petugas=petugas,
        total_bonus=total_bonus,
        total_bayar=total_bayar,
        tgl_dari=d_dari,
        tgl_sampai=d_sampai,
    )


@bonus_bp.route('/setuju-klaim', methods=['POST'])
@login_required
def setuju_klaim():
    if not current_user.is_admin():
        abort(403)

    bonus_ids = request.form.getlist('bonus_ids')
    if not bonus_ids:
        flash('Pilih bonus yang akan disetujui', 'warning')
        return redirect(url_for('bonus.index'))

    count = 0
    for bid in bonus_ids:
        bp = BonusPetugas.query.get(bid)
        if bp and bp.status == 'menunggu_klaim':
            bp.status = 'diklaim'
            bp.tanggal_klaim = datetime.now()
            bp.diklaim_oleh = current_user.id
            count += 1

    db.session.commit()
    flash(f'{count} bonus disetujui dan diklaim', 'success')
    return redirect(url_for('bonus.index'))


@bonus_bp.route('/tolak-klaim/<int:bonus_id>', methods=['POST'])
@login_required
def tolak_klaim(bonus_id):
    if not current_user.is_admin():
        abort(403)

    bp = BonusPetugas.query.get_or_404(bonus_id)
    if bp.status != 'menunggu_klaim':
        flash('Bonus tidak dalam status menunggu klaim', 'warning')
        return redirect(url_for('bonus.index'))

    bp.status = 'belum_diklaim'
    db.session.commit()
    flash('Klaim ditolak', 'success')
    return redirect(url_for('bonus.index'))


@bonus_bp.route('/batal/<int:bonus_id>', methods=['POST'])
@login_required
def batal(bonus_id):
    if not current_user.is_admin():
        abort(403)

    bp = BonusPetugas.query.get_or_404(bonus_id)
    if bp.status not in ['diklaim', 'menunggu_klaim']:
        flash('Bonus tidak bisa dibatalkan', 'warning')
        return redirect(url_for('bonus.saya'))

    bp.status = 'belum_diklaim'
    bp.tanggal_klaim = None
    bp.diklaim_oleh = None
    db.session.commit()
    flash('Bonus dibatalkan', 'success')
    if current_user.can_write_pembayaran():
        return redirect(url_for('bonus.index'))
    return redirect(url_for('bonus.saya'))


@bonus_bp.route('/api/count')
@login_required
def api_count():
    if current_user.is_admin():
        count = BonusPetugas.query.filter(BonusPetugas.status.in_(['belum_diklaim', 'menunggu_klaim'])).count()
    else:
        count = BonusPetugas.query.filter_by(
            petugas_id=current_user.id,
            status='belum_diklaim'
        ).count()
    return jsonify({'count': count})


@bonus_bp.route('/cetak-persetujuan/<int:petugas_id>')
@login_required
def cetak_persetujuan(petugas_id):
    if not current_user.is_admin() and current_user.id != petugas_id:
        abort(403)

    tgl_dari_str = request.args.get('dari', date.today().strftime('%Y-%m-%d'))
    tgl_sampai_str = request.args.get('sampai', date.today().strftime('%Y-%m-%d'))

    try:
        d_dari = datetime.strptime(tgl_dari_str, '%Y-%m-%d').date()
        d_sampai = datetime.strptime(tgl_sampai_str, '%Y-%m-%d').date()
    except:
        d_dari = date.today()
        d_sampai = date.today()

    bonus_list = BonusPetugas.query.filter(
        BonusPetugas.petugas_id == petugas_id,
        BonusPetugas.status == 'diklaim',
        BonusPetugas.tanggal_klaim >= d_dari,
        BonusPetugas.tanggal_klaim <= d_sampai + timedelta(days=1),
    ).order_by(BonusPetugas.tanggal_klaim.asc()).all()

    if not bonus_list:
        flash('Tidak ada bonus yang disetujui dalam periode klaim tersebut.', 'warning')
        if current_user.can_write_pembayaran():
            return redirect(url_for('bonus.detail', petugas_id=petugas_id))
        return redirect(url_for('bonus.saya'))

    petugas = User.query.get_or_404(petugas_id)
    total_bonus = sum(b.jumlah_bonus for b in bonus_list)

    return render_template('bonus/cetak_persetujuan.html',
        bonus_list=bonus_list,
        petugas=petugas,
        total_bonus=total_bonus,
        tgl_dari=d_dari,
        tgl_sampai=d_sampai,
    )