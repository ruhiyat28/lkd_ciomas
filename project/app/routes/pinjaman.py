from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from ..models import db, Pinjaman, Nasabah, Pembayaran, RekeningTabungan, DetailSPP, AnggotaKelompok, User
from ..utils.auto_jurnal import jurnal_pencairan
from config import Config
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from werkzeug.utils import secure_filename
import os, logging
from ..utils.helpers import save_file

logger = logging.getLogger(__name__)

pinjaman_bp = Blueprint('pinjaman', __name__)


def generate_spk():
    year  = date.today().year
    # Use efficient MAX query instead of loading all records
    from sqlalchemy import func

    try:
        max_result = db.session.query(
            func.max(db.func.cast(
                db.func.substring(Pinjaman.spk, r'\d+$'),
                db.Integer
            ))
        ).filter(Pinjaman.spk.like(f'SPK-{year}-%')).scalar()
        next_num = (max_result or 0) + 1
    except Exception:
        # Fallback for SQLite
        existing = db.session.query(Pinjaman.spk).filter(Pinjaman.spk.like(f'SPK-{year}-%')).all()
        nums = []
        for (spk,) in existing:
            try:
                nums.append(int(spk.split('-')[-1]))
            except (ValueError, IndexError):
                pass
        next_num = max(nums) + 1 if nums else 1

    return Config.format_spk(year, next_num)


STATUS_LABELS = {
    'pengajuan':'Pengajuan','cek_dokumen':'Cek Dokumen',
    'verifikasi':'Verifikasi Lapangan','acc_direktur':'Menunggu ACC',
    'cair':'Aktif','lunas':'Lunas','ditolak':'Ditolak'
}


@pinjaman_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status','')
    desa_filter   = request.args.get('desa','')
    jenis_filter  = request.args.get('jenis','')   # '' | 'kelompok' | 'mandiri'
    search        = request.args.get('q','')
    page          = request.args.get('page',1,type=int)

    q = db.session.query(Pinjaman).join(Nasabah)
    if current_user.is_kader():
        desa_filter = current_user.kode_desa
        q = q.filter(Nasabah.kode_desa == desa_filter)
    elif current_user.is_nasabah():
        q = q.filter(Nasabah.id == current_user.nasabah_id_fk)
    elif desa_filter:
        q = q.filter(Nasabah.kode_desa == desa_filter)
    
    if status_filter: q = q.filter(Pinjaman.status == status_filter)
    if jenis_filter:  q = q.filter(Nasabah.jenis == jenis_filter)
    if search:
        q = q.filter(Nasabah.nama.ilike(f'%{search}%') | Pinjaman.spk.ilike(f'%{search}%') | Nasabah.nasabah_id.ilike(f'%{search}%'))

    pinjaman_list = q.order_by(Pinjaman.id.desc()).paginate(page=page, per_page=20)
    
    if current_user.is_nasabah():
        # Jika nasabah, kita tampilkan view yang lebih personal (seperti detail)
        # Ambil pinjaman aktif terbaru atau daftar pinjaman mereka
        all_p = q.order_by(Pinjaman.id.desc()).all()
        
        # Helper data untuk detail view di template nasabah
        # (Sama seperti logika di detail() tapi untuk list/single view)
        data_p = []
        for p in all_p:
            tp_bayar, tj_bayar = p.get_realisasi_pembayaran()
            t_pokok, t_jasa, b_nunggak = p.get_tunggakan()
            k_val, k_lab = p.get_kolektibilitas()
            data_p.append({
                'p': p,
                'total_pokok_bayar': tp_bayar,
                'total_jasa_bayar': tj_bayar,
                'tunggak_pokok': t_pokok,
                'tunggak_jasa': t_jasa,
                'bulan_nunggak': b_nunggak,
                'kolek': k_val,
                'kolek_label': k_lab,
                'jadwal': p.get_jadwal_angsuran()
            })

        return render_template('pinjaman/index_nasabah.html', data_p=data_p)

    total_pinjaman  = Pinjaman.query.count()
    total_cair      = Pinjaman.query.filter_by(status='cair').count()
    total_lunas     = Pinjaman.query.filter_by(status='lunas').count()
    total_pengajuan = Pinjaman.query.filter(Pinjaman.status.in_(['pengajuan','cek_dokumen','verifikasi','acc_direktur'])).count()

    return render_template('pinjaman/index.html',
        pinjaman_list=pinjaman_list, status_filter=status_filter,
        jenis_filter=jenis_filter,
        desa_list=Config.DESA_LIST, desa_filter=desa_filter,
        search=search, STATUS_LABELS=STATUS_LABELS,
        total_pinjaman=total_pinjaman, total_cair=total_cair,
        total_lunas=total_lunas, total_pengajuan=total_pengajuan)


@pinjaman_bp.route('/cari-nasabah')
@login_required
def cari_nasabah():
    """API endpoint untuk autocomplete nasabah di form pinjaman."""
    q = request.args.get('q','').strip()
    if len(q) < 2:
        return jsonify([])
    query = db.session.query(Nasabah)
    if current_user.is_kader():
        query = query.filter_by(kode_desa=current_user.kode_desa)
    
    results = query.filter(
        Nasabah.nama.ilike(f'%{q}%') |
        Nasabah.nasabah_id.ilike(f'%{q}%') |
        Nasabah.nik.ilike(f'%{q}%')
    ).limit(10).all()
    return jsonify([{
        'id': n.id,
        'nasabah_id': n.nasabah_id,
        'nama': n.nama,
        'nik': n.nik or '',
        'desa': n.nama_desa,
        'jenis': n.jenis,
        'pekerjaan': n.pekerjaan or '',
        'dok_lengkap': n.dokumen_lengkap(),
    } for n in results])


@pinjaman_bp.route('/tambah', methods=['GET','POST'])
@login_required
def tambah():
    if not current_user.can_write_pinjaman() and not current_user.is_nasabah():
        abort(403)

    nasabah_id = current_user.nasabah_id_fk if current_user.is_nasabah() else (
        request.form.get('nasabah_id_fk') or request.args.get('nasabah_id')
    )
    if not nasabah_id:
        if current_user.is_nasabah():
            flash('Akun Anda belum terhubung dengan data nasabah.', 'warning')
            return redirect(url_for('main.dashboard'))
        return render_template('pinjaman/form_tambah.html', nasabah=None, tenor_options=Config.TENOR_OPTIONS)

    nasabah = db.get_or_404(Nasabah, nasabah_id)

    if current_user.is_kader() and nasabah.kode_desa != current_user.kode_desa:
        abort(403)

    def validate_nasabah_loan(n):
        aktif = db.session.query(Pinjaman).filter_by(nasabah_id_fk=n.id, status='cair').first()
        if aktif:
            return False, f'Nasabah {n.nama} masih memiliki pinjaman aktif (SPK: {aktif.spk}).'

        pending = db.session.query(Pinjaman).filter(
            Pinjaman.nasabah_id_fk == n.id,
            Pinjaman.status.in_(['pengajuan', 'cek_dokumen', 'verifikasi', 'acc_direktur'])
        ).first()
        if pending:
            return False, f'Nasabah {n.nama} masih memiliki pengajuan tertunda (SPK: {pending.spk}).'

        penolakan = db.session.query(Pinjaman).filter_by(nasabah_id_fk=n.id, status='ditolak').count()
        if penolakan >= 3:
            return False, f'Nasabah {n.nama} telah ditolak {penolakan} kali. Tidak dapat mengajukan pinjaman kembali.'

        return True, ""

    if request.method == 'POST':
        is_valid, msg = validate_nasabah_loan(nasabah)
        if not is_valid:
            flash(msg, 'danger' if 'aktif' in msg or 'ditolak' in msg else 'warning')
            return redirect(url_for('main.dashboard') if current_user.is_nasabah() else url_for('pinjaman.tambah', nasabah_id=nasabah.id))

        try:
            tujuan = request.form.get('tujuan', '').strip()
            if not tujuan:
                flash('Tujuan pinjaman harus diisi.', 'danger')
                return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))

            try: jasa_persen = float(request.form.get('jasa_persen', 1.5))
            except (ValueError, TypeError): jasa_persen = 1.5
            if jasa_persen < 0:
                flash('Persentase jasa tidak boleh negatif.', 'danger')
                return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))

            try: tenor = int(request.form.get('tenor', 12))
            except (ValueError, TypeError): tenor = 12
            if tenor < 3 or tenor > 120:
                flash('Tenor tidak valid (min 3, maks 120 bulan).', 'danger')
                return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))

            jenis_pinjaman = request.form.get('jenis_pinjaman', 'reguler')

            if jenis_pinjaman == 'spp':
                nama_list   = request.form.getlist('spp_nama[]')
                nik_list    = request.form.getlist('spp_nik[]')
                jumlah_list = request.form.getlist('spp_jumlah[]')
                ket_list    = request.form.getlist('spp_ket[]')
                nama_list_valid = [n for n in nama_list if n.strip()]
                if not nama_list_valid:
                    flash('Tidak ada anggota. Tambahkan minimal 1 anggota melalui menu Edit Kelompok sebelum mengajukan pinjaman SPP.', 'danger')
                    return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))
                jumlah = 0
                spp_details = []
                for i, nama_a in enumerate(nama_list):
                    nama_a = nama_a.strip().upper()
                    if not nama_a:
                        continue
                    try:
                        jml_a = int(jumlah_list[i]) if i < len(jumlah_list) else 0
                    except (ValueError, TypeError):
                        jml_a = 0
                    if jml_a <= 0:
                        flash(f'Jumlah pinjaman untuk anggota {nama_a} harus lebih dari 0.', 'danger')
                        return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))
                    jumlah += jml_a
                    spp_details.append({
                        'urut': i + 1,
                        'nama_anggota': nama_a,
                        'nik_anggota': nik_list[i].strip() if i < len(nik_list) else '',
                        'jumlah': jml_a,
                        'keterangan': ket_list[i].strip() if i < len(ket_list) else '',
                    })
                if jumlah < 3000000:
                    flash(f'Total pinjaman anggota minimal Rp 3.000.000 (saat ini Rp {jumlah:,}).', 'danger')
                    return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))
            else:
                try:
                    jumlah = int(request.form.get('jumlah_pinjaman', 0))
                except (ValueError, TypeError):
                    jumlah = 0
                if jumlah < 3000000:
                    flash('Jumlah pinjaman minimal Rp 3.000.000.', 'danger')
                    return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))

            p = Pinjaman(
                spk=generate_spk(),
                jenis_pinjaman=jenis_pinjaman,
                nasabah_id_fk=nasabah.id,
                jumlah_pinjaman=jumlah,
                jasa_persen=jasa_persen,
                tenor=tenor,
                tujuan=tujuan,
                tanggal_pengajuan=date.today(),
                status='pengajuan',
                created_by=current_user.id,
            )
            db.session.add(p)
            db.session.flush()

            if jenis_pinjaman == 'spp':
                for sd in spp_details:
                    db.session.add(DetailSPP(
                        pinjaman_id=p.id, **sd
                    ))
                p.surat_tanggung_renteng = save_file(request.files.get('surat_tanggung_renteng'), 'surat_tanggung_renteng', p.spk.replace('/', ''))
                p.surat_ijin_keluarga = save_file(request.files.get('surat_ijin_keluarga'), 'surat_ijin_keluarga', p.spk.replace('/', ''))

            db.session.commit()
            flash(f'Pengajuan pinjaman berhasil. SPK: {p.spk}', 'success')
            return redirect(url_for('pinjaman.detail', id=p.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Gagal menyimpan pinjaman: {e}', exc_info=True)
            flash(f'Gagal menyimpan pinjaman: {e}', 'danger')
            return redirect(url_for('pinjaman.tambah', nasabah_id=nasabah.id))

    else: # GET
        is_valid, msg = validate_nasabah_loan(nasabah)
        if not is_valid:
            flash(msg, 'danger' if 'aktif' in msg or 'ditolak' in msg else 'warning')
            return redirect(url_for('main.dashboard'))

    return render_template('pinjaman/form_tambah.html',
        nasabah=nasabah, tenor_options=Config.TENOR_OPTIONS)


@pinjaman_bp.route('/detail/<int:id>')
@login_required
def detail(id):
    p = db.get_or_404(Pinjaman, id)
    if current_user.is_kader() and p.nasabah.kode_desa != current_user.kode_desa:
        abort(403)
    if current_user.is_nasabah() and p.nasabah_id_fk != current_user.nasabah_id_fk:
        abort(403)
    jadwal = p.get_jadwal_angsuran() if p.status in ['cair','lunas'] else []
    tunggak_pokok, tunggak_jasa, bulan_nunggak = p.get_tunggakan()
    kolek, kolek_label = p.get_kolektibilitas()
    total_pokok_bayar, total_jasa_bayar = p.get_realisasi_pembayaran()

    # Riwayat angsuran
    riwayat = db.session.query(Pembayaran).filter_by(pinjaman_id=id).order_by(Pembayaran.tanggal_bayar).all()

    # Estimasi pelunasan
    angsuran_belum = [j for j in jadwal if not j['lunas']]
    sisa_tenor = len(angsuran_belum)
    sisa_jasa = sisa_tenor * p.angsuran_jasa if p.angsuran_jasa else 0
    total_pelunasan = p.get_saldo_pokok() + sisa_jasa

    # Map user names
    user_map = {u.id: u.nama_lengkap for u in db.session.query(User).all()}

    return render_template('pinjaman/detail.html', p=p, jadwal=jadwal,
        tunggak_pokok=tunggak_pokok, tunggak_jasa=tunggak_jasa,
        bulan_nunggak=bulan_nunggak, kolek=kolek, kolek_label=kolek_label,
        total_pokok_bayar=total_pokok_bayar, total_jasa_bayar=total_jasa_bayar,
        today=date.today(),
        riwayat=riwayat, user_map=user_map,
        angsuran_belum=angsuran_belum,
        estimasi_sisa_tenor=sisa_tenor,
        estimasi_sisa_jasa=sisa_jasa,
        estimasi_total_pelunasan=total_pelunasan)


@pinjaman_bp.route('/proses/<int:id>', methods=['POST'])
@login_required
def proses(id):
    p   = db.get_or_404(Pinjaman, id)
    if current_user.is_kader() and p.nasabah.kode_desa != current_user.kode_desa:
        abort(403)
    aksi = request.form.get('aksi')

    if aksi == 'cek_dokumen' and p.status == 'pengajuan':
        flash('Gunakan form Pemeriksaan Dokumen untuk memproses pengajuan ini.', 'warning')
        return redirect(url_for('pemeriksaan.form', pinjaman_id=p.id))

    if aksi == 'verifikasi' and p.status in ['cek_dokumen', 'verifikasi']:
        try:
            p.tanggal_kunjungan = datetime.strptime(request.form.get('tanggal_kunjungan',''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            p.tanggal_kunjungan = date.today()
        p.petugas_kunjungan = current_user.nama_lengkap
        p.hasil_kunjungan   = request.form.get('hasil_kunjungan','')
        p.rekomendasi       = request.form.get('rekomendasi','')
        p.verified_by       = current_user.id
        p.verified_at       = datetime.now(timezone.utc)
        
        # Simpan foto_kunjungan
        new_f = save_file(request.files.get('foto_kunjungan'), 'foto', p.spk.replace('/',''))
        if new_f:
            p.foto_kunjungan = new_f
            
        p.status = 'verifikasi'
        db.session.commit()
        flash('Berita acara kunjungan disimpan.', 'success')

    if aksi == 'acc' and p.status == 'verifikasi':
        p.status           = 'acc_direktur'
        p.tanggal_acc      = date.today()
        p.acc_by           = current_user.id
        p.catatan_direktur = request.form.get('catatan_direktur','')
        db.session.commit()
        flash('Pinjaman di-ACC Direktur.', 'success')

    elif aksi == 'tolak':
        p.status           = 'ditolak'
        p.catatan_direktur = request.form.get('catatan_direktur','')
        
        # Hitung jumlah penolakan untukthis nasabah
        penolakan_sebelumnya = db.session.query(Pinjaman).filter(
            Pinjaman.nasabah_id_fk == p.nasabah_id_fk,
            Pinjaman.status == 'ditolak'
        ).count()
        p.jumlah_penolakan = penolakan_sebelumnya + 1
        
        db.session.commit()
        flash('Pinjaman ditolak.', 'warning')

    elif aksi == 'cairkan' and p.status == 'acc_direktur':
        from ..models import hitung_angsuran_bulat
        try:
            tgl_cair  = datetime.strptime(request.form.get('tanggal_cair',''), '%Y-%m-%d').date()
            tgl_mulai = datetime.strptime(request.form.get('tanggal_mulai_angsuran',''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            tgl_cair  = date.today()
            tgl_mulai = date.today() + relativedelta(months=1)

        hasil = hitung_angsuran_bulat(p.jumlah_pinjaman, p.tenor, p.jasa_persen)
        p.tanggal_cair            = tgl_cair
        p.tanggal_mulai_angsuran  = tgl_mulai
        p.status                  = 'cair'
        p.angsuran_pokok          = hasil['pokok']
        p.angsuran_jasa           = hasil['jasa']
        p.angsuran_total          = hasil['total']
        p.angsuran_terakhir_pokok = hasil['pokok_terakhir']
        db.session.commit()
        # Auto-jurnal pencairan
        try:
            jurnal_pencairan(p, current_user.id)
        except Exception as e:
            logger.warning(f'Jurnal pencairan gagal (COA mungkin belum di-seed): {e}')
        flash(f'Pinjaman dicairkan! Angsuran: Rp {hasil["total"]:,}/bulan', 'success')
        return redirect(url_for('pinjaman.cetak_kuitansi_cair', id=p.id))

    return redirect(url_for('pinjaman.detail', id=id))


@pinjaman_bp.route('/cetak/spk/<int:id>')
@login_required
def cetak_spk(id):
    return render_template('print/spk.html', p=db.get_or_404(Pinjaman, id), back_url=url_for('pinjaman.detail', id=id))


@pinjaman_bp.route('/cetak/kuitansi-cair/<int:id>')
@login_required
def cetak_kuitansi_cair(id):
    return render_template('print/kuitansi_cair.html', p=db.get_or_404(Pinjaman, id), back_url=url_for('pinjaman.detail', id=id))


@pinjaman_bp.route('/cetak/kartu-angsuran/<int:id>')
@login_required
def cetak_kartu_angsuran(id):
    p = db.get_or_404(Pinjaman, id)
    return render_template('print/kartu_angsuran.html', p=p, jadwal=p.get_jadwal_angsuran(), back_url=url_for('pinjaman.detail', id=id))


@pinjaman_bp.route('/cetak/riwayat/<int:id>')
@login_required
def cetak_riwayat(id):
    p = db.get_or_404(Pinjaman, id)
    if current_user.is_kader() and p.nasabah.kode_desa != current_user.kode_desa:
        abort(403)
    if current_user.is_nasabah() and p.nasabah_id_fk != current_user.nasabah_id_fk:
        abort(403)
        
    jadwal = p.get_jadwal_angsuran()
    tunggak_pokok, tunggak_jasa, bulan_nunggak = p.get_tunggakan()
    kolek, kolek_label = p.get_kolektibilitas()
    total_pokok_bayar, total_jasa_bayar = p.get_realisasi_pembayaran()
    riwayat = db.session.query(Pembayaran).filter_by(pinjaman_id=id).order_by(Pembayaran.tanggal_bayar).all()
    
    # Estimasi pelunasan
    angsuran_belum = [j for j in jadwal if not j['lunas']]
    sisa_tenor = len(angsuran_belum)
    sisa_jasa = sisa_tenor * p.angsuran_jasa if p.angsuran_jasa else 0
    total_pelunasan = p.get_saldo_pokok() + sisa_jasa
    
    user_map = {u.id: u.nama_lengkap for u in db.session.query(User).all()}
    
    return render_template('print/riwayat_pinjaman.html', p=p, jadwal=jadwal,
        tunggak_pokok=tunggak_pokok, tunggak_jasa=tunggak_jasa,
        bulan_nunggak=bulan_nunggak, kolek=kolek, kolek_label=kolek_label,
        total_pokok_bayar=total_pokok_bayar, total_jasa_bayar=total_jasa_bayar,
        today=date.today(),
        riwayat=riwayat, user_map=user_map, current_user=current_user,
        angsuran_belum=angsuran_belum,
        estimasi_sisa_tenor=sisa_tenor,
        estimasi_sisa_jasa=sisa_jasa,
        estimasi_total_pelunasan=total_pelunasan,
        back_url=url_for('pinjaman.detail', id=id))


@pinjaman_bp.route('/rekap-pencairan')
@login_required
def rekap_pencairan():
    tgl_dari    = request.args.get('dari', date.today().replace(day=1).strftime('%Y-%m-%d'))
    tgl_sampai  = request.args.get('sampai', date.today().strftime('%Y-%m-%d'))
    desa_filter = request.args.get('desa','')
    try:
        d_dari   = datetime.strptime(tgl_dari,'%Y-%m-%d').date()
        d_sampai = datetime.strptime(tgl_sampai,'%Y-%m-%d').date()
    except:
        d_dari   = date.today().replace(day=1)
        d_sampai = date.today()

    q = db.session.query(Pinjaman).join(Nasabah).filter(
        Pinjaman.tanggal_cair >= d_dari,
        Pinjaman.tanggal_cair <= d_sampai,
        Pinjaman.status.in_(['cair','lunas'])
    )
    if desa_filter: q = q.filter(Nasabah.kode_desa == desa_filter)
    pinjaman_list = q.order_by(Pinjaman.tanggal_cair).all()
    total_cair    = sum(p.jumlah_pinjaman for p in pinjaman_list)

    if request.args.get('cetak'):
        return render_template('print/rekap_pencairan.html',
            pinjaman_list=pinjaman_list, total_cair=total_cair,
            tgl_dari=d_dari, tgl_sampai=d_sampai,
            desa_filter=desa_filter, desa_list=Config.DESA_LIST)

    return render_template('pinjaman/rekap_pencairan.html',
        pinjaman_list=pinjaman_list, total_cair=total_cair,
        tgl_dari=tgl_dari, tgl_sampai=tgl_sampai,
        desa_filter=desa_filter, desa_list=Config.DESA_LIST)


@pinjaman_bp.route('/hapus/<int:id>', methods=['POST'])
@login_required
def hapus(id):
    if not current_user.is_admin(): abort(403)
    p = db.get_or_404(Pinjaman, id)
    spk = p.spk
    nama = p.nasabah.nama
    from ..models import JurnalUmum
    jurnal_list = db.session.query(JurnalUmum).filter_by(referensi=spk, tipe='pencairan').all()
    for j in jurnal_list:
        db.session.delete(j)
    db.session.delete(p)
    db.session.commit()
    flash(f'Pinjaman {spk} (Nasabah: {nama}) beserta jurnal terkait berhasil dihapus.', 'success')
    return redirect(url_for('pinjaman.index'))


@pinjaman_bp.route('/cetak/ba/<int:id>')
@login_required
def cetak_ba(id):
    p = db.get_or_404(Pinjaman, id)
    if current_user.is_kader() and p.nasabah.kode_desa != current_user.kode_desa:
        abort(403)
    verifier = db.session.get(User, p.verified_by) if p.verified_by else None
    return render_template('print/berita_acara.html', p=p, verifier=verifier, back_url=url_for('pinjaman.detail', id=id), today=date.today())


@pinjaman_bp.route('/cetak/spp/<int:id>')
@login_required
def cetak_spp(id):
    p = db.get_or_404(Pinjaman, id)
    if not p.status in ['acc_direktur', 'cair', 'lunas']:
        abort(403)
    from ..models import hitung_angsuran_bulat
    acc_by = db.session.get(User, p.acc_by) if p.acc_by else None
    if p.angsuran_total is None:
        hasil = hitung_angsuran_bulat(p.jumlah_pinjaman, p.tenor, p.jasa_persen)
        p.angsuran_pokok = hasil['pokok']
        p.angsuran_jasa = hasil['jasa']
        p.angsuran_total = hasil['total']
        p.angsuran_terakhir_pokok = hasil['pokok_terakhir']
        db.session.commit()
    return render_template('print/surat_perintah_pencairan.html', p=p, acc_by=acc_by, back_url=url_for('pinjaman.detail', id=id), today=date.today())
