from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ..models import db, Nasabah, RekeningTabungan, TransaksiTabungan
from config import Config
from datetime import date, datetime

tabungan_bp = Blueprint('tabungan', __name__)

@tabungan_bp.before_request
def restrict_kader():
    if current_user.is_kader():
        abort(403)


def generate_no_rekening(nasabah_id_str):
    """Format: TAB-{nasabah_id}, contoh: TAB-UT-001"""
    return f"TAB-{nasabah_id_str}"


def generate_no_bukti():
    year  = date.today().strftime('%Y')
    month = date.today().strftime('%m')
    count = TransaksiTabungan.query.filter(
        TransaksiTabungan.no_bukti.like(f'TAB/{year}/{month}/%')
    ).count() + 1
    return f"TAB/{year}/{month}/{count:04d}"


def get_or_create_rekening(nasabah):
    """Buat rekening tabungan jika belum ada."""
    rek = RekeningTabungan.query.filter_by(nasabah_id=nasabah.id).first()
    if not rek:
        rek = RekeningTabungan(
            nasabah_id  = nasabah.id,
            no_rekening = generate_no_rekening(nasabah.nasabah_id),
        )
        db.session.add(rek)
        db.session.commit()
    return rek


@tabungan_bp.route('/')
@login_required
def index():
    if current_user.is_nasabah():
        if current_user.nasabah_id_fk:
            return redirect(url_for('tabungan.by_nasabah', nasabah_id=current_user.nasabah_id_fk))
        abort(403)

    desa_filter = request.args.get('desa', '')
    search      = request.args.get('q', '')
    page        = request.args.get('page', 1, type=int)

    q = RekeningTabungan.query.join(Nasabah).filter(
        (RekeningTabungan.saldo_pokok > 0) |
        (RekeningTabungan.saldo_wajib > 0) |
        (RekeningTabungan.saldo_sukarela > 0)
    )
    if desa_filter: q = q.filter(Nasabah.kode_desa == desa_filter)
    if search:
        q = q.filter(
            Nasabah.nama.ilike(f'%{search}%') |
            Nasabah.nasabah_id.ilike(f'%{search}%') |
            RekeningTabungan.no_rekening.ilike(f'%{search}%')
        )

    # Urut dari penabung terakhir (terbaru berdasarkan transaksi)
    from ..models import TransaksiTabungan
    from sqlalchemy import func
    subq = db.session.query(
        TransaksiTabungan.rekening_id,
        func.max(TransaksiTabungan.tanggal).label('last_trx')
    ).group_by(TransaksiTabungan.rekening_id).subquery()
    q = q.outerjoin(subq, RekeningTabungan.id == subq.c.rekening_id)
    rekening_list = q.order_by(subq.c.last_trx.desc().nullslast(), Nasabah.nasabah_id).paginate(page=page, per_page=20)
    total_pokok    = db.session.query(db.func.sum(RekeningTabungan.saldo_pokok)).scalar() or 0
    total_wajib    = db.session.query(db.func.sum(RekeningTabungan.saldo_wajib)).scalar() or 0
    total_sukarela = db.session.query(db.func.sum(RekeningTabungan.saldo_sukarela)).scalar() or 0

    return render_template('tabungan/index.html',
        rekening_list=rekening_list, desa_filter=desa_filter, search=search,
        desa_list=Config.DESA_LIST,
        total_pokok=total_pokok, total_wajib=total_wajib, total_sukarela=total_sukarela)


@tabungan_bp.route('/detail/<int:id>')
@login_required
def detail(id):
    rek = RekeningTabungan.query.get_or_404(id)
    if current_user.is_nasabah() and rek.nasabah_id != current_user.nasabah_id_fk:
        abort(403)
    transaksi_list = TransaksiTabungan.query.filter_by(
        rekening_id=id
    ).order_by(TransaksiTabungan.tanggal.desc(), TransaksiTabungan.id.desc()).all()
    return render_template('tabungan/detail.html', rek=rek, transaksi_list=transaksi_list)


@tabungan_bp.route('/setor/<int:id>', methods=['GET','POST'])
@login_required
def setor(id):
    if not current_user.can_write_pembayaran(): abort(403)
    rek = RekeningTabungan.query.get_or_404(id)

    if request.method == 'POST':
        kategori = request.form.get('kategori', 'sukarela')
        jumlah   = int(''.join(c for c in request.form.get('jumlah','0') if c.isdigit()) or '0')
        if jumlah <= 0:
            flash('Jumlah tidak valid.', 'danger')
            return redirect(url_for('tabungan.detail', id=id))

        no_bukti = generate_no_bukti()
        try:
            tgl = datetime.strptime(request.form.get('tanggal',''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            tgl = date.today()

        # Tambah saldo
        setattr(rek, f'saldo_{kategori}',
                getattr(rek, f'saldo_{kategori}') + jumlah)

        tr = TransaksiTabungan(
            rekening_id = id,
            tanggal     = tgl,
            jenis       = 'setor',
            kategori    = kategori,
            jumlah      = jumlah,
            keterangan  = request.form.get('keterangan','Setoran tabungan'),
            no_bukti    = no_bukti,
            created_by  = current_user.id,
        )
        db.session.add(tr)
        db.session.commit()

        flash(f'Setoran Rp {jumlah:,} ({kategori}) berhasil. Bukti: {no_bukti}', 'success')
        return redirect(url_for('tabungan.detail', id=id))

    return render_template('tabungan/setor.html', rek=rek, today_str=date.today().strftime('%Y-%m-%d'))


@tabungan_bp.route('/tarik/<int:id>', methods=['GET','POST'])
@login_required
def tarik(id):
    if not current_user.can_write_pembayaran(): abort(403)
    rek = RekeningTabungan.query.get_or_404(id)

    if request.method == 'POST':
        kategori = request.form.get('kategori', 'sukarela')
        jumlah   = int(''.join(c for c in request.form.get('jumlah','0') if c.isdigit()) or '0')

        if jumlah <= 0:
            flash('Jumlah tidak valid.', 'danger')
            return redirect(url_for('tabungan.tarik', id=id))

        # Validasi: pokok & wajib tidak bisa ditarik jika ada pinjaman aktif
        if kategori in ['pokok', 'wajib'] and rek.punya_pinjaman_aktif():
            flash(
                f'Tabungan {kategori} tidak bisa ditarik selama ada pinjaman aktif. '
                'Penarikan hanya bisa dilakukan setelah semua pinjaman lunas, '
                'kecuali untuk tambahan pembayaran angsuran (gunakan fitur di menu Pembayaran).',
                'danger'
            )
            return redirect(url_for('tabungan.tarik', id=id))

        saldo_sekarang = getattr(rek, f'saldo_{kategori}')
        if jumlah > saldo_sekarang:
            flash(f'Saldo {kategori} tidak cukup. Saldo: Rp {saldo_sekarang:,}', 'danger')
            return redirect(url_for('tabungan.tarik', id=id))

        no_bukti = generate_no_bukti()
        try:
            tgl = datetime.strptime(request.form.get('tanggal',''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            tgl = date.today()

        setattr(rek, f'saldo_{kategori}', saldo_sekarang - jumlah)
        tr = TransaksiTabungan(
            rekening_id = id,
            tanggal     = tgl,
            jenis       = 'tarik',
            kategori    = kategori,
            jumlah      = jumlah,
            keterangan  = request.form.get('keterangan', 'Penarikan tabungan'),
            no_bukti    = no_bukti,
            created_by  = current_user.id,
        )
        db.session.add(tr)
        db.session.commit()

        flash(f'Penarikan Rp {jumlah:,} ({kategori}) berhasil. Bukti: {no_bukti}', 'success')
        return redirect(url_for('tabungan.detail', id=id))

    return render_template('tabungan/tarik.html', rek=rek, today_str=date.today().strftime('%Y-%m-%d'))


@tabungan_bp.route('/nasabah/<int:nasabah_id>')
@login_required
def by_nasabah(nasabah_id):
    """Shortcut: buka/buat rekening dari halaman nasabah."""
    if current_user.is_nasabah() and nasabah_id != current_user.nasabah_id_fk:
        abort(403)
    nasabah = Nasabah.query.get_or_404(nasabah_id)
    rek     = get_or_create_rekening(nasabah)
    return redirect(url_for('tabungan.detail', id=rek.id))


@tabungan_bp.route('/ajukan-penarikan', methods=['GET', 'POST'])
@login_required
def ajukan_penarikan():
    if not current_user.is_nasabah():
        abort(403)
    
    if not current_user.nasabah:
        flash('Data nasabah tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    nasabah = current_user.nasabah
    rek = get_or_create_rekening(nasabah)
    
    if request.method == 'POST':
        jumlah = int(''.join(c for c in request.form.get('jumlah','0') if c.isdigit()) or '0')
        keterangan = request.form.get('keterangan', '')
        
        if jumlah <= 0:
            flash('Jumlah tidak valid.', 'danger')
            return redirect(url_for('tabungan.ajukan_penarikan'))
            
        if jumlah > rek.saldo_sukarela:
            flash(f'Saldo sukarela tidak cukup. Maksimal: Rp {rek.saldo_sukarela:,}', 'danger')
            return redirect(url_for('tabungan.ajukan_penarikan'))
            
        from ..models import PengajuanPenarikan
        pengajuan = PengajuanPenarikan(
            rekening_id=rek.id,
            jumlah=jumlah,
            keterangan=keterangan,
            status='menunggu'
        )
        db.session.add(pengajuan)
        db.session.commit()
        
        flash('Pengajuan penarikan tabungan berhasil dikirim. Menunggu verifikasi admin.', 'success')
        return redirect(url_for('tabungan.detail', id=rek.id))
        
    return render_template('tabungan/ajukan_penarikan.html', rek=rek)


@tabungan_bp.route('/daftar-pengajuan')
@login_required
def daftar_pengajuan():
    if not current_user.can_write_pembayaran():
        abort(403)
    
    from ..models import PengajuanPenarikan
    list_pengajuan = PengajuanPenarikan.query.order_by(PengajuanPenarikan.created_at.desc()).all()
    return render_template('tabungan/daftar_pengajuan.html', list_pengajuan=list_pengajuan)


@tabungan_bp.route('/proses-pengajuan/<int:id>', methods=['POST'])
@login_required
def proses_pengajuan(id):
    if not current_user.can_write_pembayaran():
        abort(403)
    
    from ..models import PengajuanPenarikan, TransaksiTabungan
    p = PengajuanPenarikan.query.get_or_404(id)
    aksi = request.form.get('aksi') # setujui / tolak
    
    if p.status != 'menunggu':
        flash('Pengajuan sudah diproses.', 'warning')
        return redirect(url_for('tabungan.daftar_pengajuan'))
        
    if aksi == 'setujui':
        rek = p.rekening
        if p.jumlah > rek.saldo_sukarela:
            flash('Saldo nasabah tidak mencukupi saat ini.', 'danger')
            p.status = 'ditolak'
            p.alasan_tolak = 'Saldo tidak mencukupi saat proses persetujuan.'
            db.session.commit()
            return redirect(url_for('tabungan.daftar_pengajuan'))

        rek.saldo_sukarela -= p.jumlah
        no_bukti = generate_no_bukti()
        tr = TransaksiTabungan(
            rekening_id=rek.id,
            tanggal=date.today(),
            jenis='tarik',
            kategori='sukarela',
            jumlah=p.jumlah,
            keterangan=f"Penarikan disetujui: {p.keterangan}",
            no_bukti=no_bukti,
            created_by=current_user.id
        )
        db.session.add(tr)
        p.status = 'disetujui'
        db.session.commit()

        flash(f'Pengajuan disetujui. Saldo nasabah telah berkurang. Bukti: {no_bukti}', 'success')
    else:
        p.status = 'ditolak'
        p.alasan_tolak = request.form.get('alasan', 'Ditolak oleh admin.')
        db.session.commit()
        flash('Pengajuan penarikan ditolak.', 'info')

    return redirect(url_for('tabungan.daftar_pengajuan'))


@tabungan_bp.route('/mutasi/<int:id>')
@login_required
def mutasi(id):
    """Rekening koran / mutasi per rekening."""
    rek = RekeningTabungan.query.get_or_404(id)
    if current_user.is_nasabah() and rek.nasabah_id != current_user.nasabah_id_fk:
        abort(403)

    tgl_awal = request.args.get('tgl_awal', '')
    tgl_akhir = request.args.get('tgl_akhir', '')

    q = TransaksiTabungan.query.filter_by(rekening_id=id)
    if tgl_awal:
        q = q.filter(TransaksiTabungan.tanggal >= date.fromisoformat(tgl_awal))
    if tgl_akhir:
        q = q.filter(TransaksiTabungan.tanggal <= date.fromisoformat(tgl_akhir))
    transaksi_list = q.order_by(TransaksiTabungan.tanggal.asc(), TransaksiTabungan.id.asc()).all()

    # Hitung saldo berjalan
    saldo_berjalan = 0
    for t in transaksi_list:
        if t.jenis == 'setor':
            saldo_berjalan += t.jumlah
        else:
            saldo_berjalan -= t.jumlah
        t.saldo_akhir = saldo_berjalan

    return render_template('tabungan/mutasi.html', rek=rek, transaksi_list=transaksi_list,
                           tgl_awal=tgl_awal, tgl_akhir=tgl_akhir, saldo_berjalan=saldo_berjalan)


@tabungan_bp.route('/laporan')
@login_required
def laporan():
    """Laporan agregat tabungan per desa dan kategori."""
    periode = request.args.get('periode', 'semua')
    tahun = request.args.get('tahun', date.today().strftime('%Y'))

    q = RekeningTabungan.query.join(Nasabah)
    if periode == 'tahun_ini' and tahun:
        # Filter hanya rekening yang punya transaksi di tahun tersebut
        subq = db.session.query(TransaksiTabungan.rekening_id).filter(
            TransaksiTabungan.tanggal >= date(int(tahun), 1, 1),
            TransaksiTabungan.tanggal <= date(int(tahun), 12, 31)
        ).distinct().subquery()
        q = q.filter(RekeningTabungan.id.in_(subq))

    q = q.order_by(Nasabah.kode_desa, Nasabah.nama)
    rekening_list = q.all()

    # Group by desa
    data_per_desa = {}
    total_pokok = 0
    total_wajib = 0
    total_sukarela = 0
    total_semua = 0

    for rek in rekening_list:
        desa = rek.nasabah.kode_desa or 'Lainnya'
        if desa not in data_per_desa:
            data_per_desa[desa] = {'pokok': 0, 'wajib': 0, 'sukarela': 0, 'total': 0, 'count': 0}
        data_per_desa[desa]['pokok'] += rek.saldo_pokok
        data_per_desa[desa]['wajib'] += rek.saldo_wajib
        data_per_desa[desa]['sukarela'] += rek.saldo_sukarela
        total_rek = rek.total_saldo()
        data_per_desa[desa]['total'] += total_rek
        data_per_desa[desa]['count'] += 1
        total_pokok += rek.saldo_pokok
        total_wajib += rek.saldo_wajib
        total_sukarela += rek.saldo_sukarela
        total_semua += total_rek

    return render_template('tabungan/laporan.html',
                           data_per_desa=data_per_desa,
                           total_pokok=total_pokok,
                           total_wajib=total_wajib,
                           total_sukarela=total_sukarela,
                           total_semua=total_semua,
                           periode=periode,
                           tahun=tahun,
                           desa_list=Config.DESA_LIST)


@tabungan_bp.route('/rekap-setoran')
@login_required
def rekap_setoran():
    """Rekapitulasi setoran per periode."""
    dari = request.args.get('dari', '')
    sampai = request.args.get('sampai', '')

    q = TransaksiTabungan.query.filter_by(jenis='setor').join(RekeningTabungan).join(Nasabah)
    if dari:
        q = q.filter(TransaksiTabungan.tanggal >= date.fromisoformat(dari))
    if sampai:
        q = q.filter(TransaksiTabungan.tanggal <= date.fromisoformat(sampai))
    transaksi_list = q.order_by(TransaksiTabungan.tanggal.desc(), TransaksiTabungan.id.desc()).all()

    total_setoran = sum(t.jumlah for t in transaksi_list)
    total_per_kategori = {}
    for t in transaksi_list:
        total_per_kategori[t.kategori] = total_per_kategori.get(t.kategori, 0) + t.jumlah

    # Group by tanggal
    dari_dict = {}
    for t in transaksi_list:
        tgl_str = t.tanggal.strftime('%Y-%m-%d')
        if tgl_str not in dari_dict:
            dari_dict[tgl_str] = {'tanggal': t.tanggal, 'pokok': 0, 'wajib': 0, 'sukarela': 0, 'total': 0}
        dari_dict[tgl_str][t.kategori] += t.jumlah
        dari_dict[tgl_str]['total'] += t.jumlah
    rekap_per_tgl = sorted(dari_dict.values(), key=lambda x: x['tanggal'], reverse=True)

    return render_template('tabungan/rekap_setoran.html',
                           rekap_per_tgl=rekap_per_tgl,
                           transaksi_list=transaksi_list,
                           total_setoran=total_setoran,
                           total_per_kategori=total_per_kategori,
                           dari=dari,
                           sampai=sampai)
