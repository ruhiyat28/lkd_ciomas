from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from ..models import db, Pinjaman, Pembayaran, Nasabah, RekeningTabungan, TransaksiTabungan, BonusPetugas, BonusPembina, User
from config import Config
from datetime import date, datetime, timezone
import math, logging

logger = logging.getLogger(__name__)

pembayaran_bp = Blueprint('pembayaran', __name__)


@pembayaran_bp.before_request
def restrict_nasabah_role():
    if current_user.is_authenticated and current_user.is_nasabah():
        if request.method == 'POST':
            abort(403)

def generate_no_kuitansi():
    year  = date.today().strftime('%Y')
    month = date.today().strftime('%m')
    count = Pembayaran.query.filter(
        Pembayaran.no_kuitansi.like(f'KWT/{year}/{month}/%')
    ).count() + 1
    return f"KWT/{year}/{month}/{count:04d}"


def parse_rupiah(val):
    if not val: return 0
    try:
        return int(''.join(c for c in str(val) if c.isdigit()))
    except (ValueError, TypeError): return 0


def hitung_alokasi(pinjaman, jumlah_bayar):
    jumlah_bayar = (jumlah_bayar // 100) * 100
    tunggak_pokok, tunggak_jasa, bulan_nunggak = pinjaman.get_tunggakan()
    sisa = jumlah_bayar
    bayar_jasa = bayar_pokok = 0
    ket = []
    if tunggak_jasa > 0:
        bj = min(sisa, tunggak_jasa); bayar_jasa += bj; sisa -= bj
    if sisa > 0 and tunggak_pokok > 0:
        bp = min(sisa, tunggak_pokok); bayar_pokok += bp; sisa -= bp
    if sisa > 0 and pinjaman.angsuran_jasa:
        bj = min(sisa, pinjaman.angsuran_jasa); bayar_jasa += bj; sisa -= bj
    if sisa > 0:
        saldo_sisa = pinjaman.get_saldo_pokok() - bayar_pokok
        pa = pinjaman.angsuran_terakhir_pokok \
            if saldo_sisa <= (pinjaman.angsuran_terakhir_pokok or pinjaman.angsuran_pokok) \
            else pinjaman.angsuran_pokok
        pa = min(pa or 0, saldo_sisa)
        bp = min(sisa, pa); bayar_pokok += bp; sisa -= bp

    total_bayar_after, _ = pinjaman.get_realisasi_pembayaran()
    new_total = total_bayar_after + bayar_pokok
    angsuran_ke = 0; kum = 0
    for j in pinjaman.get_jadwal_angsuran():
        kum += j['pokok']; angsuran_ke += 1
        if kum >= new_total: break

    if bulan_nunggak > 0: ket.append(f"Termasuk tunggakan {bulan_nunggak} bulan")
    if sisa > 0: ket.append(f"Kelebihan Rp {sisa:,} → angsuran berikutnya")

    return {'bayar_pokok': bayar_pokok, 'bayar_jasa': bayar_jasa,
            'angsuran_ke': angsuran_ke, 'sisa': sisa, 'keterangan': '. '.join(ket)}


# ── HALAMAN UTAMA: Form + Rekap terpadu ──────────────────────
@pembayaran_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST' and not current_user.can_write_pembayaran(): abort(403)

    search      = request.args.get('q','')
    pinjaman_id = request.args.get('pinjaman_id') or request.form.get('pinjaman_id')
    pinjaman    = None

    # Rekap pembayaran terakhir (bottom table)
    tgl_dari_str   = request.args.get('dari',   date.today().replace(day=1).strftime('%Y-%m-%d'))
    tgl_sampai_str = request.args.get('sampai', date.today().strftime('%Y-%m-%d'))
    desa_filter    = request.args.get('desa','')
    status_acc_filter = request.args.get('status_acc','')
    try:
        d_dari   = datetime.strptime(tgl_dari_str,   '%Y-%m-%d').date()
        d_sampai = datetime.strptime(tgl_sampai_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        d_dari   = date.today().replace(day=1)
        d_sampai = date.today()

    # Load pinjaman
    if pinjaman_id:
        pinjaman = Pinjaman.query.get(pinjaman_id)
        if pinjaman and current_user.is_kader() and pinjaman.nasabah.kode_desa != current_user.kode_desa:
            abort(403)
    elif search:
        query = Pinjaman.query.join(Nasabah).filter(
            (Nasabah.nama.ilike(f'%{search}%')) |
            (Pinjaman.spk.ilike(f'%{search}%'))  |
            (Nasabah.nasabah_id.ilike(f'%{search}%'))
        ).filter(Pinjaman.status == 'cair')
        
        if current_user.is_kader():
            query = query.filter(Nasabah.kode_desa == current_user.kode_desa)
            
        pinjaman = query.first()

    # POST — proses pembayaran
    if request.method == 'POST' and pinjaman:
        jumlah_bayar = parse_rupiah(request.form.get('jumlah_bayar','0'))
        pakai_tab    = 'pakai_tabungan' in request.form
        jumlah_tab   = 0; rekening = None

        if pakai_tab:
            rekening = RekeningTabungan.query.filter_by(nasabah_id=pinjaman.nasabah_id_fk).first()
            if rekening:
                jenis_tab   = request.form.get('jenis_tabungan','sukarela')
                jumlah_tab  = parse_rupiah(request.form.get('jumlah_tabungan','0'))
                saldo_ada   = getattr(rekening, f'saldo_{jenis_tab}', 0)
                jumlah_tab  = min(jumlah_tab, saldo_ada)

        bayar_pokok_manual = parse_rupiah(request.form.get('bayar_pokok','0'))
        bayar_jasa_manual  = parse_rupiah(request.form.get('bayar_jasa','0'))
        total_bayar = bayar_pokok_manual + bayar_jasa_manual

        if total_bayar < 100:
            flash('Total alokasi bayar minimal Rp 100', 'danger')
            return redirect(url_for('pembayaran.index', pinjaman_id=pinjaman.id))
        if bayar_pokok_manual < 0 or bayar_jasa_manual < 0:
            flash('Jumlah bayar tidak valid.', 'danger')
            return redirect(url_for('pembayaran.index', pinjaman_id=pinjaman.id))
        if bayar_pokok_manual > pinjaman.jumlah_pinjaman:
            flash('Pembayaran pokok melebihi total pinjaman.', 'danger')
            return redirect(url_for('pembayaran.index', pinjaman_id=pinjaman.id))
        if pinjaman.get_saldo_pokok() <= 0:
            flash('Pinjaman sudah lunas!', 'warning')
            return redirect(url_for('pembayaran.index'))

        no_kuitansi = generate_no_kuitansi()
        try:
            tanggal_bayar = datetime.strptime(request.form.get('tanggal_bayar',''), '%Y-%m-%d').date()
        except (ValueError, TypeError): tanggal_bayar = date.today()

        # Hitung angsuran_ke berdasarkan bayar_pokok
        total_bayar_after, _ = pinjaman.get_realisasi_pembayaran()
        new_total = total_bayar_after + bayar_pokok_manual
        angsuran_ke = 0; kum = 0
        for j in pinjaman.get_jadwal_angsuran():
            kum += j['pokok']; angsuran_ke += 1
            if kum >= new_total: break

        tunggak_pokok, tunggak_jasa, bulan_nunggak = pinjaman.get_tunggakan()
        ket = []
        if bulan_nunggak > 0: ket.append(f"Termasuk tunggakan {bulan_nunggak} bulan")

        pb = Pembayaran(
            no_kuitansi  = no_kuitansi,
            pinjaman_id  = pinjaman.id,
            tanggal_bayar= tanggal_bayar,
            jumlah_bayar = total_bayar,
            bayar_pokok  = bayar_pokok_manual,
            bayar_jasa   = bayar_jasa_manual,
            angsuran_ke  = angsuran_ke,
            keterangan   = '. '.join(ket),
            created_by   = current_user.id,
            status_acc   = 'menunggu' if current_user.is_kader() else None,
        )
        db.session.add(pb)

        # Debit tabungan jika dipakai
        if jumlah_tab > 0 and rekening:
            jenis_tab = request.form.get('jenis_tabungan','sukarela')
            setattr(rekening, f'saldo_{jenis_tab}',
                    getattr(rekening, f'saldo_{jenis_tab}') - jumlah_tab)
            db.session.flush()
            from ..utils.auto_jurnal import jurnal_pembayaran
            db.session.add(TransaksiTabungan(
                rekening_id=rekening.id, tanggal=tanggal_bayar, jenis='tarik',
                kategori=jenis_tab, jumlah=jumlah_tab,
                keterangan=f'Tambahan angsuran {pinjaman.spk} — {no_kuitansi}',
                no_bukti=no_kuitansi, pembayaran_id=pb.id, created_by=current_user.id))

        # Cek lunas
        total_pokok, _ = pinjaman.get_realisasi_pembayaran()
        if total_pokok + bayar_pokok_manual >= pinjaman.jumlah_pinjaman:
            pinjaman.status = 'lunas'

        db.session.commit()

        # Bonus & Jurnal: hanya jika langsung valid (non-kader)
        # Jika kader, diproses saat approval
        needs_approval = current_user.is_kader() and pb.status_acc == 'menunggu'
        if not needs_approval:
            try:
                bonus = BonusPetugas.hitung_bonus(pb, current_user.id)
                if bonus:
                    db.session.add(bonus)
                    db.session.flush()
                    if current_user.is_kader() and current_user.pembina_id:
                        bonus_pembina = BonusPetugas.buat_bonus_pembina(
                            pb.id, current_user.id, bonus.jumlah_bonus
                        )
                        if bonus_pembina:
                            db.session.add(bonus_pembina)
                    db.session.commit()
            except Exception as e:
                logger.error(f'Bonus gagal dibuat: {e}', exc_info=True)

            try:
                from ..utils.auto_jurnal import jurnal_pembayaran
                jurnal_pembayaran(pb, current_user.id)
            except Exception as e:
                logger.error(f'Jurnal pembayaran gagal: {e}', exc_info=True)

        flash(f'Pembayaran berhasil! Kuitansi: {no_kuitansi}{" — Menunggu persetujuan pembina" if needs_approval else ""}', 'success')
        return redirect(url_for('pembayaran.index', _anchor='') + f'?cetak_id={pb.id}')

    # Data untuk rekap tabel bawah
    if current_user.is_kader():
        desa_filter = current_user.kode_desa

    qr = Pembayaran.query.join(Pinjaman).join(Nasabah).filter(
        Pembayaran.tanggal_bayar >= d_dari,
        Pembayaran.tanggal_bayar <= d_sampai,
    )

    can_see_all = current_user.is_admin() or current_user.is_manajer() or current_user.is_keuangan()

    if status_acc_filter:
        qr = qr.filter(Pembayaran.status_acc == status_acc_filter)
    elif not can_see_all:
        qr = qr.filter(
            db.or_(Pembayaran.status_acc == None, Pembayaran.status_acc == '', Pembayaran.status_acc == 'diterima')
        )
    pembayaran_list = qr.order_by(Pembayaran.tanggal_bayar.desc()).all()
    total_bayar_r  = sum(p.jumlah_bayar for p in pembayaran_list)
    total_pokok_r  = sum(p.bayar_pokok  for p in pembayaran_list)
    total_jasa_r   = sum(p.bayar_jasa   for p in pembayaran_list)

    tunggak_pokok = tunggak_jasa = bulan_nunggak = 0
    rekening = None
    if pinjaman:
        tunggak_pokok, tunggak_jasa, bulan_nunggak = pinjaman.get_tunggakan()
        rekening = RekeningTabungan.query.filter_by(nasabah_id=pinjaman.nasabah_id_fk).first()

    from sqlalchemy import func as _func
    today_d       = date.today()
    start_month   = today_d.replace(day=1)
    bayar_hari_ini   = Pembayaran.query.filter(Pembayaran.tanggal_bayar == today_d).count()
    total_hari_ini   = db.session.query(_func.coalesce(_func.sum(Pembayaran.jumlah_bayar), 0)).filter(Pembayaran.tanggal_bayar == today_d).scalar()
    menunggu_acc     = Pembayaran.query.filter_by(status_acc='menunggu').count()
    bayar_bulan_ini  = Pembayaran.query.filter(Pembayaran.tanggal_bayar >= start_month).count()

    return render_template('pembayaran/index.html',
        pinjaman=pinjaman, search=search,
        tunggak_pokok=tunggak_pokok, tunggak_jasa=tunggak_jasa,
        bulan_nunggak=bulan_nunggak, rekening=rekening,
        today_str=date.today().strftime('%Y-%m-%d'),
        pembayaran_list=pembayaran_list,
        total_bayar_r=total_bayar_r, total_pokok_r=total_pokok_r,
        total_jasa_r=total_jasa_r,
        tgl_dari_str=tgl_dari_str, tgl_sampai_str=tgl_sampai_str,
        desa_filter=desa_filter, desa_list=Config.DESA_LIST,
        status_acc_filter=status_acc_filter,
        bayar_hari_ini=bayar_hari_ini, total_hari_ini=total_hari_ini,
        menunggu_acc=menunggu_acc, bayar_bulan_ini=bayar_bulan_ini)


@pembayaran_bp.route('/kuitansi/<int:id>')
@login_required
def cetak_kuitansi(id):
    pb = Pembayaran.query.get_or_404(id)
    if pb.status_acc == 'menunggu' and not (current_user.is_admin() or current_user.is_manajer() or current_user.is_keuangan()):
        abort(403)
    return render_template('print/kuitansi_angsuran.html', p=pb)


@pembayaran_bp.route('/cetak-terpilih')
@login_required
def cetak_terpilih():
    """Cetak kuitansi untuk pembayaran terpilih (comma-separated IDs)."""
    ids_str = request.args.get('ids','')
    if not ids_str:
        flash('Tidak ada data dipilih.', 'warning')
        return redirect(url_for('pembayaran.index'))
    try:
        ids = [int(x) for x in ids_str.split(',') if x.strip()]
    except (ValueError, TypeError): ids = []

    qr = Pembayaran.query.filter(Pembayaran.id.in_(ids))
    if not (current_user.is_admin() or current_user.is_manajer() or current_user.is_keuangan()):
        qr = qr.filter(
            db.or_(Pembayaran.status_acc == None, Pembayaran.status_acc == '', Pembayaran.status_acc == 'diterima')
        )

    pembayaran_list = qr.order_by(Pembayaran.tanggal_bayar).all()
    return render_template('print/rekap_pembayaran_terpilih.html', pembayaran_list=pembayaran_list,
        total_bayar=sum(p.jumlah_bayar for p in pembayaran_list),
        total_pokok=sum(p.bayar_pokok  for p in pembayaran_list),
        total_jasa =sum(p.bayar_jasa   for p in pembayaran_list))


@pembayaran_bp.route('/search-suggestions')
@login_required
def search_suggestions():
    q = request.args.get('q', '')
    if len(q) < 2:
        return {'results': []}

    query = Pinjaman.query.join(Nasabah).filter(
        (Nasabah.nama.ilike(f'%{q}%')) |
        (Pinjaman.spk.ilike(f'%{q}%')) |
        (Nasabah.nasabah_id.ilike(f'%{q}%'))
    ).filter(Pinjaman.status == 'cair')

    if current_user.is_kader():
        query = query.filter(Nasabah.kode_desa == current_user.kode_desa)

    results = query.limit(10).all()

    return jsonify({
        'results': [
            {
                'id': p.id,
                'nama': p.nasabah.nama,
                'nasabah_id': p.nasabah.nasabah_id,
                'spk': p.spk,
                'jenis': p.nasabah.jenis,
                'text': f"{p.nasabah.nama} ({p.spk}) - {p.nasabah.nasabah_id}"
            } for p in results
        ]
    })


@pembayaran_bp.route('/hapus/<int:id>', methods=['POST'])
@login_required
def hapus(id):
    if not current_user.is_admin(): abort(403)
    pb = Pembayaran.query.get_or_404(id)
    from ..models import JurnalUmum, BonusPetugas, BonusPembina
    try:
        if pb.pinjaman.status == 'lunas':
            pb.pinjaman.status = 'cair'
        jurnal_list = JurnalUmum.query.filter_by(referensi=pb.no_kuitansi, tipe='angsuran').all()
        for j in jurnal_list:
            db.session.delete(j)
        
        # Hapus bonus terkait
        for bonus in pb.bonus_list:
            db.session.delete(bonus)
        for bonus_pembina in pb.bonus_pembina_list:
            db.session.delete(bonus_pembina)
            
        db.session.delete(pb)
        db.session.commit()
        flash(f'Pembayaran {pb.no_kuitansi} berhasil dihapus. Tindakan ini juga menghapus bonus untuk petugas dan bonus terkait untuk pembina.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus pembayaran: {e}', 'danger')
    return redirect(url_for('pembayaran.index'))


# ── ACC / APPROVAL ──────────────────────────────────────────────
@pembayaran_bp.route('/acc/<int:id>', methods=['POST'])
@login_required
def acc(id):
    pb = Pembayaran.query.get_or_404(id)
    if pb.status_acc != 'menunggu':
        flash('Status tidak valid untuk disetujui.', 'warning')
        return redirect_back()
    can_acc = current_user.bisa_acc_pembayaran_ini(pb)
    if not can_acc:
        abort(403)
    pb.status_acc = 'diterima'
    pb.acc_by = current_user.id
    pb.acc_at = datetime.now(timezone.utc)
    db.session.commit()
    bonus = BonusPetugas.hitung_bonus(pb, pb.created_by)
    if bonus:
        db.session.add(bonus)
        db.session.flush()
        try:
            dari_user = User.query.get(pb.created_by)
            if dari_user and dari_user.is_kader() and dari_user.pembina_id:
                bonus_pembina = BonusPetugas.buat_bonus_pembina(pb.id, pb.created_by, bonus.jumlah_bonus)
                if bonus_pembina:
                    db.session.add(bonus_pembina)
        except Exception as e:
            logger.error(f'Bonus pembina gagal: {e}', exc_info=True)

    try:
        from ..utils.auto_jurnal import jurnal_pembayaran
        jurnal_pembayaran(pb, pb.created_by)
    except Exception as e:
        logger.error(f'Jurnal pembayaran gagal saat approval: {e}', exc_info=True)

    db.session.commit()
    flash(f'Pembayaran {pb.no_kuitansi} disetujui.', 'success')
    return redirect_back()


@pembayaran_bp.route('/tolak/<int:id>', methods=['POST'])
@login_required
def tolak(id):
    pb = Pembayaran.query.get_or_404(id)
    if pb.status_acc != 'menunggu':
        flash('Status tidak valid untuk ditolak.', 'warning')
        return redirect_back()
    if not current_user.bisa_acc_pembayaran_ini(pb):
        abort(403)
    pb.status_acc = 'ditolak'
    pb.acc_by = current_user.id
    pb.acc_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f'Pembayaran {pb.no_kuitansi} ditolak.', 'success')
    return redirect_back()


def redirect_back():
    return redirect(request.referrer or url_for('pembayaran.index'))
