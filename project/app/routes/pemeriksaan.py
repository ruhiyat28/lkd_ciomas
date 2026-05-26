from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, exists, func
from ..models import db, Pinjaman, PemeriksaanDokumen, Nasabah, User
from config import Config
from datetime import date, datetime, timezone

pemeriksaan_bp = Blueprint('pemeriksaan', __name__)

ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']

def generate_nomor_surat():
    tahun = date.today().year
    max_urut = db.session.query(func.max(PemeriksaanDokumen.nomor_urut)).filter(
        func.extract('year', PemeriksaanDokumen.created_at) == tahun
    ).scalar() or 0
    no_urut = max_urut + 1
    nomor = f"{no_urut:04d}/PP/BB-LKD/{ROMAN[date.today().month]}/{tahun}"
    return no_urut, nomor


@pemeriksaan_bp.route('/')
@login_required
def index():
    desa_filter = request.args.get('desa', '')
    q = db.session.query(Pinjaman).join(Nasabah).filter(
        or_(
            Pinjaman.status == 'pengajuan',
            exists().where(PemeriksaanDokumen.pinjaman_id == Pinjaman.id)
        )
    )
    if current_user.is_kader():
        desa_filter = current_user.kode_desa
        q = q.filter(Nasabah.kode_desa == desa_filter)
    elif desa_filter:
        q = q.filter(Nasabah.kode_desa == desa_filter)
    pinjaman_list = q.order_by(Pinjaman.id.desc()).all()

    total_pengajuan     = Pinjaman.query.filter(Pinjaman.status == 'pengajuan').count()
    total_sudah_periksa = PemeriksaanDokumen.query.count()
    total_layak         = PemeriksaanDokumen.query.filter_by(hasil='layak').count()
    total_tidak_layak   = PemeriksaanDokumen.query.filter_by(hasil='tidak_layak').count()

    return render_template('pemeriksaan/index.html',
        pinjaman_list=pinjaman_list, desa_filter=desa_filter,
        desa_list=Config.DESA_LIST,
        total_pengajuan=total_pengajuan,
        total_sudah_periksa=total_sudah_periksa,
        total_layak=total_layak, total_tidak_layak=total_tidak_layak)


@pemeriksaan_bp.route('/<int:pinjaman_id>', methods=['GET', 'POST'])
@login_required
def form(pinjaman_id):
    p = db.get_or_404(Pinjaman, pinjaman_id)
    if current_user.is_kader() and p.nasabah.kode_desa != current_user.kode_desa:
        abort(403)
    existing = PemeriksaanDokumen.query.filter_by(pinjaman_id=p.id).first()
    if p.status != 'pengajuan' and not existing:
        flash('Pengajuan ini sudah diproses.', 'warning')
        return redirect(url_for('pinjaman.detail', id=p.id))

    if request.method == 'POST':
        catatan = request.form.get('catatan_pemeriksa', '')
        hasil   = request.form.get('hasil', 'layak')

        if existing:
            periksa = existing
        else:
            periksa = PemeriksaanDokumen(pinjaman_id=p.id)
            db.session.add(periksa)

        periksa.pemeriksa_id        = current_user.id
        periksa.tanggal_pemeriksaan = date.today()
        periksa.catatan_pemeriksa   = catatan
        periksa.nama_verifikator    = request.form.get('nama_verifikator', '')
        periksa.hasil               = hasil

        if not periksa.nomor_surat:
            no_urut, nomor = generate_nomor_surat()
            periksa.nomor_urut = no_urut
            periksa.nomor_surat = nomor

        if p.jenis_pinjaman == 'spp':
            periksa.surat_tanggung_renteng_valid = request.form.get('surat_tanggung_renteng_valid') == '1'
            periksa.surat_ijin_keluarga_valid    = request.form.get('surat_ijin_keluarga_valid') == '1'
        else:
            periksa.foto_valid              = request.form.get('foto_valid') == '1'
            periksa.ktp_valid               = request.form.get('ktp_valid') == '1'
            periksa.kk_valid                = request.form.get('kk_valid') == '1'
            periksa.surat_usaha_valid       = request.form.get('surat_usaha_valid') == '1'
            periksa.bukti_penghasilan_valid = request.form.get('bukti_penghasilan_valid') == '1'
            periksa.jaminan_valid           = request.form.get('jaminan_valid') == '1'

        if hasil == 'layak':
            p.status = 'cek_dokumen'
        else:
            if p.status != 'ditolak':
                p.jumlah_penolakan = (p.jumlah_penolakan or 0) + 1
            p.status = 'ditolak'
            p.catatan_direktur = catatan

        db.session.commit()
        flash('Hasil pemeriksaan dokumen disimpan.', 'success')
        return redirect(url_for('pemeriksaan.form', pinjaman_id=p.id))

    user_map = {u.id: u.nama_lengkap for u in db.session.query(User).all()}
    return render_template('pemeriksaan/form.html', p=p, existing=existing,
        user_map=user_map, today=date.today())


@pemeriksaan_bp.route('/<int:pinjaman_id>/cetak')
@login_required
def cetak(pinjaman_id):
    p = db.get_or_404(Pinjaman, pinjaman_id)
    periksa = PemeriksaanDokumen.query.filter_by(pinjaman_id=p.id).first()
    pemeriksa = db.session.get(User, periksa.pemeriksa_id) if periksa else None
    return render_template('print/pemeriksaan_dokumen.html', p=p, periksa=periksa,
        pemeriksa=pemeriksa, back_url=url_for('pinjaman.detail', id=p.id), today=date.today())


@pemeriksaan_bp.route('/<int:pinjaman_id>/cetak/spv')
@login_required
def cetak_spv(pinjaman_id):
    p = db.get_or_404(Pinjaman, pinjaman_id)
    periksa = PemeriksaanDokumen.query.filter_by(pinjaman_id=p.id).first()
    if not periksa or periksa.hasil != 'layak':
        abort(404)
    return render_template('print/surat_perintah_verifikasi.html', p=p,
        periksa=periksa, today=date.today())
