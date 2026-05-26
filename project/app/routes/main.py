from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session, jsonify
from flask_login import login_required, current_user
from ..models import Nasabah, Pinjaman, Pembayaran, Pengaturan, Pengumuman, db, AjuanDokumen
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()

    # Get available years from both Pembayaran (payments) and Pinjaman (loans) tables
    tahun_pembayaran = [int(r[0]) for r in db.session.query(
        func.extract('year', Pembayaran.tanggal_bayar).label('tahun')
    ).filter(Pembayaran.tanggal_bayar.isnot(None)).distinct().all()]
    
    tahun_pinjaman = [int(r[0]) for r in db.session.query(
        func.extract('year', Pinjaman.tanggal_cair).label('tahun')
    ).filter(Pinjaman.tanggal_cair.isnot(None)).distinct().all()]
    
    # Combine and remove duplicates, sort descending
    available_tahun = sorted(set(tahun_pembayaran + tahun_pinjaman), reverse=True)
    
    if not available_tahun:
        available_tahun = [today.year, today.year - 1, today.year - 2]
    
    q_nasabah = Nasabah.query
    q_pinjaman = Pinjaman.query
    q_pembayaran = Pembayaran.query

    if current_user.is_kader():
        q_nasabah = q_nasabah.filter_by(kode_desa=current_user.kode_desa)
        q_pinjaman = q_pinjaman.join(Nasabah).filter(Nasabah.kode_desa == current_user.kode_desa)
        q_pembayaran = q_pembayaran.join(Pinjaman).join(Nasabah).filter(Nasabah.kode_desa == current_user.kode_desa)
    elif current_user.is_nasabah():
        q_nasabah = q_nasabah.filter_by(id=current_user.nasabah_id_fk)
        q_pinjaman = q_pinjaman.filter_by(nasabah_id_fk=current_user.nasabah_id_fk)
        q_pembayaran = q_pembayaran.join(Pinjaman).filter(Pinjaman.nasabah_id_fk == current_user.nasabah_id_fk)

    total_nasabah      = q_nasabah.count()
    nasabah_kelompok   = q_nasabah.filter_by(jenis='kelompok').count()
    nasabah_perorangan = q_nasabah.filter_by(jenis='perorangan').count()

    total_pinjaman_aktif = q_pinjaman.filter_by(status='cair').count()
    pinjaman_aktif    = q_pinjaman.filter_by(status='cair').all()
    pinjaman_all      = q_pinjaman.filter(Pinjaman.status.in_(['cair', 'lunas'])).all()
    total_outstanding = sum(p.get_saldo_pokok() for p in pinjaman_all)

    # Pinjaman Active by Jenis
    pinjaman_kelompok_active = 0
    pinjaman_perorangan_active = 0
    for p in pinjaman_aktif:
        if p.nasabah.jenis == 'kelompok':
            pinjaman_kelompok_active += 1
        else:
            pinjaman_perorangan_active += 1

    pending_pengajuan = q_pinjaman.filter(
        Pinjaman.status.in_(['pengajuan', 'cek_dokumen', 'verifikasi', 'acc_direktur'])
    ).count()

    # ── Filter Pembayaran ──────────────────────────────────────────────────
    tahun = request.args.get('tahun', str(today.year))
    bulan = request.args.get('bulan', '')

    q_pembayaran_base = q_pembayaran

    if tahun:
        q_pembayaran = q_pembayaran.filter(
            db.extract('year', Pembayaran.tanggal_bayar) == int(tahun))
    if bulan:
        q_pembayaran = q_pembayaran.filter(
            db.extract('month', Pembayaran.tanggal_bayar) == int(bulan))

    pembayaran_terfilter = q_pembayaran.all()
    total_bayar_pokok = sum(p.bayar_pokok for p in pembayaran_terfilter)
    total_bayar_jasa  = sum(p.bayar_jasa  for p in pembayaran_terfilter)
    total_bayar       = total_bayar_pokok + total_bayar_jasa
    
    # Get available months for selected year from both tables
    available_bulan = []
    if tahun:
        bulan_pembayaran = [int(r[0]) for r in db.session.query(
            func.extract('month', Pembayaran.tanggal_bayar).label('bulan')
        ).filter(
            Pembayaran.tanggal_bayar.isnot(None),
            func.extract('year', Pembayaran.tanggal_bayar) == int(tahun)
        ).distinct().all()]
        
        bulan_pinjaman = [int(r[0]) for r in db.session.query(
            func.extract('month', Pinjaman.tanggal_cair).label('bulan')
        ).filter(
            Pinjaman.tanggal_cair.isnot(None),
            func.extract('year', Pinjaman.tanggal_cair) == int(tahun)
        ).distinct().all()]
        
        available_bulan = sorted(set(bulan_pembayaran + bulan_pinjaman))
    
    if not available_bulan:
        available_bulan = list(range(1, 13))

    # ── Total Penyaluran (filtered by tahun/bulan) ─────────────────────────
    penyaluran_q = q_pinjaman.filter(Pinjaman.status.in_(['cair', 'lunas']))
    if tahun:
        penyaluran_q = penyaluran_q.filter(
            db.extract('year', Pinjaman.tanggal_cair) == int(tahun))
    if bulan:
        penyaluran_q = penyaluran_q.filter(
            db.extract('month', Pinjaman.tanggal_cair) == int(bulan))
    total_penyaluran = sum(p.jumlah_pinjaman for p in penyaluran_q.all())

    # ── Chart Data: Pemasukan per Bulan ────────────────────────────────────
    chart_pemasukan  = []
    chart_penyaluran = []
    if tahun:
        # Gunakan query terpisah khusus chart (filter tahun saja, abaikan filter bulan dari atas)
        q_pembayaran_chart = q_pembayaran_base.filter(db.extract('year', Pembayaran.tanggal_bayar) == int(tahun))
        q_pinjaman_chart = q_pinjaman.filter(
            Pinjaman.status.in_(['cair', 'lunas']),
            db.extract('year', Pinjaman.tanggal_cair) == int(tahun)
        )

        for m in range(1, 13):
            pb = q_pembayaran_chart.filter(
                db.extract('month', Pembayaran.tanggal_bayar) == m
            ).all()
            b_pokok = sum(p.bayar_pokok for p in pb)
            b_jasa  = sum(p.bayar_jasa  for p in pb)
            chart_pemasukan.append({'bulan': m, 'pokok': b_pokok, 'jasa': b_jasa})

            pj = q_pinjaman_chart.filter(
                db.extract('month', Pinjaman.tanggal_cair) == m
            ).all()
            chart_penyaluran.append({'bulan': m, 'penyaluran': sum(p.jumlah_pinjaman for p in pj)})

    # ── RKP Targets untuk Chart (target garis) ─────────────────────────────
    rkp_target_pendapatan = []
    rkp_target_penyaluran = []
    if tahun:
        for m in range(1, 13):
            try:
                rp = int(Pengaturan.get(f'rkp_{tahun}_m{m:02d}_pendapatan', '0') or 0)
            except (ValueError, TypeError):
                rp = 0
            try:
                rs = int(Pengaturan.get(f'rkp_{tahun}_m{m:02d}_penyaluran', '0') or 0)
            except (ValueError, TypeError):
                rs = 0
            rkp_target_pendapatan.append(rp)
            rkp_target_penyaluran.append(rs)

    # ── Kolektibilitas ─────────────────────────────────────────────────────
    kolek_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    nunggak_count = 0
    for p in pinjaman_aktif:
        _, _, bn = p.get_tunggakan()
        k_val, _ = p.get_kolektibilitas()
        kolek_dist[k_val] += 1
        if bn > 0:
            nunggak_count += 1

    # ── Rekap per Desa ─────────────────────────────────────────────────────
    rekap_desa = {}
    for n in q_nasabah.all():
        desa = n.nama_desa
        if desa not in rekap_desa:
            rekap_desa[desa] = {
                'jumlah_nasabah': 0, 'perorangan': 0,
                'kelompok': 0, 'saldo_pinjaman': 0
            }
        rekap_desa[desa]['jumlah_nasabah'] += 1
        if n.jenis == 'kelompok':
            rekap_desa[desa]['kelompok'] += 1
        else:
            rekap_desa[desa]['perorangan'] += 1

    for p in pinjaman_aktif:
        desa = p.nasabah.nama_desa
        if desa in rekap_desa:
            rekap_desa[desa]['saldo_pinjaman'] += p.get_saldo_pokok()

    rekap_desa_sorted = sorted(
        [{'desa': k, **v} for k, v in rekap_desa.items()],
        key=lambda x: x['saldo_pinjaman'], reverse=True
    )

    rekening = None
    has_active_loan = False
    pengumuman_aktif = []
    ajuan_disetujui = []
    if current_user.is_nasabah():
        rekening = current_user.nasabah.rekening if current_user.nasabah else None
        has_active_loan = Pinjaman.query.filter_by(nasabah_id_fk=current_user.nasabah_id_fk, status='cair').first() is not None
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        pengumuman_aktif = Pengumuman.query.filter(
            Pengumuman.aktif == True,
            db.or_(
                Pengumuman.target == 'semua',
                Pengumuman.nasabah_id_fk == current_user.nasabah_id_fk
            ),
            db.or_(
                Pengumuman.expires_at == None,
                Pengumuman.expires_at > now
            )
        ).order_by(Pengumuman.created_at.desc()).limit(5).all()
        ajuan_disetujui = AjuanDokumen.query.filter_by(
            nasabah_id=current_user.nasabah.id,
            status='disetujui'
        ).all()

    return render_template('main/dashboard.html',
        today=today,
        tahun_pilih=tahun,
        bulan_pilih=bulan,
        available_tahun=available_tahun,
        available_bulan=available_bulan,
        total_nasabah=total_nasabah,
        nasabah_kelompok=nasabah_kelompok,
        nasabah_perorangan=nasabah_perorangan,
        total_pinjaman_aktif=total_pinjaman_aktif,
        pinjaman_kelompok_active=pinjaman_kelompok_active,
        pinjaman_perorangan_active=pinjaman_perorangan_active,
        total_outstanding=total_outstanding,
        pending_pengajuan=pending_pengajuan,
        total_bayar_pokok=total_bayar_pokok,
        total_bayar_jasa=total_bayar_jasa,
        total_bayar=total_bayar,
        total_penyaluran=total_penyaluran,
        total_nunggak=nunggak_count,
        kolek_dist=kolek_dist,
        chart_pemasukan=chart_pemasukan,
        chart_penyaluran=chart_penyaluran,
        rkp_target_pendapatan=rkp_target_pendapatan,
        rkp_target_penyaluran=rkp_target_penyaluran,
        rekap_desa=rekap_desa_sorted,
        rekening=rekening,
        has_active_loan=has_active_loan,
        pengumuman_aktif=pengumuman_aktif,
        ajuan_disetujui=ajuan_disetujui
    )


@main_bp.route('/profil', methods=['GET', 'POST'])
@login_required
def profil_nasabah():
    if not current_user.is_nasabah():
        return redirect(url_for('main.dashboard'))
    
    nasabah = current_user.nasabah
    if not nasabah:
        return "Data nasabah tidak ditemukan.", 404
    
    approved_docs = set()
    pending_ajuan = AjuanDokumen.query.filter_by(
        nasabah_id=nasabah.id, 
        status='disetujui'
    ).all()
    for ajuan in pending_ajuan:
        approved_docs.add(ajuan.dokumen)
    
    if request.method == 'POST':
        prefix = nasabah.nasabah_id.replace('-', '')
        from ..utils.helpers import save_file
        
        uploaded = False
        for field, subfolder, force_portrait in [
            ('foto','foto', True),('ktp','ktp', False),('kk','kk', False),
            ('surat_usaha','sku', False),('bukti_penghasilan','penghasilan', False),
            ('jaminan','jaminan', False)
        ]:
            if field not in approved_docs:
                continue
            
            file = request.files.get(field)
            if file and file.filename:
                new_f = save_file(file, subfolder, prefix, force_portrait=force_portrait)
                if new_f:
                    setattr(nasabah, field, new_f)
                    uploaded = True
        
        if uploaded:
            db.session.commit()
            for field in approved_docs:
                AjuanDokumen.query.filter_by(
                    nasabah_id=nasabah.id,
                    dokumen=field,
                    status='disetujui'
                ).delete()
            db.session.commit()
            flash('Dokumen berhasil diperbarui.', 'success')
        else:
            flash('Pilih file untuk mengunggah atau Anda belum mendapat persetujuan.', 'warning')
        return redirect(url_for('main.profil_nasabah'))
        
    return render_template('main/profil_nasabah.html', nasabah=nasabah, approved_docs=approved_docs)


@main_bp.route('/ajuan-dokumen', methods=['GET', 'POST'])
@login_required
def ajuan_dokumen():
    if not current_user.is_nasabah():
        return redirect(url_for('main.dashboard'))
    
    nasabah = current_user.nasabah
    if not nasabah:
        return "Data nasabah tidak ditemukan.", 404
    
    if request.method == 'POST':
        dokumen_fields = {
            'foto': 'Pas Photo',
            'ktp': 'KTP',
            'kk': 'Kartu Keluarga',
            'surat_usaha': 'Surat Usaha',
            'bukti_penghasilan': 'Bukti Penghasilan',
            'jaminan': 'Jaminan'
        }
        
        diajukan = []
        for field, label in dokumen_fields.items():
            if request.form.get(field) == 'on':
                existing_ajuan = AjuanDokumen.query.filter_by(
                    nasabah_id=nasabah.id,
                    dokumen=field,
                    status='menunggu'
                ).first()
                
                if not existing_ajuan:
                    ajuan_baru = AjuanDokumen(
                        nasabah_id=nasabah.id,
                        dokumen=field,
                        alasan=request.form.get(f'alasan_{field}', '')
                    )
                    db.session.add(ajuan_baru)
                    diajukan.append(label)
        
        if diajukan:
            db.session.commit()
            flash(f'Pengajuan perubahan dokumen untuk: {", ".join(diajukan)}. Menunggu persetujuan admin.', 'success')
        else:
            flash('Tidak ada dokumen yang diajukan atau sudah ada pengajuan yang menunggu.', 'warning')
        
        return redirect(url_for('main.profil_nasabah'))
    
    pending_ajuan = AjuanDokumen.query.filter_by(
        nasabah_id=nasabah.id,
        status='menunggu'
    ).all()
    
    pending_docs = {a.dokumen for a in pending_ajuan}
    
    return render_template('main/ajuan_dokumen.html', nasabah=nasabah, pending_docs=pending_docs)


@main_bp.route('/admin/ajuan-dokumen')
@login_required
def admin_ajuan_dokumen():
    if not current_user.can_edit_delete():
        abort(403)
    
    status_filter = request.args.get('status', 'menunggu')
    query = AjuanDokumen.query
    
    if status_filter != 'semua':
        query = query.filter_by(status=status_filter)
    
    all_ajuan = query.order_by(AjuanDokumen.tanggal_ajuan.desc()).all()
    
    return render_template('main/admin_ajuan_dokumen_list.html', 
                          all_ajuan=all_ajuan, 
                          status_filter=status_filter)


@main_bp.route('/admin/ajuan-dokumen/<int:ajuan_id>/proses', methods=['POST'])
@login_required
def admin_proses_ajuan_dokumen(ajuan_id):
    if not current_user.can_edit_delete():
        abort(403)
    
    from datetime import datetime
    
    ajuan = AjuanDokumen.query.get_or_404(ajuan_id)
    action = request.form.get('action')
    catatan = request.form.get('catatan', '')
    
    if action == 'setujui':
        ajuan.status = 'disetujui'
        ajuan.tanggal_respon = datetime.utcnow()
        ajuan.admin_id = current_user.id
        ajuan.catatan_admin = catatan
        flash(f'Pengajuan dokumen untuk {ajuan.nasabah.nama} telah disetujui.', 'success')
    elif action == 'tolak':
        ajuan.status = 'ditolak'
        ajuan.tanggal_respon = datetime.utcnow()
        ajuan.admin_id = current_user.id
        ajuan.catatan_admin = catatan
        flash(f'Pengajuan dokumen untuk {ajuan.nasabah.nama} telah ditolak.', 'warning')
    
    db.session.commit()
    return redirect(url_for('main.admin_ajuan_dokumen', status=request.args.get('status', 'menunggu')))


@main_bp.route('/notif/clear', methods=['POST'])
@login_required
def clear_notifications():
    """Menandai semua notifikasi sudah dibaca dengan menyimpan timestamp di session."""
    session['notif_cleared_at'] = datetime.utcnow().isoformat()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Notifikasi telah ditandai sudah dibaca'})
    
    flash('Semua notifikasi telah ditandai sudah dibaca.', 'success')
    return redirect(request.referrer or url_for('main.dashboard'))
