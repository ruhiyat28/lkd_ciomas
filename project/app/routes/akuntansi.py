from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from ..models import db, AkunCOA, JurnalUmum, JurnalDetail, Aset, Pengaturan, AsetMutasi, OpnameAset
from ..utils.coa_seed import seed_coa, GOLONGAN_MAP
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

akuntansi_bp = Blueprint('akuntansi', __name__)
ROLES_KEUANGAN = ('admin', 'manajer_lkd', 'keuangan')

@akuntansi_bp.before_request
def restrict_kader():
    if current_user.is_kader():
        abort(403)


def _periode(req):
    d1 = req.args.get('dari',   date.today().replace(day=1).strftime('%Y-%m-%d'))
    d2 = req.args.get('sampai', date.today().strftime('%Y-%m-%d'))
    try: d_dari   = datetime.strptime(d1,'%Y-%m-%d').date()
    except (ValueError, TypeError): d_dari = date.today().replace(day=1)
    try: d_sampai = datetime.strptime(d2,'%Y-%m-%d').date()
    except (ValueError, TypeError): d_sampai = date.today()
    return d_dari, d_sampai, d1, d2


def _akun_saldo(kode, tgl_sampai=None):
    a = AkunCOA.query.filter_by(kode=kode).first()
    return a.get_saldo(None, tgl_sampai) if a else 0


def _akun_saldo_like(pattern, tgl_sampai=None):
    akuns = AkunCOA.query.filter(AkunCOA.kode.like(pattern), AkunCOA.bisa_jurnal==True).all()
    return sum(a.get_saldo(None, tgl_sampai) for a in akuns)


def _sum_golongan(golongan, tgl_dari=None, tgl_sampai=None, exclude_tipe=None):
    akuns = AkunCOA.query.filter_by(golongan=golongan, bisa_jurnal=True, aktif=True).all()
    return sum(a.get_saldo(tgl_dari, tgl_sampai, exclude_tipe) for a in akuns)


# ── COA ──────────────────────────────────────────────────────
@akuntansi_bp.route('/coa')
@login_required
def coa():
    akun_list = AkunCOA.query.order_by(AkunCOA.kode).all()
    if not akun_list:
        seed_coa()
        akun_list = AkunCOA.query.order_by(AkunCOA.kode).all()
    # Group by top-level induk
    from collections import defaultdict
    tree = defaultdict(list)
    for a in akun_list:
        top = a.kode.split('.')[0]
        tree[top].append(a)
    return render_template('akuntansi/coa.html',
        akun_list=akun_list, tree=dict(tree),
        GOLONGAN_MAP=GOLONGAN_MAP)


@akuntansi_bp.route('/coa/seed', methods=['POST'])
@login_required
def coa_seed_route():
    if not current_user.is_admin(): abort(403)
    # Force reseed - delete dependants first to avoid IntegrityError
    try:
        from sqlalchemy import text
        if db.engine.name == 'postgresql':
            db.session.execute(text("""
                TRUNCATE TABLE 
                jurnal_detail, jurnal_umum, saldo_awal, 
                transaksi_tabungan, pembayaran, detail_spp, 
                jaminan_bpkb, jaminan_shm, jaminan_lain, 
                pinjaman, akun_coa, aset_mutasi, opname_aset, aset CASCADE
            """))
        else:
            # Fallback untuk SQLite atau lainnya
            from ..models import JurnalDetail, SaldoAwal, Pembayaran, Pinjaman, DetailSPP, TransaksiTabungan, JaminanBPKB, JaminanSHM, JaminanLain, AsetMutasi, OpnameAset, Aset
            JurnalDetail.query.delete()
            JurnalUmum.query.delete()
            SaldoAwal.query.delete()
            TransaksiTabungan.query.delete()
            Pembayaran.query.delete()
            DetailSPP.query.delete()
            JaminanBPKB.query.delete()
            JaminanSHM.query.delete()
            JaminanLain.query.delete()
            Pinjaman.query.delete()
            AsetMutasi.query.delete()
            OpnameAset.query.delete()
            Aset.query.delete()
        
        db.session.commit()
        seed_coa(force=True)
        flash('Data transaksi dibersihkan dan COA standar berhasil dimuat ulang.','success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal membersihkan data: {str(e)}','danger')
    return redirect(url_for('akuntansi.coa'))


@akuntansi_bp.route('/coa/tambah', methods=['GET','POST'])
@login_required
def coa_tambah():
    if current_user.role not in ('admin','keuangan'): abort(403)
    if request.method == 'POST':
        kode = request.form.get('kode','').strip()
        if AkunCOA.query.filter_by(kode=kode).first():
            flash(f'Kode {kode} sudah ada.','danger')
        else:
            parts = kode.split('.')
            level = len(parts)
            gol   = int(parts[0])
            parent_kode = '.'.join(parts[:-1]) if level > 1 else None
            parent = AkunCOA.query.filter_by(kode=parent_kode).first() if parent_kode else None
            akun = AkunCOA(
                kode=kode, nama=request.form.get('nama',''),
                golongan=gol, golongan_nama=GOLONGAN_MAP.get(gol,''),
                saldo_normal=request.form.get('saldo_normal','debit'),
                level=level, parent_id=parent.id if parent else None,
                bisa_jurnal=(level == 4),
                aktif=True,
            )
            db.session.add(akun); db.session.commit()
            flash(f'Akun {kode} ditambahkan.','success')
            return redirect(url_for('akuntansi.coa'))
    akun_list = AkunCOA.query.order_by(AkunCOA.kode).all()
    return render_template('akuntansi/coa_form.html',
        akun=None, akun_list=akun_list, GOLONGAN_MAP=GOLONGAN_MAP)


@akuntansi_bp.route('/coa/edit/<int:id>', methods=['GET','POST'])
@login_required
def coa_edit(id):
    if current_user.role not in ('admin','keuangan'): abort(403)
    akun = AkunCOA.query.get_or_404(id)
    if request.method == 'POST':
        akun.nama         = request.form.get('nama', akun.nama)
        akun.saldo_normal = request.form.get('saldo_normal', akun.saldo_normal)
        akun.aktif        = 'aktif' in request.form
        akun.keterangan   = request.form.get('keterangan','')
        akun.bisa_jurnal  = 'bisa_jurnal' in request.form
        db.session.commit()
        flash('Akun diperbarui.','success')
        return redirect(url_for('akuntansi.coa'))
    akun_list = AkunCOA.query.order_by(AkunCOA.kode).all()
    return render_template('akuntansi/coa_form.html',
        akun=akun, akun_list=akun_list, GOLONGAN_MAP=GOLONGAN_MAP)


@akuntansi_bp.route('/coa/hapus/<int:id>', methods=['POST'])
@login_required
def coa_hapus(id):
    if current_user.role not in ('admin','keuangan'): abort(403)
    akun = AkunCOA.query.get_or_404(id)
    if akun.kode in ['1.1.01.01','1.1.03.01','1.1.01.02']:
        flash('Akun kunci tidak bisa dihapus.','danger')
        return redirect(url_for('akuntansi.coa'))
    children = AkunCOA.query.filter_by(parent_id=akun.id).first()
    if children:
        flash('Tidak bisa menghapus: akun ini memiliki anak.','danger')
        return redirect(url_for('akuntansi.coa'))
    from ..models import JurnalDetail
    ada_jurnal = JurnalDetail.query.filter_by(akun_id=akun.id).first()
    if ada_jurnal:
        flash('Tidak bisa menghapus: akun sudah pernah digunakan di jurnal. Gunakan Nonaktif sebagai alternatif.','warning')
        return redirect(url_for('akuntansi.coa'))
    db.session.delete(akun)
    db.session.commit()
    flash(f'Akun {akun.kode} ({akun.nama}) beserta semua data terkait telah berhasil dihapus.', 'success')
    return redirect(url_for('akuntansi.coa'))


@akuntansi_bp.route('/coa/api')
@login_required
def coa_api():
    q = request.args.get('q','')
    load_all = request.args.get('all','')
    base = AkunCOA.query.filter(AkunCOA.bisa_jurnal==True, AkunCOA.aktif==True)
    if load_all == '1':
        items = base.order_by(AkunCOA.kode).all()
    else:
        items = base.filter(
            AkunCOA.kode.ilike(f'%{q}%') | AkunCOA.nama.ilike(f'%{q}%')
        ).order_by(AkunCOA.kode).limit(30).all()
    return jsonify([{
        'id': a.id, 'kode': a.kode, 'nama': a.nama,
        'saldo_normal': a.saldo_normal, 'golongan': a.golongan
    } for a in items])


# ── JURNAL UMUM ──────────────────────────────────────────────
@akuntansi_bp.route('/jurnal')
@login_required
def jurnal():
    d_dari, d_sampai, d1, d2 = _periode(request)
    tipe = request.args.get('tipe','')
    q = JurnalUmum.query.filter(
        JurnalUmum.tanggal >= d_dari, JurnalUmum.tanggal <= d_sampai)
    if tipe: q = q.filter(JurnalUmum.tipe == tipe)
    jlist = q.order_by(JurnalUmum.tanggal, JurnalUmum.id).all()
    return render_template('akuntansi/jurnal.html',
        jurnal_list=jlist, tgl_dari=d1, tgl_sampai=d2, tipe_filter=tipe,
        total_debit=sum(j.total_debit for j in jlist),
        total_kredit=sum(j.total_kredit for j in jlist))


@akuntansi_bp.route('/jurnal/tambah', methods=['GET','POST'])
@login_required
def jurnal_tambah():
    if not current_user.can_view_akuntansi(): abort(403)
    if request.method == 'POST':
        try: tgl = datetime.strptime(request.form.get('tanggal',''),'%Y-%m-%d').date()
        except (ValueError, TypeError): tgl = date.today()
        akun_ids = request.form.getlist('akun_id[]')
        debits   = request.form.getlist('debit[]')
        kredits  = request.form.getlist('kredit[]')
        kets     = request.form.getlist('ket_baris[]') or []
        def clean(v): return int(''.join(c for c in str(v) if c.isdigit()) or '0')
        td = sum(clean(d) for d in debits)
        tk = sum(clean(k) for k in kredits)
        if td != tk:
            flash(f'Jurnal tidak balance! D={td:,} ≠ K={tk:,}','danger')
            return redirect(url_for('akuntansi.jurnal_tambah'))
        today = date.today()
        prefix = f"JU-MAN/{today.year}/{today.month:02d}/"
        count  = JurnalUmum.query.filter(JurnalUmum.no_jurnal.like(f'{prefix}%')).count()+1
        j = JurnalUmum(no_jurnal=f"{prefix}{count:04d}", tanggal=tgl,
                       keterangan=request.form.get('keterangan',''),
                       referensi=request.form.get('referensi',''),
                       tipe='manual', status='posted',
                       total_debit=td, total_kredit=tk, created_by=current_user.id)
        db.session.add(j); db.session.flush()
        for i, aid in enumerate(akun_ids):
            if not aid: continue
            d = clean(debits[i] if i<len(debits) else '0')
            k = clean(kredits[i] if i<len(kredits) else '0')
            if d==0 and k==0: continue
            db.session.add(JurnalDetail(
                jurnal_id=j.id, akun_id=int(aid),
                keterangan=kets[i] if i<len(kets) else '', debit=d, kredit=k))
        db.session.commit()
        flash(f'Jurnal {j.no_jurnal} tersimpan.','success')
        return redirect(url_for('akuntansi.jurnal'))
    akun_list = AkunCOA.query.filter_by(bisa_jurnal=True,aktif=True).order_by(AkunCOA.kode).all()
    return render_template('akuntansi/jurnal_form.html', akun_list=akun_list)


@akuntansi_bp.route('/jurnal/detail/<int:id>')
@login_required
def jurnal_detail(id):
    return render_template('akuntansi/jurnal_detail.html', j=JurnalUmum.query.get_or_404(id))


@akuntansi_bp.route('/jurnal/cetak/<int:id>')
@login_required
def jurnal_cetak(id):
    j = JurnalUmum.query.get_or_404(id)
    manajer_lkd = Pengaturan.get('manajer_lkd', '')
    direktur = Pengaturan.get('direktur', '')
    return render_template('print/slip_jurnal.html', j=j, manajer_lkd=manajer_lkd, direktur=direktur, today=date.today())


@akuntansi_bp.route('/jurnal/hapus/<int:id>', methods=['POST'])
@login_required
def jurnal_hapus(id):
    if not current_user.is_admin(): abort(403)
    j = JurnalUmum.query.get_or_404(id)
    if j.tipe != 'manual':
        flash('Jurnal otomatis tidak bisa dihapus.','danger')
        return redirect(url_for('akuntansi.jurnal'))
    db.session.delete(j); db.session.commit()
    flash(f'Jurnal {j.no_jurnal} ({j.keterangan}) berhasil dihapus.', 'success')
    return redirect(url_for('akuntansi.jurnal'))


# ── BUKU BESAR ───────────────────────────────────────────────
@akuntansi_bp.route('/buku-besar')
@login_required
def buku_besar():
    d_dari, d_sampai, d1, d2 = _periode(request)
    akun_id  = request.args.get('akun_id','')
    akun_list= AkunCOA.query.filter_by(bisa_jurnal=True,aktif=True).order_by(AkunCOA.kode).all()
    akun_sel = AkunCOA.query.get(akun_id) if akun_id else None
    mutasi=[]; saldo_awal=0
    if akun_sel:
        # Gunakan get_saldo untuk menghitung saldo awal sebelum tgl_dari
        saldo_awal = akun_sel.get_saldo(None, d_dari - relativedelta(days=1))
        rows = db.session.query(JurnalDetail,JurnalUmum).join(JurnalUmum).filter(
            JurnalDetail.akun_id==akun_sel.id, JurnalUmum.status=='posted',
            JurnalUmum.tanggal>=d_dari, JurnalUmum.tanggal<=d_sampai
        ).order_by(JurnalUmum.tanggal,JurnalUmum.id).all()
        saldo = saldo_awal
        for det,jur in rows:
            saldo += (det.debit-det.kredit) if akun_sel.saldo_normal=='debit' else (det.kredit-det.debit)
            mutasi.append({'jur':jur,'det':det,'saldo':saldo})
    if request.args.get('cetak') == '1' and akun_sel:
        lembaga = {'nama': Pengaturan.get('nama_lembaga'), 'direktur': Pengaturan.get('direktur')}
        return render_template('print/buku_besar_cetak.html',
            akun_sel=akun_sel, mutasi=mutasi, saldo_awal=saldo_awal,
            tgl_dari=d_dari, tgl_sampai=d_sampai, lembaga=lembaga)
    return render_template('akuntansi/buku_besar.html',
        akun_list=akun_list, akun_sel=akun_sel, mutasi=mutasi,
        saldo_awal=saldo_awal, tgl_dari=d1, tgl_sampai=d2, akun_id=akun_id)


# ── NERACA SALDO ─────────────────────────────────────────────
@akuntansi_bp.route('/neraca-saldo')
@login_required
def neraca_saldo():
    d_dari, d_sampai, d1, d2 = _periode(request)
    rows=[]; td_tot=tk_tot=0
    for a in AkunCOA.query.filter_by(bisa_jurnal=True,aktif=True).order_by(AkunCOA.kode).all():
        s = a.get_saldo(None, d_sampai)
        if s==0: continue
        d = max(s,0) if a.saldo_normal=='debit' else max(-s,0)
        k = max(s,0) if a.saldo_normal=='kredit' else max(-s,0)
        if d==0 and k==0: continue
        rows.append({'akun':a,'debit':d,'kredit':k})
        td_tot+=d; tk_tot+=k
    lembaga={'nama':Pengaturan.get('nama_lembaga'),'direktur':Pengaturan.get('direktur')}
    tmpl = 'print/neraca_saldo_cetak.html' if request.args.get('cetak')=='1' else 'akuntansi/neraca_saldo.html'
    return render_template(tmpl,
        rows=rows, total_d=td_tot, total_k=tk_tot, tgl_dari=d1, tgl_sampai=d2, lembaga=lembaga)


# ── LABA RUGI ────────────────────────────────────────────────
@akuntansi_bp.route('/laba-rugi')
@login_required
def laba_rugi():
    d_dari, d_sampai, d1, d2 = _periode(request)
    def gol_rows(gol):
        rows=[]; tot=0
        for a in AkunCOA.query.filter_by(golongan=gol,bisa_jurnal=True,aktif=True).order_by(AkunCOA.kode).all():
            s = a.get_saldo(d_dari, d_sampai)
            if s: rows.append({'akun':a,'saldo':s}); tot+=s
        return rows, tot
    pend_rows,tot_pend = gol_rows(4)
    hpp_rows, tot_hpp  = gol_rows(5)
    beban_rows,tot_beban = gol_rows(6)
    lain_rows, tot_lain = [], 0
    for gol in [7]:
        r,t = gol_rows(gol); lain_rows+=r; tot_lain+=t
    laba_kotor = tot_pend - tot_hpp
    laba_usaha = laba_kotor - tot_beban
    laba_bersih= laba_usaha + tot_lain
    lembaga={'nama':Pengaturan.get('nama_lembaga'),'direktur':Pengaturan.get('direktur')}
    tmpl = 'print/laba_rugi_cetak.html' if request.args.get('cetak')=='1' else 'akuntansi/laba_rugi.html'
    return render_template(tmpl,
        pend_rows=pend_rows, tot_pend=tot_pend,
        hpp_rows=hpp_rows, tot_hpp=tot_hpp,
        beban_rows=beban_rows, tot_beban=tot_beban,
        lain_rows=lain_rows, tot_lain=tot_lain,
        laba_kotor=laba_kotor, laba_usaha=laba_usaha, laba_bersih=laba_bersih,
        tgl_dari=d_dari, tgl_sampai=d_sampai, tgl_dari_str=d1, tgl_sampai_str=d2, lembaga=lembaga)


# ── NERACA ───────────────────────────────────────────────────
@akuntansi_bp.route('/neraca')
@login_required
def neraca():
    d2_str = request.args.get('sampai', date.today().strftime('%Y-%m-%d'))
    try: d_sampai = datetime.strptime(d2_str,'%Y-%m-%d').date()
    except (ValueError, TypeError): d_sampai = date.today()
    d_prev = date(d_sampai.year - 1, 12, 31)
    exclude_tutup = ['tutup_buku']

    def get_gol(gol, sampai, exclude=None):
        rows=[]; tot=0
        for a in AkunCOA.query.filter_by(golongan=gol,bisa_jurnal=True,aktif=True).order_by(AkunCOA.kode).all():
            s=a.get_saldo(None, sampai, exclude)
            if s: rows.append({'akun':a,'saldo':s}); tot+=s
        return rows,tot

    def sum_gol(gol, sampai, exclude=None):
        return _sum_golongan(gol, None, sampai, exclude)

    # Current year
    aset_rows,tot_aset = get_gol(1, d_sampai)
    kwjb_rows,tot_kwjb = get_gol(2, d_sampai)
    ekuitas_rows,tot_ekuitas = get_gol(3, d_sampai)
    laba = (sum_gol(4, d_sampai) + sum_gol(7, d_sampai)
            - sum_gol(5, d_sampai) - sum_gol(6, d_sampai))
    tot_ekuitas_net = tot_ekuitas + laba

    # Previous year (exclude closing entries to show pre-closing balances)
    aset_rows_prev,tot_aset_prev = get_gol(1, d_prev, exclude_tutup)
    kwjb_rows_prev,tot_kwjb_prev = get_gol(2, d_prev, exclude_tutup)
    ekuitas_rows_prev,tot_ekuitas_prev = get_gol(3, d_prev, exclude_tutup)
    laba_prev = (sum_gol(4, d_prev, exclude_tutup) + sum_gol(7, d_prev, exclude_tutup)
                 - sum_gol(5, d_prev, exclude_tutup) - sum_gol(6, d_prev, exclude_tutup))
    tot_ekuitas_net_prev = tot_ekuitas_prev + laba_prev

    aset_prev_map     = {r['akun'].id: r['saldo'] for r in aset_rows_prev}
    kwjb_prev_map     = {r['akun'].id: r['saldo'] for r in kwjb_rows_prev}
    ekuitas_prev_map  = {r['akun'].id: r['saldo'] for r in ekuitas_rows_prev}

    lembaga={'nama':Pengaturan.get('nama_lembaga'),'direktur':Pengaturan.get('direktur')}
    tmpl = 'print/neraca_cetak.html' if request.args.get('cetak')=='1' else 'akuntansi/neraca.html'
    return render_template(tmpl,
        aset_rows=aset_rows, tot_aset=tot_aset,
        kwjb_rows=kwjb_rows, tot_kwjb=tot_kwjb,
        ekuitas_rows=ekuitas_rows, tot_ekuitas=tot_ekuitas,
        laba_berjalan=laba, tot_ekuitas_net=tot_ekuitas_net,
        aset_prev_map=aset_prev_map, tot_aset_prev=tot_aset_prev,
        kwjb_prev_map=kwjb_prev_map, tot_kwjb_prev=tot_kwjb_prev,
        ekuitas_prev_map=ekuitas_prev_map, tot_ekuitas_prev=tot_ekuitas_prev,
        laba_berjalan_prev=laba_prev, tot_ekuitas_net_prev=tot_ekuitas_net_prev,
        d_sampai=d_sampai, d_prev=d_prev, d_sampai_str=d2_str, lembaga=lembaga)


# ── ARUS KAS (3 KELOMPOK) ─────────────────────────────────────
@akuntansi_bp.route('/arus-kas')
@login_required
def arus_kas():
    d_dari, d_sampai, d1, d2 = _periode(request)
    lembaga = {'nama': Pengaturan.get('nama_lembaga')}
    KAS = '1.1.01.01'

    def sum_kas_by_tipe(tipe_list, side):
        akun_kas = AkunCOA.query.filter_by(kode=KAS).first()
        if not akun_kas: return 0
        return db.session.query(func.sum(
            JurnalDetail.debit if side=='debit' else JurnalDetail.kredit
        )).join(JurnalUmum).filter(
            JurnalDetail.akun_id == akun_kas.id,
            JurnalUmum.status == 'posted',
            JurnalUmum.tipe.in_(tipe_list),
            JurnalUmum.tanggal >= d_dari,
            JurnalUmum.tanggal <= d_sampai
        ).scalar() or 0

    def sum_kas_manual_by_golongan(gols, side_kas, by_kode=False):
        """
        Untuk jurnal manual, kita cari baris KAS (debit/kredit) 
        yang lawan transaksinya adalah golongan atau kode tertentu.
        """
        akun_kas = AkunCOA.query.filter_by(kode=KAS).first()
        if not akun_kas: return 0
        
        # Cari ID jurnal yang tipe manual dan ada akun golongan/kode tertentu
        if by_kode:
            subq = db.session.query(JurnalDetail.jurnal_id).join(AkunCOA).filter(
                AkunCOA.kode.in_(gols)
            ).subquery()
        else:
            subq = db.session.query(JurnalDetail.jurnal_id).join(AkunCOA).filter(
                AkunCOA.golongan.in_(gols)
            ).subquery()
        
        return db.session.query(func.sum(
            JurnalDetail.debit if side_kas=='debit' else JurnalDetail.kredit
        )).join(JurnalUmum).filter(
            JurnalDetail.akun_id == akun_kas.id,
            JurnalUmum.status == 'posted',
            JurnalUmum.tipe == 'manual',
            JurnalUmum.id.in_(subq),
            JurnalUmum.tanggal >= d_dari,
            JurnalUmum.tanggal <= d_sampai
        ).scalar() or 0

    # 1. OPERASI
    # Masuk: Total Kas dari Angsuran
    total_kas_angsuran = sum_kas_by_tipe(['angsuran'], 'debit')
    
    # Split Pokok dan Jasa untuk tampilan laporan yang lebih detail
    # Kita hitung Jasa dari sisi Kredit pendapatan di jurnal angsuran
    kas_masuk_ops_jasa = db.session.query(func.sum(JurnalDetail.kredit)).join(JurnalUmum).join(AkunCOA).filter(
        AkunCOA.golongan == 4, # Pendapatan
        JurnalUmum.tipe == 'angsuran',
        JurnalUmum.tanggal >= d_dari, JurnalUmum.tanggal <= d_sampai
    ).scalar() or 0
    kas_masuk_ops_pokok = total_kas_angsuran - kas_masuk_ops_jasa
    
    # Masuk: Admin (biasanya dari manual atau potongan pencairan jika ada)
    kas_masuk_ops_admin = sum_kas_manual_by_golongan([4], 'debit') 
    
    # Keluar: Pencairan Pinjaman
    kas_keluar_pencairan = sum_kas_by_tipe(['pencairan'], 'kredit')
    # Keluar: Beban Operasional (Golongan 6 & 7 manual)
    kas_keluar_ops_beban = sum_kas_manual_by_golongan([6, 7], 'kredit')
    kas_keluar_gaji = sum_kas_manual_by_golongan(['6.1.01.00'], 'kredit', by_kode=True) # Beban Gaji spesifik jika ingin dipisah
    
    net_ops = (kas_masuk_ops_pokok + kas_masuk_ops_jasa + kas_masuk_ops_admin) - (kas_keluar_pencairan + kas_keluar_ops_beban)

    # 2. INVESTASI (1.2.xx)
    subq_aset_tetap = db.session.query(JurnalDetail.jurnal_id).join(AkunCOA).filter(
        AkunCOA.kode.like('1.2.%')
    ).subquery()
    
    kas_masuk_inv_aset = db.session.query(func.sum(JurnalDetail.debit)).join(JurnalUmum).filter(
        JurnalDetail.akun_id == AkunCOA.query.filter_by(kode=KAS).first().id,
        JurnalUmum.id.in_(subq_aset_tetap),
        JurnalUmum.tanggal >= d_dari, JurnalUmum.tanggal <= d_sampai
    ).scalar() or 0
    
    kas_keluar_inv_aset = db.session.query(func.sum(JurnalDetail.kredit)).join(JurnalUmum).filter(
        JurnalDetail.akun_id == AkunCOA.query.filter_by(kode=KAS).first().id,
        JurnalUmum.id.in_(subq_aset_tetap),
        JurnalUmum.tanggal >= d_dari, JurnalUmum.tanggal <= d_sampai
    ).scalar() or 0
    
    kas_masuk_inv_lain = 0
    kas_keluar_inv_lain = 0
    net_inv = (kas_masuk_inv_aset + kas_masuk_inv_lain) - (kas_keluar_inv_aset + kas_keluar_inv_lain)

    # 3. PENDANAAN (Modal)
    kas_masuk_pend_modal = sum_kas_manual_by_golongan([3], 'debit')
    kas_keluar_pend_modal = sum_kas_manual_by_golongan([3], 'kredit')
    kas_masuk_pend_lain = 0
    
    net_pend = (kas_masuk_pend_modal + kas_masuk_pend_lain) - kas_keluar_pend_modal

    net_total = net_ops + net_inv + net_pend

    # Saldo awal & akhir kas
    akun_kas = AkunCOA.query.filter_by(kode=KAS).first()
    saldo_awal_kas = akun_kas.get_saldo(None, d_dari - relativedelta(days=1)) if akun_kas else 0
    saldo_akhir_kas = saldo_awal_kas + net_total

    tmpl = 'print/arus_kas_cetak.html' if request.args.get('cetak')=='1' else 'akuntansi/arus_kas.html'
    return render_template(tmpl,
        kas_masuk_ops_pokok=kas_masuk_ops_pokok,
        kas_masuk_ops_jasa=kas_masuk_ops_jasa,
        kas_masuk_ops_admin=kas_masuk_ops_admin,
        kas_keluar_pencairan=kas_keluar_pencairan,
        kas_keluar_ops_beban=kas_keluar_ops_beban,
        kas_keluar_gaji=kas_keluar_gaji,
        net_ops=net_ops,
        kas_masuk_inv_aset=kas_masuk_inv_aset,
        kas_masuk_inv_lain=kas_masuk_inv_lain,
        kas_keluar_inv_aset=kas_keluar_inv_aset,
        kas_keluar_inv_lain=kas_keluar_inv_lain,
        net_inv=net_inv,
        kas_masuk_pend_modal=kas_masuk_pend_modal,
        kas_masuk_pend_lain=kas_masuk_pend_lain,
        kas_keluar_pend_modal=kas_keluar_pend_modal,
        net_pend=net_pend,
        net_total=net_total,
        saldo_awal_kas=saldo_awal_kas,
        saldo_akhir_kas=saldo_akhir_kas,
        tgl_dari=d_dari, tgl_sampai=d_sampai,
        tgl_dari_str=d1, tgl_sampai_str=d2, lembaga=lembaga)



# ── PERUBAHAN EKUITAS ────────────────────────────────────────
@akuntansi_bp.route('/perubahan-ekuitas')
@login_required
def perubahan_ekuitas():
    d_dari, d_sampai, d1, d2 = _periode(request)
    modal_awal  = _akun_saldo_like('3.1.01.%', d_dari - relativedelta(days=1))
    modal_awal += _akun_saldo('3.1.02.01', d_dari - relativedelta(days=1))
    modal_awal += _akun_saldo('3.1.02.02', d_dari - relativedelta(days=1))
    modal_awal += _akun_saldo('3.4.01.01', d_dari - relativedelta(days=1))
    laba_awal   = _akun_saldo('3.3.01.01', d_dari - relativedelta(days=1))
    laba_awal  += _akun_saldo('3.3.01.02', d_dari - relativedelta(days=1))
    laba_periode = (_sum_golongan(4, d_dari, d_sampai) + _sum_golongan(7, d_dari, d_sampai)
                    - _sum_golongan(5, d_dari, d_sampai) - _sum_golongan(6, d_dari, d_sampai))
    modal_akhir = (_akun_saldo_like('3.1.01.%') + _akun_saldo('3.1.02.01')
                   + _akun_saldo('3.1.02.02') + _akun_saldo('3.4.01.01'))
    ekuitas_akhir = modal_akhir + laba_awal + laba_periode
    lembaga={'nama':Pengaturan.get('nama_lembaga'),'direktur':Pengaturan.get('direktur')}
    tmpl = 'print/perubahan_ekuitas_cetak.html' if request.args.get('cetak')=='1' else 'akuntansi/perubahan_ekuitas.html'
    return render_template(tmpl,
        modal_awal=modal_awal, laba_awal=laba_awal,
        laba_periode=laba_periode, modal_akhir=modal_akhir,
        ekuitas_akhir=ekuitas_akhir,
        tgl_dari=d_dari, tgl_sampai=d_sampai,
        tgl_dari_str=d1, tgl_sampai_str=d2, lembaga=lembaga)


# ── MANAJEMEN ASET ───────────────────────────────────────────
@akuntansi_bp.route('/aset')
@login_required
def aset_index():
    aset_list = Aset.query.filter_by(aktif=True).order_by(Aset.kode_aset).all()
    cetak = request.args.get('cetak')
    total_perolehan = sum(a.nilai_perolehan for a in aset_list)
    total_akumulasi = sum(a.akumulasi_penyusutan for a in aset_list)
    total_buku = sum(a.nilai_buku for a in aset_list)
    tmpl = 'print/daftar_aset.html' if cetak else 'akuntansi/aset.html'
    return render_template(tmpl,
        aset_list=aset_list,
        total_perolehan=total_perolehan,
        total_akumulasi=total_akumulasi,
        total_buku=total_buku,
        tanggal_cetak=date.today())


KATEGORI_KE_AKUN = {
    'Tanah': '1.3.01.01',
    'Kendaraan': '1.3.02.01',
    'Peralatan dan Mesin': '1.3.03.01',
    'Meubelair': '1.3.04.01',
    'Gedung dan Bangunan': '1.3.05.01',
    'Konstruksi Dalam Pengerjaan': '1.3.06.01',
    'Aset Tetap Lainnya': '1.3.99.99',
}
KATEGORI_LIST = list(KATEGORI_KE_AKUN.keys())

KATEGORI_DEPR = {
    'Kendaraan': ('1.3.07.01', '6.1.07.02'),
    'Peralatan dan Mesin': ('1.3.07.02', '6.1.07.03'),
    'Meubelair': ('1.3.07.03', '6.1.07.04'),
    'Gedung dan Bangunan': ('1.3.07.04', '6.1.07.05'),
    'Aset Tetap Lainnya': ('1.3.07.02', '6.1.07.03'),
}


@akuntansi_bp.route('/aset/tambah', methods=['GET','POST'])
@login_required
def aset_tambah():
    if current_user.role not in ('admin','keuangan'): abort(403)
    akun_list = AkunCOA.query.filter(AkunCOA.golongan==1,AkunCOA.aktif==True).order_by(AkunCOA.kode).all()
    akun_sumber = AkunCOA.query.filter(AkunCOA.bisa_jurnal==True,AkunCOA.aktif==True).order_by(AkunCOA.kode).all()
    kas_tunai = AkunCOA.query.filter_by(kode='1.1.01.01').first()
    default_sumber_id = kas_tunai.id if kas_tunai else None
    if request.method == 'POST':
        try: tgl=datetime.strptime(request.form.get('tanggal_perolehan',''),'%Y-%m-%d').date()
        except (ValueError, TypeError): tgl=None
        def num(v): return int(''.join(c for c in str(v) if c.isdigit()) or '0')
        nilai=num(request.form.get('nilai_perolehan',0))
        akum=num(request.form.get('akumulasi_penyusutan',0))
        a=Aset(kode_aset=request.form.get('kode_aset',''),
               nama=request.form.get('nama',''),
               kategori=request.form.get('kategori',''),
               tanggal_perolehan=tgl, nilai_perolehan=nilai,
               umur_ekonomis=int(request.form.get('umur_ekonomis',0) or 0),
               akumulasi_penyusutan=akum, nilai_buku=nilai-akum,
               lokasi=request.form.get('lokasi',''),
               kondisi=request.form.get('kondisi','baik'),
               keterangan=request.form.get('keterangan',''),
               akun_id=request.form.get('akun_id') or None,
               created_by=current_user.id)
        try:
            db.session.add(a); db.session.flush()

            sumber_id = request.form.get('sumber_dana_id', type=int)
            if sumber_id and a.akun_id and nilai > 0:
                akun_debit = AkunCOA.query.get(a.akun_id)
                akun_kredit = AkunCOA.query.get(sumber_id)
                if akun_debit and akun_kredit:
                    prefix = f"JU-PB/{tgl.year if tgl else date.today().year}/{tgl.month if tgl else date.today().month:02d}/"
                    count = JurnalUmum.query.filter(JurnalUmum.no_jurnal.like(f'{prefix}%')).count() + 1
                    no_jurnal = f"{prefix}{count:04d}"
                    j = JurnalUmum(
                        no_jurnal=no_jurnal, tanggal=tgl or date.today(),
                        keterangan=f"Pembelian {a.nama}",
                        referensi=a.kode_aset, tipe='pembelian_aset',
                        status='posted',
                        total_debit=nilai, total_kredit=nilai,
                        created_by=current_user.id,
                    )
                    db.session.add(j); db.session.flush()
                    db.session.add(JurnalDetail(
                        jurnal_id=j.id, akun_id=akun_debit.id,
                        keterangan=f"Pembelian {a.nama}", debit=nilai, kredit=0,
                    ))
                    db.session.add(JurnalDetail(
                        jurnal_id=j.id, akun_id=akun_kredit.id,
                        keterangan=f"Pembelian {a.nama}", debit=0, kredit=nilai,
                    ))

            db.session.commit()
            flash(f'Aset "{a.nama}" ditambahkan.','success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal menyimpan aset: {e}','danger')
        return redirect(url_for('akuntansi.aset_index'))
    return render_template('akuntansi/aset_form.html', aset=None, akun_list=akun_list,
                           akun_sumber=akun_sumber, kategori_list=KATEGORI_LIST,
                           kategori_akun_map=KATEGORI_KE_AKUN, default_sumber_id=default_sumber_id)


@akuntansi_bp.route('/aset/edit/<int:id>', methods=['GET','POST'])
@login_required
def aset_edit(id):
    if not current_user.can_edit_delete(): abort(403)
    a=Aset.query.get_or_404(id)
    akun_list=AkunCOA.query.filter(AkunCOA.golongan==1,AkunCOA.aktif==True).order_by(AkunCOA.kode).all()
    if request.method=='POST':
        def num(v): return int(''.join(c for c in str(v) if c.isdigit()) or '0')
        try: a.tanggal_perolehan=datetime.strptime(request.form.get('tanggal_perolehan',''),'%Y-%m-%d').date()
        except (ValueError, TypeError): pass
        a.nama=request.form.get('nama',a.nama); a.kategori=request.form.get('kategori',a.kategori)
        a.nilai_perolehan=num(request.form.get('nilai_perolehan',a.nilai_perolehan))
        a.akumulasi_penyusutan=num(request.form.get('akumulasi_penyusutan',a.akumulasi_penyusutan))
        a.nilai_buku=a.nilai_perolehan-a.akumulasi_penyusutan
        a.lokasi=request.form.get('lokasi',''); a.kondisi=request.form.get('kondisi','baik')
        a.keterangan=request.form.get('keterangan',''); a.akun_id=request.form.get('akun_id') or None
        a.aktif='aktif' in request.form
        db.session.commit(); flash('Aset diperbarui.','success')
        return redirect(url_for('akuntansi.aset_index'))
    return render_template('akuntansi/aset_form.html', aset=a, akun_list=akun_list, kategori_list=KATEGORI_LIST)


@akuntansi_bp.route('/aset/hapus/<int:id>', methods=['POST'])
@login_required
def aset_hapus(id):
    if not current_user.is_admin():
        abort(403)
    a = Aset.query.get_or_404(id)
    nama_aset = a.nama
    try:
        from ..models import AsetMutasi, OpnameAset
        AsetMutasi.query.filter_by(aset_id=a.id).delete()
        OpnameAset.query.filter_by(aset_id=a.id).delete()
        if a.kode_aset:
            jurnal = JurnalUmum.query.filter_by(referensi=a.kode_aset, tipe='pembelian_aset').first()
            if jurnal:
                JurnalDetail.query.filter_by(jurnal_id=jurnal.id).delete()
                db.session.delete(jurnal)
        db.session.delete(a)
        db.session.commit()
        flash(f'Aset "{nama_aset}" berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus aset: {e}', 'danger')
    return redirect(url_for('akuntansi.aset_index'))


# ── PENYUSUTAN ASET ──────────────────────────────────────────
@akuntansi_bp.route('/aset/penyusutan')
@login_required
def aset_penyusutan():
    """Hitung & tampilkan penyusutan per aset."""
    aset_list = Aset.query.filter(Aset.aktif==True, Aset.umur_ekonomis>0).order_by(Aset.kategori, Aset.nama).all()
    for a in aset_list:
        a.penyusutan_tahunan = a.nilai_perolehan // a.umur_ekonomis if a.umur_ekonomis > 0 else 0
        a.penyusutan_bulanan = a.penyusutan_tahunan // 12

    total_perolehan = sum(a.nilai_perolehan for a in aset_list)
    total_akumulasi = sum(a.akumulasi_penyusutan for a in aset_list)
    total_buku = sum(a.nilai_buku for a in aset_list)

    # Group by kategori
    dari_kat = {}
    for a in aset_list:
        kat = a.kategori or 'Lainnya'
        if kat not in dari_kat:
            dari_kat[kat] = {'aset': [], 'total_perolehan': 0, 'total_akumulasi': 0, 'total_buku': 0}
        dari_kat[kat]['aset'].append(a)
        dari_kat[kat]['total_perolehan'] += a.nilai_perolehan
        dari_kat[kat]['total_akumulasi'] += a.akumulasi_penyusutan
        dari_kat[kat]['total_buku'] += a.nilai_buku

    return render_template('akuntansi/penyusutan.html',
                           aset_list=aset_list,
                           dari_kat=dari_kat,
                           total_perolehan=total_perolehan,
                           total_akumulasi=total_akumulasi,
                           total_buku=total_buku,
                           today_str=date.today().strftime('%Y-%m-%d'))


@akuntansi_bp.route('/aset/penyusutan/jurnal', methods=['POST'])
@login_required
def aset_penyusutan_jurnal():
    """Buat jurnal penyusutan otomatis."""
    if current_user.role not in ('admin','keuangan'): abort(403)
    bulan = request.form.get('bulan', date.today().strftime('%Y-%m'))
    try:
        tgl = datetime.strptime(f"{bulan}-01", '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Format bulan tidak valid.', 'danger')
        return redirect(url_for('akuntansi.aset_penyusutan'))

    from ..models import JurnalUmum, JurnalDetail
    aset_list = Aset.query.filter(Aset.aktif==True, Aset.umur_ekonomis>0).all()
    if not aset_list:
        flash('Tidak ada aset yang disusutkan.', 'warning')
        return redirect(url_for('akuntansi.aset_penyusutan'))

    total_penyusutan = 0
    baris = []
    for a in aset_list:
        peny_bulanan = (a.nilai_perolehan // a.umur_ekonomis) // 12 if a.umur_ekonomis > 0 else 0
        if peny_bulanan > 0:
            total_penyusutan += peny_bulanan
            baris.append((a, peny_bulanan))

    if total_penyusutan == 0:
        flash('Tidak ada penyusutan yang perlu dicatat.', 'warning')
        return redirect(url_for('akuntansi.aset_penyusutan'))

    # Cek apakah sudah ada jurnal penyusutan untuk bulan ini
    existing = JurnalUmum.query.filter(
        JurnalUmum.tipe == 'penyusutan',
        JurnalUmum.tanggal >= tgl.replace(day=1),
        JurnalUmum.tanggal <= date(tgl.year, 12, 31) if tgl.month == 12 else JurnalUmum.tanggal <= (tgl.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    ).first()
    if existing:
        flash('Jurnal penyusutan bulan ini sudah ada.', 'warning')
        return redirect(url_for('akuntansi.aset_penyusutan'))

    no_jurnal = f"JU-PS/{tgl.year}/{tgl.month:02d}/0001"

    j = JurnalUmum(
        no_jurnal=no_jurnal,
        tanggal=tgl,
        keterangan=f"Penyusutan aset bulan {tgl.strftime('%B %Y')}",
        referensi=f"PS-{tgl.strftime('%Y%m')}",
        tipe='penyusutan',
        status='posted',
        total_debit=total_penyusutan,
        total_kredit=total_penyusutan,
        created_by=current_user.id,
    )
    db.session.add(j)
    db.session.flush()

    for a, peny in baris:
        if peny > 0:
            pair = KATEGORI_DEPR.get(a.kategori)
            if pair:
                akun_akum = AkunCOA.query.filter_by(kode=pair[0]).first()
                akun_beban = AkunCOA.query.filter_by(kode=pair[1]).first()
                if akun_akum and akun_beban:
                    db.session.add(JurnalDetail(
                        jurnal_id=j.id, akun_id=akun_beban.id,
                        keterangan=f"Penyusutan {a.kode_aset} — {a.nama}",
                        debit=peny, kredit=0,
                    ))
                    db.session.add(JurnalDetail(
                        jurnal_id=j.id, akun_id=akun_akum.id,
                        keterangan=f"Penyusutan {a.kode_aset} — {a.nama}",
                        debit=0, kredit=peny,
                    ))
        a.akumulasi_penyusutan = (a.akumulasi_penyusutan or 0) + peny
        a.nilai_buku = a.nilai_perolehan - a.akumulasi_penyusutan
        db.session.add(a)

    db.session.commit()
    flash(f'Jurnal penyusutan bulan {tgl.strftime("%B %Y")} berhasil dicatat. Total: Rp {total_penyusutan:,}', 'success')
    return redirect(url_for('akuntansi.aset_penyusutan'))


# ── MUTASI ASET ──────────────────────────────────────────────
@akuntansi_bp.route('/aset/mutasi')
@login_required
def aset_mutasi():
    """Daftar mutasi/perpindahan aset."""
    list_mutasi = AsetMutasi.query.order_by(AsetMutasi.tanggal.desc()).all()
    aset_list = Aset.query.filter_by(aktif=True).order_by(Aset.kode_aset).all()
    return render_template('akuntansi/mutasi_aset.html',
                           list_mutasi=list_mutasi, aset_list=aset_list,
                           today_str=date.today().strftime('%Y-%m-%d'))


@akuntansi_bp.route('/aset/mutasi/tambah', methods=['POST'])
@login_required
def aset_mutasi_tambah():
    """Catat mutasi aset."""
    if current_user.role not in ('admin','keuangan'): abort(403)
    aset_id = request.form.get('aset_id', type=int)
    aset = Aset.query.get_or_404(aset_id)
    try:
        tgl = datetime.strptime(request.form.get('tanggal',''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        tgl = date.today()

    m = AsetMutasi(
        aset_id=aset_id,
        tanggal=tgl,
        tipe=request.form.get('tipe','pindah'),
        dari_lokasi=aset.lokasi,
        ke_lokasi=request.form.get('ke_lokasi',''),
        keterangan=request.form.get('keterangan',''),
        created_by=current_user.id,
    )
    if m.ke_lokasi:
        aset.lokasi = m.ke_lokasi
    if m.tipe == 'hapus':
        aset.aktif = False
    db.session.add(m)
    db.session.commit()
    flash('Mutasi aset berhasil dicatat.', 'success')
    return redirect(url_for('akuntansi.aset_mutasi'))


# ── OPNAME ASET ──────────────────────────────────────────────
@akuntansi_bp.route('/aset/opname', methods=['GET','POST'])
@login_required
def aset_opname():
    """Stock opname — pencocokan fisik vs catatan."""
    aset_list = Aset.query.filter_by(aktif=True).order_by(Aset.kategori, Aset.kode_aset).all()
    if request.method == 'POST':
        from datetime import datetime as dt
        try:
            tgl_opname = datetime.strptime(request.form.get('tanggal_opname',''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            tgl_opname = date.today()

        for a in aset_list:
            fisik = request.form.get(f'fisik_{a.id}', 'ada')
            kondisi_fisik = request.form.get(f'kondisi_{a.id}', a.kondisi)
            catatan = request.form.get(f'catatan_{a.id}', '')
            status = 'sesuai'
            if fisik == 'ada' and kondisi_fisik != a.kondisi:
                status = 'kondisi_berubah'
            elif fisik == 'tidak_ada':
                status = 'hilang'
                a.aktif = False

            op = OpnameAset(
                aset_id=a.id,
                tanggal_opname=tgl_opname,
                kondisi_catatan=a.kondisi,
                kondisi_fisik=kondisi_fisik,
                status=status,
                catatan=catatan,
                created_by=current_user.id,
            )
            db.session.add(op)
            if kondisi_fisik != a.kondisi:
                a.kondisi = kondisi_fisik

        db.session.commit()
        flash(f'Opname aset tanggal {tgl_opname.strftime("%d/%m/%Y")} berhasil disimpan.', 'success')
        return redirect(url_for('akuntansi.aset_opname'))

    # History opname
    history = OpnameAset.query.order_by(OpnameAset.tanggal_opname.desc()).all()
    return render_template('akuntansi/opname_aset.html',
                           aset_list=aset_list, history=history,
                           today_str=date.today().strftime('%Y-%m-%d'))


# ── LAPORAN ASET ─────────────────────────────────────────────
@akuntansi_bp.route('/aset/laporan')
@login_required
def aset_laporan():
    """Ringkasan & laporan aset tetap."""
    aset_list = Aset.query.order_by(Aset.kategori, Aset.nama).all()
    kategori_list = sorted(set(a.kategori for a in aset_list if a.kategori) | {'Lainnya'})
    dari_kat = {}
    grand_total_perolehan = 0
    grand_total_akumulasi = 0
    grand_total_buku = 0

    for kat in kategori_list:
        aset_kat = [a for a in aset_list if (a.kategori or 'Lainnya') == kat]
        total_p = sum(a.nilai_perolehan for a in aset_kat)
        total_a = sum(a.akumulasi_penyusutan for a in aset_kat)
        total_b = sum(a.nilai_buku for a in aset_kat)
        dari_kat[kat] = {'aset': aset_kat, 'total_perolehan': total_p, 'total_akumulasi': total_a, 'total_buku': total_b}
        grand_total_perolehan += total_p
        grand_total_akumulasi += total_a
        grand_total_buku += total_b

    return render_template('akuntansi/laporan_aset.html',
                           dari_kat=dari_kat,
                           grand_total_perolehan=grand_total_perolehan,
                           grand_total_akumulasi=grand_total_akumulasi,
                           grand_total_buku=grand_total_buku,
                           aset_list=aset_list)


# ── SALDO AWAL JURNAL ────────────────────────────────────────
@akuntansi_bp.route('/saldo-awal', methods=['GET','POST'])
@login_required
def saldo_awal():
    if current_user.role not in ('admin','keuangan'): abort(403)
    from sqlalchemy import text
    if request.method=='POST':
        try: tgl=datetime.strptime(request.form.get('tanggal',''),'%Y-%m-%d').date()
        except (ValueError, TypeError): tgl=date.today().replace(month=1,day=1)
        
        from ..models import SaldoAwal
        akun_ids = request.form.getlist('akun_id[]')
        debits   = request.form.getlist('debit[]')
        kredits  = request.form.getlist('kredit[]')
        kets     = request.form.getlist('keterangan[]')
        
        def num(v): return int(''.join(c for c in str(v) if c.isdigit()) or '0')
        saved=0
        for i,aid in enumerate(akun_ids):
            if not aid: continue
            d = num(debits[i] if i<len(debits) else '0')
            k = num(kredits[i] if i<len(kredits) else '0')
            ket = kets[i] if (i<len(kets) and kets[i]) else 'Saldo Awal'
            if d==0 and k==0: continue
            
            sa = SaldoAwal(
                akun_id=int(aid), tanggal=tgl, debit=d, kredit=k,
                keterangan=ket, created_by=current_user.id
            )
            db.session.add(sa)
            saved+=1
        db.session.commit()
        flash(f'{saved} saldo awal disimpan.','success')
        return redirect(url_for('akuntansi.saldo_awal'))
    
    akun_list=AkunCOA.query.filter_by(bisa_jurnal=True,aktif=True).order_by(AkunCOA.kode).all()
    from ..models import SaldoAwal
    try:
        existing = db.session.query(
            AkunCOA.kode, AkunCOA.nama, 
            func.sum(SaldoAwal.debit).label('d'), 
            func.sum(SaldoAwal.kredit).label('k')
        ).join(SaldoAwal).group_by(AkunCOA.kode, AkunCOA.nama).order_by(AkunCOA.kode).all()
    except Exception: existing=[]
    return render_template('akuntansi/saldo_awal.html',
        akun_list=akun_list, existing=existing,
        today_str=date.today().replace(month=1,day=1).strftime('%Y-%m-%d'))
