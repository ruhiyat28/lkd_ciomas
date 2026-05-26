from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ..models import db, Nasabah, JaminanBPKB, JaminanSHM, JaminanLain, Pinjaman
from config import Config
from ..utils.helpers import save_file

jaminan_bp = Blueprint('jaminan', __name__)


# ── Index: tampilkan HANYA nasabah yang sudah ada jaminannya ─
@jaminan_bp.route('/')
@login_required
def index():
    search      = request.args.get('q','')
    desa_filter = request.args.get('desa','')
    page        = request.args.get('page',1,type=int)

    # Nasabah yang sudah punya minimal 1 jaminan (any type)
    from sqlalchemy import or_, exists
    has_jaminan = or_(
        exists().where(JaminanBPKB.nasabah_id == Nasabah.id),
        exists().where(JaminanSHM.nasabah_id  == Nasabah.id),
        exists().where(JaminanLain.nasabah_id == Nasabah.id),
    )
    q = Nasabah.query.filter(has_jaminan)
    if desa_filter: q = q.filter(Nasabah.kode_desa == desa_filter)
    if search:
        q = q.filter(
            Nasabah.nama.ilike(f'%{search}%') |
            Nasabah.nasabah_id.ilike(f'%{search}%')
        )
    nasabah_list = q.order_by(Nasabah.nasabah_id).paginate(page=page, per_page=20)

    total_bpkb = JaminanBPKB.query.count()
    total_shm  = JaminanSHM.query.count()
    total_lain = JaminanLain.query.count()
    total_jaminan = total_bpkb + total_shm + total_lain

    return render_template('jaminan/index.html',
        nasabah_list=nasabah_list, search=search,
        desa_filter=desa_filter, desa_list=Config.DESA_LIST,
        total_jaminan=total_jaminan, total_bpkb=total_bpkb,
        total_shm=total_shm, total_lain=total_lain)


# ── Cari nasabah untuk posting jaminan (belum ada jaminan) ──
@jaminan_bp.route('/cari')
@login_required
def cari():
    search = request.args.get('q','')
    desa_filter = request.args.get('desa','')
    results = []
    if search or desa_filter:
        q = Nasabah.query
        if desa_filter: q = q.filter(Nasabah.kode_desa == desa_filter)
        if search:
            q = q.filter(
                Nasabah.nama.ilike(f'%{search}%') |
                Nasabah.nasabah_id.ilike(f'%{search}%')
            )
        results = q.order_by(Nasabah.nasabah_id).limit(30).all()
    return render_template('jaminan/cari.html',
        results=results, search=search,
        desa_filter=desa_filter, desa_list=Config.DESA_LIST)


# ── Detail jaminan nasabah (3 tab) ──────────────────────────
@jaminan_bp.route('/nasabah/<int:nasabah_id>')
@login_required
def detail(nasabah_id):
    nasabah  = Nasabah.query.get_or_404(nasabah_id)
    pinjaman = Pinjaman.query.filter_by(nasabah_id_fk=nasabah_id).order_by(Pinjaman.id.desc()).all()
    return render_template('jaminan/detail.html',
        nasabah=nasabah, pinjaman=pinjaman,
        tab=request.args.get('tab','bpkb'))


# ── BPKB Tambah ─────────────────────────────────────────────
@jaminan_bp.route('/bpkb/tambah/<int:nasabah_id>', methods=['GET','POST'])
@login_required
def bpkb_tambah(nasabah_id):
    if not current_user.can_write_nasabah(): abort(403)
    nasabah  = Nasabah.query.get_or_404(nasabah_id)
    pinjaman = Pinjaman.query.filter_by(nasabah_id_fk=nasabah_id).filter(
        Pinjaman.status.in_(['cair','acc_direktur'])).order_by(Pinjaman.id.desc()).all()
    if request.method == 'POST':
        kep = request.form.get('kepemilikan','milik_sendiri')
        if kep=='milik_sendiri':
            nama_pemilik=nasabah.nama; alamat_pemilik=nasabah.alamat or ''
        else:
            nama_pemilik=request.form.get('nama_pemilik','').upper()
            alamat_pemilik=request.form.get('alamat_pemilik','')
        surat_kuasa = save_file(request.files.get('surat_kuasa'),'jaminan_docs',
                                f"sk_{nasabah.nasabah_id}") if kep=='milik_orang_lain' else None
        try: tahun=int(request.form.get('tahun_pembuatan') or 0) or None
        except (ValueError, TypeError): tahun=None
        j = JaminanBPKB(
            nasabah_id=nasabah_id, kepemilikan=kep, surat_kuasa=surat_kuasa,
            nama_pemilik=nama_pemilik, alamat_pemilik=alamat_pemilik,
            jenis_kendaraan=request.form.get('jenis_kendaraan',''),
            merk=request.form.get('merk','').upper(), tipe=request.form.get('tipe','').upper(),
            nomor_polisi=request.form.get('nomor_polisi','').upper(),
            nomor_rangka=request.form.get('nomor_rangka','').upper(),
            nomor_mesin=request.form.get('nomor_mesin','').upper(),
            tahun_pembuatan=tahun,
            pinjaman_id=request.form.get('pinjaman_id') or None,
            keterangan=request.form.get('keterangan',''), created_by=current_user.id,
        )
        db.session.add(j); db.session.commit()
        flash(f'Jaminan BPKB {j.merk} {j.nomor_polisi} tersimpan.','success')
        return redirect(url_for('jaminan.detail', nasabah_id=nasabah_id, tab='bpkb'))
    return render_template('jaminan/form_bpkb.html', nasabah=nasabah, pinjaman=pinjaman, jaminan=None)


@jaminan_bp.route('/bpkb/edit/<int:id>', methods=['GET','POST'])
@login_required
def bpkb_edit(id):
    if not current_user.can_edit_delete(): abort(403)
    j=JaminanBPKB.query.get_or_404(id); nasabah=j.nasabah
    pinjaman=Pinjaman.query.filter_by(nasabah_id_fk=nasabah.id).order_by(Pinjaman.id.desc()).all()
    if request.method=='POST':
        j.kepemilikan=request.form.get('kepemilikan','milik_sendiri')
        if j.kepemilikan=='milik_sendiri':
            j.nama_pemilik=nasabah.nama; j.alamat_pemilik=nasabah.alamat or ''
        else:
            j.nama_pemilik=request.form.get('nama_pemilik','').upper()
            j.alamat_pemilik=request.form.get('alamat_pemilik','')
            from ..utils.helpers import save_file; nsk=save_file(request.files.get('surat_kuasa'),'jaminan_docs',f"sk_{nasabah.nasabah_id}")
            if nsk: j.surat_kuasa=nsk
        j.jenis_kendaraan=request.form.get('jenis_kendaraan','')
        j.merk=request.form.get('merk','').upper(); j.tipe=request.form.get('tipe','').upper()
        j.nomor_polisi=request.form.get('nomor_polisi','').upper()
        j.nomor_rangka=request.form.get('nomor_rangka','').upper()
        j.nomor_mesin=request.form.get('nomor_mesin','').upper()
        try: j.tahun_pembuatan=int(request.form.get('tahun_pembuatan') or 0) or None
        except (ValueError, TypeError): pass
        j.pinjaman_id=request.form.get('pinjaman_id') or None
        j.keterangan=request.form.get('keterangan','')
        db.session.commit(); flash('Jaminan BPKB diperbarui.','success')
        return redirect(url_for('jaminan.detail', nasabah_id=nasabah.id, tab='bpkb'))
    return render_template('jaminan/form_bpkb.html', nasabah=nasabah, pinjaman=pinjaman, jaminan=j)


@jaminan_bp.route('/bpkb/hapus/<int:id>', methods=['POST'])
@login_required
def bpkb_hapus(id):
    if not current_user.can_edit_delete(): abort(403)
    j=JaminanBPKB.query.get_or_404(id); nid=j.nasabah_id
    db.session.delete(j); db.session.commit(); flash("Jaminan BPKB berhasil dihapus.", "success")
    return redirect(url_for('jaminan.detail', nasabah_id=nid, tab='bpkb'))


# ── SHM ─────────────────────────────────────────────────────
@jaminan_bp.route('/shm/tambah/<int:nasabah_id>', methods=['GET','POST'])
@login_required
def shm_tambah(nasabah_id):
    if not current_user.can_write_nasabah(): abort(403)
    nasabah=Nasabah.query.get_or_404(nasabah_id)
    pinjaman=Pinjaman.query.filter_by(nasabah_id_fk=nasabah_id).filter(
        Pinjaman.status.in_(['cair','acc_direktur'])).order_by(Pinjaman.id.desc()).all()
    if request.method=='POST':
        try: tahun=int(request.form.get('tahun_penerbitan') or 0) or None
        except (ValueError, TypeError): tahun=None
        j=JaminanSHM(
            nasabah_id=nasabah_id,
            nama_pemilik=request.form.get('nama_pemilik','').upper(),
            alamat_pemilik=request.form.get('alamat_pemilik',''),
            lokasi_lahan=request.form.get('lokasi_lahan',''),
            luas_lahan=request.form.get('luas_lahan',''),
            nib=request.form.get('nib','').upper(),
            tahun_penerbitan=tahun,
            pinjaman_id=request.form.get('pinjaman_id') or None,
            keterangan=request.form.get('keterangan',''), created_by=current_user.id,
        )
        db.session.add(j); db.session.commit()
        flash(f'Jaminan SHM NIB {j.nib} tersimpan.','success')
        return redirect(url_for('jaminan.detail', nasabah_id=nasabah_id, tab='shm'))
    return render_template('jaminan/form_shm.html', nasabah=nasabah, pinjaman=pinjaman, jaminan=None)


@jaminan_bp.route('/shm/edit/<int:id>', methods=['GET','POST'])
@login_required
def shm_edit(id):
    if not current_user.can_edit_delete(): abort(403)
    j=JaminanSHM.query.get_or_404(id)
    pinjaman=Pinjaman.query.filter_by(nasabah_id_fk=j.nasabah_id).order_by(Pinjaman.id.desc()).all()
    if request.method=='POST':
        j.nama_pemilik=request.form.get('nama_pemilik','').upper()
        j.alamat_pemilik=request.form.get('alamat_pemilik','')
        j.lokasi_lahan=request.form.get('lokasi_lahan','')
        j.luas_lahan=request.form.get('luas_lahan','')
        j.nib=request.form.get('nib','').upper()
        try: j.tahun_penerbitan=int(request.form.get('tahun_penerbitan') or 0) or None
        except (ValueError, TypeError): pass
        j.pinjaman_id=request.form.get('pinjaman_id') or None
        j.keterangan=request.form.get('keterangan','')
        db.session.commit(); flash('Jaminan SHM diperbarui.','success')
        return redirect(url_for('jaminan.detail', nasabah_id=j.nasabah_id, tab='shm'))
    return render_template('jaminan/form_shm.html', nasabah=j.nasabah, pinjaman=pinjaman, jaminan=j)


@jaminan_bp.route('/shm/hapus/<int:id>', methods=['POST'])
@login_required
def shm_hapus(id):
    if not current_user.can_edit_delete(): abort(403)
    j=JaminanSHM.query.get_or_404(id); nid=j.nasabah_id
    db.session.delete(j); db.session.commit(); flash("Jaminan SHM berhasil dihapus.", "success")
    return redirect(url_for('jaminan.detail', nasabah_id=nid, tab='shm'))


# ── Jaminan Lain ─────────────────────────────────────────────
@jaminan_bp.route('/lain/tambah/<int:nasabah_id>', methods=['GET','POST'])
@login_required
def lain_tambah(nasabah_id):
    if not current_user.can_write_nasabah(): abort(403)
    nasabah=Nasabah.query.get_or_404(nasabah_id)
    pinjaman=Pinjaman.query.filter_by(nasabah_id_fk=nasabah_id).filter(
        Pinjaman.status.in_(['cair','acc_direktur'])).order_by(Pinjaman.id.desc()).all()
    if request.method=='POST':
        j=JaminanLain(
            nasabah_id=nasabah_id,
            jenis_jaminan=request.form.get('jenis_jaminan',''),
            nomor_jaminan=request.form.get('nomor_jaminan','').upper(),
            nama_pemilik=request.form.get('nama_pemilik','').upper(),
            alamat_pemilik=request.form.get('alamat_pemilik',''),
            keterangan=request.form.get('keterangan',''),
            pinjaman_id=request.form.get('pinjaman_id') or None,
            created_by=current_user.id,
        )
        db.session.add(j); db.session.commit()
        flash(f'Jaminan {j.jenis_jaminan} tersimpan.','success')
        return redirect(url_for('jaminan.detail', nasabah_id=nasabah_id, tab='lain'))
    return render_template('jaminan/form_lain.html', nasabah=nasabah, pinjaman=pinjaman, jaminan=None)


@jaminan_bp.route('/lain/edit/<int:id>', methods=['GET','POST'])
@login_required
def lain_edit(id):
    if not current_user.can_edit_delete(): abort(403)
    j=JaminanLain.query.get_or_404(id)
    pinjaman=Pinjaman.query.filter_by(nasabah_id_fk=j.nasabah_id).order_by(Pinjaman.id.desc()).all()
    if request.method=='POST':
        j.jenis_jaminan=request.form.get('jenis_jaminan','')
        j.nomor_jaminan=request.form.get('nomor_jaminan','').upper()
        j.nama_pemilik=request.form.get('nama_pemilik','').upper()
        j.alamat_pemilik=request.form.get('alamat_pemilik','')
        j.keterangan=request.form.get('keterangan','')
        j.pinjaman_id=request.form.get('pinjaman_id') or None
        db.session.commit(); flash('Jaminan diperbarui.','success')
        return redirect(url_for('jaminan.detail', nasabah_id=j.nasabah_id, tab='lain'))
    return render_template('jaminan/form_lain.html', nasabah=j.nasabah, pinjaman=pinjaman, jaminan=j)


@jaminan_bp.route('/lain/hapus/<int:id>', methods=['POST'])
@login_required
def lain_hapus(id):
    if not current_user.can_edit_delete(): abort(403)
    j=JaminanLain.query.get_or_404(id); nid=j.nasabah_id
    db.session.delete(j); db.session.commit(); flash("Jaminan lain berhasil dihapus.", "success")
    return redirect(url_for('jaminan.detail', nasabah_id=nid, tab='lain'))
