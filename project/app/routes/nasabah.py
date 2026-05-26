from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, jsonify
from flask_login import login_required, current_user
from ..models import db, Nasabah, RekeningTabungan, AnggotaKelompok, User
from config import Config
import os
from werkzeug.utils import secure_filename
from datetime import datetime

nasabah_bp = Blueprint('nasabah', __name__)

@nasabah_bp.before_request
def restrict_nasabah_role():
    if current_user.is_authenticated and current_user.is_nasabah():
        if request.method == 'POST':
            abort(403)

from ..utils.helpers import save_file, get_next_nasabah_id



# ── Index ────────────────────────────────────────────────────
@nasabah_bp.route('/')
@login_required
def index():
    page           = request.args.get('page', 1, type=int)
    desa_filter    = request.args.get('desa', '')
    jenis_filter   = request.args.get('jenis', 'perorangan')
    status_filter  = request.args.get('status', 'aktif')
    search         = request.args.get('q', '')

    if current_user.is_kader() and status_filter == 'calon':
        status_filter = 'aktif'
    
    q = Nasabah.query
    if current_user.is_kader():
        desa_filter = current_user.kode_desa
        q = q.filter_by(kode_desa=desa_filter)
    elif desa_filter:
        q = q.filter_by(kode_desa=desa_filter)
    
    if jenis_filter:  q = q.filter_by(jenis=jenis_filter)
    if status_filter: q = q.filter_by(status=status_filter)
    
    if search:
        q = q.filter(Nasabah.nama.ilike(f'%{search}%') |
                     Nasabah.nasabah_id.ilike(f'%{search}%') |
                     Nasabah.nik.ilike(f'%{search}%'))

    nasabah_list     = q.order_by(Nasabah.nasabah_id).paginate(page=page, per_page=20)

    total_nasabah   = Nasabah.query.count()
    total_aktif     = Nasabah.query.filter_by(status='aktif').count()
    total_calon     = Nasabah.query.filter_by(status='calon').count()
    total_perorangan = Nasabah.query.filter_by(jenis='perorangan', status='aktif').count()

    return render_template('nasabah/index.html',
        nasabah_list=nasabah_list, desa_list=Config.DESA_LIST,
        desa_filter=desa_filter, jenis_filter=jenis_filter, 
        status_filter=status_filter, search=search,
        total_nasabah=total_nasabah, total_aktif=total_aktif,
        total_calon=total_calon, total_perorangan=total_perorangan)


# ── Tambah ───────────────────────────────────────────────────

@nasabah_bp.route('/count')
@login_required
def count_json():
    from flask import jsonify
    q = Nasabah.query
    if current_user.is_kader():
        q = q.filter_by(kode_desa=current_user.kode_desa)
        
    return jsonify({
        'perorangan': q.filter_by(jenis='perorangan', status='aktif').count(),
        'kelompok'  : q.filter_by(jenis='kelompok', status='aktif').count(),
        'calon'     : q.filter_by(status='calon').count(),
    })


@nasabah_bp.route('/tambah', methods=['GET','POST'])
@login_required
def tambah():
    if not current_user.can_write_nasabah(): abort(403)
    jenis = request.args.get('jenis','perorangan')  # pre-select jenis

    if request.method == 'POST':
        jenis     = request.form.get('jenis','perorangan')
        kode_desa = request.form.get('kode_desa','')
        if current_user.is_kader():
            kode_desa = current_user.kode_desa
        
        nama_desa = dict(Config.DESA_LIST).get(kode_desa,'')

        # ID: manual atau auto
        nasabah_id_manual = request.form.get('nasabah_id_manual','').strip().upper()
        if nasabah_id_manual:
            if Nasabah.query.filter_by(nasabah_id=nasabah_id_manual).first():
                flash(f'ID {nasabah_id_manual} sudah digunakan!','danger')
                return redirect(url_for('nasabah.tambah', jenis=jenis))
            nasabah_id = nasabah_id_manual
        else:
            nasabah_id = get_next_nasabah_id(kode_desa)

        try:
            tgl_lahir = datetime.strptime(request.form.get('tanggal_lahir',''),'%Y-%m-%d').date()
        except (ValueError, TypeError): tgl_lahir = None

        # NIK: untuk kelompok bisa kosong
        nik = request.form.get('nik','').strip()
        if not nik:
            import uuid
            nik = f"NOID-{uuid.uuid4().hex[:12].upper()}"
        else:
            # Cek NIK duplikat untuk perorangan
            if Nasabah.query.filter_by(nik=nik).first():
                flash(f'NIK {nik} sudah terdaftar pada nasabah lain.','danger')
                return redirect(url_for('nasabah.tambah', jenis=jenis))

        nasabah = Nasabah(
            nasabah_id    = nasabah_id,
            jenis         = jenis,
            kode_desa     = kode_desa,
            nama_desa     = nama_desa,
            nama          = request.form.get('nama','').upper(),
            nik           = nik,
            tempat_lahir  = request.form.get('tempat_lahir','').upper(),
            tanggal_lahir = tgl_lahir,
            jenis_kelamin = request.form.get('jenis_kelamin',''),
            alamat        = request.form.get('alamat',''),
            no_hp         = request.form.get('no_hp',''),
            pekerjaan     = request.form.get('pekerjaan','') if jenis=='perorangan' else 'KELOMPOK',
            nama_pasangan = request.form.get('nama_pasangan','').upper(),
            nik_pasangan  = request.form.get('nik_pasangan',''),
            no_hp_pasangan= request.form.get('no_hp_pasangan',''),
            keterangan_jaminan = request.form.get('keterangan_jaminan',''),
            status        = 'calon' if current_user.is_kader() else 'aktif',
            created_by    = current_user.id,
        )

# Upload dokumen
        prefix = nasabah_id.replace('-','')
        doc_fields = [
            ('foto','foto', True),
            ('jaminan','jaminan', False),
        ]
        if jenis == 'kelompok':
            doc_fields += [('surat_tanggung_renteng_nasabah','surat_tanggung_renteng', False), ('surat_ijin_keluarga_nasabah','surat_ijin_keluarga', False)]
        else:
            doc_fields += [('ktp','ktp', False), ('kk','kk', False), ('surat_usaha','sku', False), ('bukti_penghasilan','penghasilan', False)]
        for field, subfolder, force_portrait in doc_fields:
            new_f = save_file(request.files.get(field), subfolder, prefix, force_portrait=force_portrait)
            if new_f: setattr(nasabah, field, new_f)

        db.session.add(nasabah)
        db.session.flush()

        # Auto-buat rekening tabungan
        rek = RekeningTabungan(nasabah_id=nasabah.id, no_rekening=f"TAB-{nasabah_id}")
        db.session.add(rek)

        # Simpan anggota kelompok
        if jenis == 'kelompok':
            nama_anggota_list = request.form.getlist('anggota_nama[]')
            nik_anggota_list  = request.form.getlist('anggota_nik[]')
            jabatan_list      = request.form.getlist('anggota_jabatan[]')
            hp_list           = request.form.getlist('anggota_hp[]')
            alamat_list       = request.form.getlist('anggota_alamat[]')
            ktp_files         = request.files.getlist('anggota_ktp[]')
            kk_files          = request.files.getlist('anggota_kk[]')

            for i, nama_a in enumerate(nama_anggota_list):
                nama_a = nama_a.strip().upper()
                if not nama_a: continue
                ktp_path = save_file(ktp_files[i], 'anggota_ktp', nasabah.nasabah_id) if i < len(ktp_files) else None
                kk_path  = save_file(kk_files[i], 'anggota_kk', nasabah.nasabah_id) if i < len(kk_files) else None
                a = AnggotaKelompok(
                    kelompok_id = nasabah.id,
                    urut        = i + 1,
                    nama        = nama_a,
                    nik         = nik_anggota_list[i].strip() if i < len(nik_anggota_list) else '',
                    jabatan     = jabatan_list[i] if i < len(jabatan_list) else 'anggota',
                    no_hp       = hp_list[i].strip() if i < len(hp_list) else '',
                    alamat      = alamat_list[i].strip() if i < len(alamat_list) else '',
                    ktp         = ktp_path or '',
                    kk          = kk_path or '',
                )
                db.session.add(a)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Gagal menyimpan nasabah')
            flash(f'Gagal menyimpan nasabah: {e}', 'danger')
            return redirect(url_for('nasabah.tambah', jenis=jenis))
        flash(f'Nasabah {jenis} "{nasabah.nama}" ditambahkan. ID: {nasabah_id}','success')
        return redirect(url_for('nasabah.detail', id=nasabah.id))

    return render_template('nasabah/form.html', desa_list=Config.DESA_LIST, nasabah=None, jenis=jenis)


# ── Detail ───────────────────────────────────────────────────
@nasabah_bp.route('/detail/<int:id>')
@login_required
def detail(id):
    nasabah = Nasabah.query.get_or_404(id)
    if current_user.is_kader() and nasabah.kode_desa != current_user.kode_desa:
        abort(403)
    return render_template('nasabah/detail.html', nasabah=nasabah)


# ── Edit ─────────────────────────────────────────────────────
@nasabah_bp.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit(id):
    nasabah = Nasabah.query.get_or_404(id)
    if current_user.is_kader() and nasabah.kode_desa != current_user.kode_desa:
        abort(403)

    if request.method == 'POST':
        nasabah.nama         = request.form.get('nama','').upper()
        nik_baru = request.form.get('nik', '').strip()
        if not nik_baru:
            import uuid
            nasabah.nik = f"NOID-{uuid.uuid4().hex[:12].upper()}"
        elif nik_baru != nasabah.nik:
            if Nasabah.query.filter_by(nik=nik_baru).first():
                flash(f'NIK {nik_baru} sudah terdaftar pada nasabah lain.', 'danger')
                return redirect(url_for('nasabah.edit', id=nasabah.id))
            nasabah.nik = nik_baru
        nasabah.tempat_lahir = request.form.get('tempat_lahir','').upper()
        try:
            nasabah.tanggal_lahir = datetime.strptime(request.form.get('tanggal_lahir',''),'%Y-%m-%d').date()
        except (ValueError, TypeError): pass
        nasabah.jenis_kelamin  = request.form.get('jenis_kelamin','')
        nasabah.alamat         = request.form.get('alamat','')
        nasabah.no_hp          = request.form.get('no_hp','')
        nasabah.pekerjaan      = request.form.get('pekerjaan','')
        nasabah.nama_pasangan  = request.form.get('nama_pasangan','').upper()
        nasabah.nik_pasangan   = request.form.get('nik_pasangan','')
        nasabah.no_hp_pasangan = request.form.get('no_hp_pasangan','')
        nasabah.keterangan_jaminan = request.form.get('keterangan_jaminan','')

        prefix = nasabah.nasabah_id.replace('-','')
        doc_fields = [('foto','foto'), ('jaminan','jaminan')]
        if nasabah.jenis == 'kelompok':
            doc_fields += [('surat_tanggung_renteng_nasabah','surat_tanggung_renteng'), ('surat_ijin_keluarga_nasabah','surat_ijin_keluarga')]
        else:
            doc_fields += [('ktp','ktp'), ('kk','kk'), ('surat_usaha','sku'), ('bukti_penghasilan','penghasilan')]
        for field, subfolder in doc_fields:
            new_f = save_file(request.files.get(field), subfolder, prefix)
            if new_f: setattr(nasabah, field, new_f)

        new_ttd = save_file(request.files.get('tanda_tangan'), 'ttd_nasabah', prefix)
        if new_ttd: nasabah.tanda_tangan = new_ttd

        # Update anggota kelompok jika ada
        if nasabah.jenis == 'kelompok':
            nama_list    = request.form.getlist('anggota_nama[]')
            nik_list     = request.form.getlist('anggota_nik[]')
            jabatan_list = request.form.getlist('anggota_jabatan[]')
            hp_list      = request.form.getlist('anggota_hp[]')
            alamat_list  = request.form.getlist('anggota_alamat[]')
            ktp_files    = request.files.getlist('anggota_ktp[]')
            kk_files     = request.files.getlist('anggota_kk[]')
            ktp_old_list = request.form.getlist('anggota_ktp_old[]')
            kk_old_list  = request.form.getlist('anggota_kk_old[]')
            # Hapus lama, insert baru
            AnggotaKelompok.query.filter_by(kelompok_id=nasabah.id).delete()
            for i, nama_a in enumerate(nama_list):
                nama_a = nama_a.strip().upper()
                if not nama_a: continue
                ktp_path = save_file(ktp_files[i], 'anggota_ktp', nasabah.nasabah_id) if i < len(ktp_files) and ktp_files[i].filename else (ktp_old_list[i] if i < len(ktp_old_list) and ktp_old_list[i] else '')
                kk_path  = save_file(kk_files[i], 'anggota_kk', nasabah.nasabah_id) if i < len(kk_files) and kk_files[i].filename else (kk_old_list[i] if i < len(kk_old_list) and kk_old_list[i] else '')
                db.session.add(AnggotaKelompok(
                    kelompok_id=nasabah.id, urut=i+1,
                    nama=nama_a,
                    nik=nik_list[i].strip() if i<len(nik_list) else '',
                    jabatan=jabatan_list[i] if i<len(jabatan_list) else 'anggota',
                    no_hp=hp_list[i].strip() if i<len(hp_list) else '',
                    alamat=alamat_list[i].strip() if i<len(alamat_list) else '',
                    ktp=ktp_path,
                    kk=kk_path,
                ))

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Gagal memperbarui nasabah')
            flash(f'Gagal memperbarui nasabah: {e}', 'danger')
            return redirect(url_for('nasabah.edit', id=nasabah.id))
        flash('Data nasabah diperbarui.','success')
        next_url = request.args.get('next')
        if next_url:
            return redirect(next_url)
        return redirect(url_for('nasabah.detail', id=nasabah.id))

    return render_template('nasabah/form.html', desa_list=Config.DESA_LIST, nasabah=nasabah, jenis=nasabah.jenis)


# ── Hapus ────────────────────────────────────────────────────
@nasabah_bp.route('/hapus/<int:id>', methods=['POST'])
@login_required
def hapus(id):
    if not current_user.is_admin(): abort(403)
    nasabah = Nasabah.query.get_or_404(id)
    
    if nasabah.pinjaman:
        flash('Tidak dapat menghapus nasabah karena memiliki riwayat pinjaman.', 'danger')
        return redirect(url_for('nasabah.index'))

    # Hapus user account yang terkait (jika ada)
    related_user = User.query.filter_by(nasabah_id_fk=nasabah.id).first()
    if related_user:
        # Jika nasabah daftar mandiri, created_by mungkin menunjuk ke user ini
        if nasabah.created_by == related_user.id:
            nasabah.created_by = None
            db.session.flush()
        db.session.delete(related_user)

    # Hapus rekening dan transaksinya
    if nasabah.rekening:
        from ..models import TransaksiTabungan
        TransaksiTabungan.query.filter_by(rekening_id=nasabah.rekening.id).delete()
        db.session.delete(nasabah.rekening)
        
    # Hapus jaminan
    from ..models import JaminanBPKB, JaminanSHM, JaminanLain
    JaminanBPKB.query.filter_by(nasabah_id=id).delete()
    JaminanSHM.query.filter_by(nasabah_id=id).delete()
    JaminanLain.query.filter_by(nasabah_id=id).delete()
    
    # Hapus anggota kelompok
    AnggotaKelompok.query.filter_by(kelompok_id=id).delete()

    # Hapus Ajuan Dokumen
    from ..models import AjuanDokumen
    AjuanDokumen.query.filter_by(nasabah_id=id).delete()
    
    # Hapus referensi di Pengumuman (set null)
    from ..models import Pengumuman
    Pengumuman.query.filter_by(nasabah_id_fk=id).update({'nasabah_id_fk': None})

    db.session.delete(nasabah)
    try:
        db.session.commit()
        flash(f'Nasabah {nasabah.nama} berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Gagal menghapus nasabah')
        flash(f'Gagal menghapus nasabah: {e}', 'danger')
        
    return redirect(url_for('nasabah.index'))


# ── Approve / Tolak calon nasabah ───────────────────────────
@nasabah_bp.route('/calon/approve/<int:id>', methods=['POST'])
@login_required
def calon_approve(id):
    if not (current_user.is_admin() or current_user.is_manajer() or current_user.is_staf()):
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('nasabah.index'))
    nasabah = Nasabah.query.get_or_404(id)
    action  = request.form.get('action')
    pesan   = request.form.get('pesan', '')
    if action == 'approve':
        nasabah.status = 'aktif'
        nasabah.keterangan_status = 'Pendaftaran Anda telah disetujui.'
        
        # Otomatis buat pengumuman selamat bergabung
        from ..models import Pengumuman
        prefix = "Kelompok" if nasabah.jenis == 'kelompok' else "bapak/ibu"
        isi_msg = f"Selamat bergabung {prefix} {nasabah.nama} di BUM Desa bersama UPK Ciomas LKD!"
        
        from datetime import datetime, timedelta, timezone
        
        p = Pengumuman(
            judul="Selamat Bergabung!",
            isi=isi_msg,
            tipe='info',
            target='nasabah_spesifik',
            nasabah_id_fk=nasabah.id,
            aktif=True,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            created_by=current_user.id
        )
        db.session.add(p)
        
        db.session.commit()
        flash(f'Nasabah {nasabah.nama} telah disetujui dan pesan selamat bergabung telah dikirim.', 'success')
    elif action == 'reject':
        db.session.delete(nasabah)
        db.session.commit()
        flash(f'Pendaftaran {nasabah.nama} ditolak.', 'warning')
    elif action == 'message':
        nasabah.keterangan_status = pesan
        db.session.commit()
        flash(f'Pesan terkirim ke {nasabah.nama}.', 'info')
    next_url = request.form.get('next')
    return redirect(next_url if next_url else url_for('nasabah.index', status='calon', jenis=''))


# ── API: get anggota kelompok (untuk form pinjaman SPP) ──────
@nasabah_bp.route('/api/anggota/<int:nasabah_id>')
@login_required
def api_anggota(nasabah_id):
    nasabah = Nasabah.query.get_or_404(nasabah_id)
    if nasabah.jenis != 'kelompok':
        return jsonify([])
    return jsonify([{
        'id'     : a.id,
        'urut'   : a.urut,
        'nama'   : a.nama,
        'nik'    : a.nik or '',
        'jabatan': a.jabatan,
        'no_hp'  : a.no_hp or '',
    } for a in nasabah.anggota])
