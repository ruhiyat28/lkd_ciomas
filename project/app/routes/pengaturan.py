from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from ..models import db, Pengaturan, User, Pengumuman, RekeningPembayaran, AkunCOA, JurnalUmum, JurnalDetail
from ..utils.helpers import generate_random_password, save_file

pengaturan_bp = Blueprint('pengaturan', __name__)

PENGURUS_FIELDS = [
    ('direktur',       'Direktur'),
    ('manajer_lkd',    'Manajer LKD'),
    ('kabag_kredit',   'Kepala Bagian Kredit'),
    ('kabag_keuangan', 'Kepala Bagian Keuangan'),
    ('kabag_tu',       'Kepala Bagian Tata Usaha'),
    ('kasir',          'Kasir'),
    ('staf',           'Staf'),
]

LEMBAGA_FIELDS = [
    ('nama_lembaga', 'Nama Lembaga'),
    ('alamat',       'Alamat'),
    ('telp',         'Telepon'),
    ('wa',           'WhatsApp'),
    ('email',        'Email'),
    ('wa_pengirim',  'Nomor WA Pengirim Tagihan'),
    ('wa_api_key',   'API Key WA Gateway (opsional)'),
]

BULAN_NAMES = [
    'Januari','Februari','Maret','April','Mei','Juni',
    'Juli','Agustus','September','Oktober','November','Desember'
]


@pengaturan_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)

    Pengaturan.seed_defaults()

    if request.method == 'POST':
        all_fields = [k for k, _ in LEMBAGA_FIELDS + PENGURUS_FIELDS]
        for kunci in all_fields:
            nilai = request.form.get(kunci, '')
            Pengaturan.set(kunci, nilai)
        db.session.commit()
        flash('Pengaturan lembaga berhasil disimpan.', 'success')
        return redirect(url_for('pengaturan.index'))

    data = {p.kunci: p.nilai for p in Pengaturan.query.all()}
    return render_template('pengaturan/index.html',
        data=data,
        lembaga_fields=LEMBAGA_FIELDS,
        pengurus_fields=PENGURUS_FIELDS)





@pengaturan_bp.route('/rkp', methods=['GET', 'POST'])
@login_required
def rkp():
    """Rencana Kerja dan Pendapatan (RKP) — input target bulanan per tahun."""
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)

    from datetime import date
    tahun_sekarang = date.today().year
    tahun = request.args.get('tahun', str(tahun_sekarang))
    try:
        tahun = int(tahun)
    except (ValueError, TypeError):
        tahun = tahun_sekarang

    if request.method == 'POST':
        tahun_form = int(request.form.get('tahun', tahun_sekarang))
        # Simpan data bulanan (pendapatan & penyaluran)
        for m in range(1, 13):
            for cat in ['pendapatan', 'penyaluran', 'pembayaran_pokok']:
                kunci = f'rkp_{tahun_form}_m{m:02d}_{cat}'
                nilai = request.form.get(kunci, '0').strip() or '0'
                Pengaturan.set(kunci, nilai, f'RKP {BULAN_NAMES[m-1]} {tahun_form} - {cat}')
        # Simpan rencana tahunan
        for cat in ['operasional', 'investasi', 'pendanaan', 'pendapatan_lain', 'beban_lain']:
            kunci = f'rkp_{tahun_form}_{cat}'
            nilai = request.form.get(kunci, '0').strip() or '0'
            Pengaturan.set(kunci, nilai, f'RKP Tahunan {tahun_form} - {cat}')
        db.session.commit()
        flash(f'RKP Tahun {tahun_form} berhasil disimpan.', 'success')
        return redirect(url_for('pengaturan.rkp', tahun=tahun_form))

    # Ambil data RKP untuk tahun terpilih
    data_bulanan = []
    for m in range(1, 13):
        row = {'bulan': m, 'nama': BULAN_NAMES[m-1]}
        for cat in ['pendapatan', 'penyaluran', 'pembayaran_pokok']:
            kunci = f'rkp_{tahun}_m{m:02d}_{cat}'
            try:
                row[cat] = int(Pengaturan.get(kunci, '0') or 0)
            except (ValueError, TypeError):
                row[cat] = 0
        data_bulanan.append(row)

    data_tahunan = {}
    for cat in ['operasional', 'investasi', 'pendanaan', 'pendapatan_lain', 'beban_lain']:
        kunci = f'rkp_{tahun}_{cat}'
        try:
            data_tahunan[cat] = int(Pengaturan.get(kunci, '0') or 0)
        except (ValueError, TypeError):
            data_tahunan[cat] = 0

    tahun_options = list(range(tahun_sekarang - 3, tahun_sekarang + 4))

    return render_template('pengaturan/rkp.html',
        tahun=tahun,
        tahun_options=tahun_options,
        data_bulanan=data_bulanan,
        data_tahunan=data_tahunan,
        bulan_names=BULAN_NAMES)


@pengaturan_bp.route('/users-nasabah')
@login_required
def users_nasabah():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)

    from ..models import Nasabah
    users_nasabah = User.query.filter_by(role='nasabah').all()

    return render_template('pengaturan/users_nasabah.html',
                           users_nasabah=users_nasabah)

@pengaturan_bp.route('/users-nasabah/search')
@login_required
def search_nasabah_no_account():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return {'results': []}
        
    from ..models import Nasabah, User
    
    # Ambil ID nasabah yang sudah punya akun
    subq = db.session.query(User.nasabah_id_fk).filter(User.role == 'nasabah', User.nasabah_id_fk.isnot(None))
    
    # Filter nasabah aktif yang namanya mengandung q dan belum ada di subquery
    query = Nasabah.query.filter(
        Nasabah.status == 'aktif',
        Nasabah.nama.ilike(f'%{q}%'),
        ~Nasabah.id.in_(subq)
    )
    
    results = query.limit(10).all()
    return {
        'results': [
            {
                'id': n.id,
                'nama': n.nama,
                'nasabah_id': n.nasabah_id,
                'desa': n.nama_desa
            } for n in results
        ]
    }
    
    
@pengaturan_bp.route('/users-nasabah/search-active')
@login_required
def search_nasabah_active():
    """Search all active nasabah (including those with accounts) for Broadcast."""
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return {'results': []}
        
    from ..models import Nasabah
    
    query = Nasabah.query.filter(
        Nasabah.status == 'aktif',
        (Nasabah.nama.ilike(f'%{q}%') | Nasabah.nasabah_id.ilike(f'%{q}%'))
    )
    
    results = query.limit(10).all()
    return {
        'results': [
            {
                'id': n.id,
                'nama': n.nama,
                'nasabah_id': n.nasabah_id,
                'desa': n.nama_desa
            } for n in results
        ]
    }


@pengaturan_bp.route('/users-nasabah/buat', methods=['POST'])
@login_required
def buat_akun_nasabah():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)

    from ..models import Nasabah
    nasabah_id = request.form.get('nasabah_id')
    nasabah = Nasabah.query.get_or_404(nasabah_id)

    # Cek apakah sudah ada
    if User.query.filter_by(nasabah_id_fk=nasabah.id).first():
        flash('Nasabah ini sudah memiliki akun.', 'warning')
        return redirect(url_for('pengaturan.users_nasabah'))

    # Username: ID Nasabah lowercase tanpa tanda hubung
    username = nasabah.nasabah_id.replace('-', '').lower()
    if User.query.filter_by(username=username).first():
        username = f"{username}_{nasabah.id}"

    u = User(
        username=username,
        nama_lengkap=nasabah.nama,
        role='nasabah',
        nasabah_id_fk=nasabah.id,
        aktif=True
    )
    
    password_form = request.form.get('password')
    if password_form:
        u.set_password(password_form)
        password_final = password_form
    else:
        password_final = generate_random_password()
        u.set_password(password_final)
        
    db.session.add(u)
    db.session.commit()

    flash(f'Akun berhasil dibuat untuk {nasabah.nama}. Username: {username}, Password: {password_final}', 'success')
    return redirect(url_for('pengaturan.users_nasabah'))


@pengaturan_bp.route('/users-nasabah/reset/<int:user_id>', methods=['POST'])
@login_required
def reset_password_nasabah(user_id):
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    u = User.query.get_or_404(user_id)
    password_baru = generate_random_password()
    u.set_password(password_baru)
    db.session.commit()
    flash(f'Password untuk {u.nama_lengkap} berhasil direset menjadi: {password_baru} (Catat password ini!)', 'success')
    return redirect(url_for('pengaturan.users_nasabah'))


@pengaturan_bp.route('/users-nasabah/toggle/<int:user_id>', methods=['POST'])
@login_required
def toggle_akun_nasabah(user_id):
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    u = User.query.get_or_404(user_id)
    if u.role != 'nasabah': abort(403)
    u.aktif = not u.aktif
    db.session.commit()
    status = 'diaktifkan' if u.aktif else 'dinonaktifkan'
    flash(f'Akun {u.nama_lengkap} berhasil {status}.', 'success')
    return redirect(url_for('pengaturan.users_nasabah'))


@pengaturan_bp.route('/users-nasabah/hapus/<int:user_id>', methods=['POST'])
@login_required
def hapus_akun_nasabah(user_id):
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    u = User.query.get_or_404(user_id)
    if u.role != 'nasabah': abort(403)
    nama = u.nama_lengkap
    from ..models import Nasabah
    Nasabah.query.filter_by(created_by=u.id).update({'created_by': None})
    db.session.commit()
    db.session.delete(u)
    db.session.commit()
    flash(f'Akun {nama} berhasil dihapus.', 'success')
    return redirect(url_for('pengaturan.users_nasabah'))


@pengaturan_bp.route('/tanda-tangan', methods=['GET', 'POST'])
@login_required
def tanda_tangan():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    
    users = User.query.filter(User.role.in_(['admin', 'manajer_lkd', 'kabag_kredit'])).order_by(User.nama_lengkap).all()
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        u = User.query.get_or_404(user_id)
        f = request.files.get('tanda_tangan')
        if f and f.filename:
            # Hapus file lama jika ada
            if u.tanda_tangan:
                import os
                old_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads'), u.tanda_tangan)
                if os.path.exists(old_path):
                    os.remove(old_path)
            u.tanda_tangan = save_file(f, 'tanda_tangan', u.username.replace('/',''))
            db.session.commit()
            flash(f'Tanda tangan {u.nama_lengkap} berhasil diupload.', 'success')
        return redirect(url_for('pengaturan.tanda_tangan'))
    
    return render_template('pengaturan/tanda_tangan.html', users=users)


@pengaturan_bp.route('/pengumuman')
@login_required
def pengumuman():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    pengumuman_list = Pengumuman.query.order_by(Pengumuman.created_at.desc()).all()
    return render_template('pengaturan/pengumuman.html', pengumuman_list=pengumuman_list)


@pengaturan_bp.route('/pengumuman/tambah', methods=['GET', 'POST'])
@login_required
def pengumuman_tambah():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    if request.method == 'POST':
        from ..models import Nasabah
        target = request.form.get('target', 'semua')
        judul = request.form.get('judul', '').strip()
        isi = request.form.get('isi', '').strip()
        tipe = request.form.get('tipe', 'info')
        if not judul or not isi:
            flash('Judul dan isi pengumuman wajib diisi.', 'danger')
            return redirect(url_for('pengaturan.pengumuman_tambah'))
        nasabah_id_fk = request.form.get('nasabah_id_fk')
        if target == 'nasabah_spesifik' and not nasabah_id_fk:
            flash('Pilih nasabah terlebih dahulu untuk pengumuman spesifik.', 'danger')
            return redirect(url_for('pengaturan.pengumuman_tambah'))
            
        nasabah_id_fk = int(nasabah_id_fk) if (target == 'nasabah_spesifik' and nasabah_id_fk) else None
        p = Pengumuman(judul=judul, isi=isi, tipe=tipe, target=target, nasabah_id_fk=nasabah_id_fk, aktif=True, created_by=current_user.id)
        db.session.add(p)
        db.session.commit()
        flash('Pengumuman berhasil dibuat dan dikirim ke nasabah.', 'success')
        return redirect(url_for('pengaturan.pengumuman'))
    return render_template('pengaturan/pengumuman_form.html', pengumuman=None)


@pengaturan_bp.route('/pengumuman/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def pengumuman_edit(id):
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    pengumuman = Pengumuman.query.get_or_404(id)
    if request.method == 'POST':
        pengumuman.judul = request.form.get('judul', '').strip()
        pengumuman.isi = request.form.get('isi', '').strip()
        pengumuman.tipe = request.form.get('tipe', 'info')
        pengumuman.target = request.form.get('target', 'semua')
        nas_id = request.form.get('nasabah_id_fk')
        if pengumuman.target == 'nasabah_spesifik' and not nas_id:
            flash('Pilih nasabah terlebih dahulu untuk pengumuman spesifik.', 'danger')
            return redirect(url_for('pengaturan.pengumuman_edit', id=id))
            
        pengumuman.nasabah_id_fk = int(nas_id) if (pengumuman.target == 'nasabah_spesifik' and nas_id) else None
        pengumuman.aktif = 'aktif' in request.form
        db.session.commit()
        flash('Pengumuman berhasil diperbarui.', 'success')
        return redirect(url_for('pengaturan.pengumuman'))
    return render_template('pengaturan/pengumuman_form.html', pengumuman=pengumuman)


@pengaturan_bp.route('/pengumuman/hapus/<int:id>', methods=['POST'])
@login_required
def pengumuman_hapus(id):
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    p = Pengumuman.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Pengumuman berhasil dihapus.', 'success')
    return redirect(url_for('pengaturan.pengumuman'))


@pengaturan_bp.route('/pengumuman/toggle/<int:id>', methods=['POST'])
@login_required
def pengumuman_toggle(id):
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)
    p = Pengumuman.query.get_or_404(id)
    p.aktif = not p.aktif
    db.session.commit()
    status = 'diaktifkan' if p.aktif else 'dinonaktifkan'
    flash(f'Pengumuman berhasil {status}.', 'success')
    return redirect(url_for('pengaturan.pengumuman'))


@pengaturan_bp.route('/pengumuman/<int:id>')
@login_required
def pengumuman_detail(id):
    pg = Pengumuman.query.get_or_404(id)
    # Admin/Manajer can always see
    if current_user.is_admin() or current_user.role == 'manajer_lkd':
        return render_template('pengaturan/pengumuman_detail.html', pg=pg)
        
    # Nasabah checks
    if not pg.aktif:
        abort(403)
        
    if current_user.is_nasabah():
        if pg.target == 'nasabah_spesifik' and pg.nasabah_id_fk != current_user.nasabah_id_fk:
            abort(403)
            
    return render_template('pengaturan/pengumuman_detail.html', pg=pg)


@pengaturan_bp.route('/rekening-pembayaran')
@login_required
def rekening_pembayaran():
    if not current_user.is_admin(): abort(403)
    rekening_list = RekeningPembayaran.query.order_by(RekeningPembayaran.urutan).all()
    return render_template('pengaturan/rekening_pembayaran.html', rekening_list=rekening_list)


@pengaturan_bp.route('/rekening-pembayaran/tambah', methods=['POST'])
@login_required
def tambah_rekening():
    if not current_user.is_admin(): abort(403)
    rekening = RekeningPembayaran(
        nama_bank=request.form.get('nama_bank'),
        nama_rekening=request.form.get('nama_rekening'),
        nomor_rekening=request.form.get('nomor_rekening'),
        aktif=request.form.get('aktif') == 'on',
        urutan=int(request.form.get('urutan', 0))
    )
    db.session.add(rekening)
    db.session.commit()
    flash('Rekening pembayaran berhasil ditambahkan.', 'success')
    return redirect(url_for('pengaturan.rekening_pembayaran'))


@pengaturan_bp.route('/rekening-pembayaran/<int:id>/edit', methods=['POST'])
@login_required
def edit_rekening(id):
    if not current_user.is_admin(): abort(403)
    rekening = RekeningPembayaran.query.get_or_404(id)
    rekening.nama_bank = request.form.get('nama_bank')
    rekening.nama_rekening = request.form.get('nama_rekening')
    rekening.nomor_rekening = request.form.get('nomor_rekening')
    rekening.aktif = request.form.get('aktif') == 'on'
    rekening.urutan = int(request.form.get('urutan', 0))
    db.session.commit()
    flash('Rekening pembayaran berhasil diperbarui.', 'success')
    return redirect(url_for('pengaturan.rekening_pembayaran'))


@pengaturan_bp.route('/rekening-pembayaran/<int:id>/hapus', methods=['POST'])
@login_required
def hapus_rekening(id):
    if not current_user.is_admin(): abort(403)
    rekening = RekeningPembayaran.query.get_or_404(id)
    db.session.delete(rekening)
    db.session.commit()
    flash('Rekening pembayaran berhasil dihapus.', 'success')
    return redirect(url_for('pengaturan.rekening_pembayaran'))


@pengaturan_bp.route('/bonus', methods=['GET', 'POST'])
@login_required
def bonus():
    if not current_user.is_admin(): abort(403)

    if request.method == 'POST':
        import json, traceback
        
        try:
            data = {}
            for key in request.form:
                if key.startswith('persen_'):
                    tahun = key.replace('persen_', '').strip()
                    if tahun == 'baru':
                        continue
                    raw = request.form.get(key, '').strip()
                    if not tahun or not raw:
                        continue
                    try:
                        val = float(raw)
                        if val < 0 or val > 100:
                            flash(f'Persentase untuk tahun {tahun} harus antara 0-100.', 'warning')
                            return redirect(url_for('pengaturan.bonus'))
                        data[tahun] = val
                    except (ValueError, TypeError):
                        flash(f'Nilai persentase tidak valid untuk tahun {tahun}: "{raw}"', 'warning')
                        return redirect(url_for('pengaturan.bonus'))
            
            tahun_baru = request.form.get('tahun_baru', '').strip()
            persen_baru = request.form.get('persen_baru', '').strip()
            if tahun_baru and persen_baru:
                try:
                    data[tahun_baru] = float(persen_baru)
                except (ValueError, TypeError):
                    flash(f'Nilai persentase tidak valid untuk tahun baru: "{persen_baru}"', 'warning')
                    return redirect(url_for('pengaturan.bonus'))
            
            if data:
                Pengaturan.set('bonus_persen', json.dumps(data), 'Persentase bonus per tahun')
                
            pembina_persen = request.form.get('pembina_persen', '').strip()
            if pembina_persen:
                try:
                    val = float(pembina_persen)
                    if val < 0 or val > 100:
                        flash('Persentase untuk pembina harus antara 0-100.', 'warning')
                        return redirect(url_for('pengaturan.bonus'))
                    Pengaturan.set('bonus_pembina_persen', str(val), 'Persentase potong bonus untuk pembina')
                except (ValueError, TypeError):
                    flash('Nilai persentase pembina tidak valid.', 'warning')
                    return redirect(url_for('pengaturan.bonus'))
            else:
                Pengaturan.set('bonus_pembina_persen', '20', 'Persentase potong bonus untuk pembina')
            
            db.session.commit()
            flash('Pengaturan bonus berhasil disimpan.', 'success')
         
        except Exception:
            db.session.rollback()
            tb = traceback.format_exc()
            current_app.logger.error(f'Error saving bonus settings:\n{tb}')
            flash('Gagal menyimpan pengaturan bonus. Periksa log untuk detail.', 'danger')
        
        return redirect(url_for('pengaturan.bonus'))

    import json
    json_str = Pengaturan.get('bonus_persen', '')
    percentage_map = {}
    try:
        if json_str:
            percentage_map = json.loads(json_str)
    except Exception:
        pass

    if not percentage_map:
        percentage_map = {'2022': 20.0, '2023': 10.0, '2024': 5.0, '2025': 2.0}
        Pengaturan.set('bonus_persen', json.dumps(percentage_map), 'Persentase bonus per tahun')
        db.session.commit()
    else:
        cleaned = {}
        for k, v in percentage_map.items():
            try:
                int(k)
                cleaned[k] = v
            except (ValueError, TypeError):
                pass
        if len(cleaned) != len(percentage_map):
            percentage_map = cleaned
            Pengaturan.set('bonus_persen', json.dumps(percentage_map), 'Persentase bonus per tahun')
            db.session.commit()

    tahun_list = sorted([int(t) for t in percentage_map.keys()])
    
    pembina_persen = Pengaturan.get('bonus_pembina_persen', '20')

    return render_template('pengaturan/bonus.html',
        percentage_map=percentage_map,
        tahun_list=tahun_list,
        pembina_persen=pembina_persen)


# ── TUTUP BUKU ────────────────────────────────────────────────
@pengaturan_bp.route('/tutup-buku', methods=['GET', 'POST'])
@login_required
def tutup_buku():
    if not (current_user.is_admin() or current_user.role == 'manajer_lkd'): abort(403)

    from datetime import date
    import json

    tahun_sekarang = date.today().year

    # Baca tahun yang sudah ditutup
    tutup_buku_json = Pengaturan.get('tutup_buku', '{}')
    try: tutup_buku_map = json.loads(tutup_buku_json)
    except: tutup_buku_map = {}

    if request.method == 'POST':
        tahun = request.form.get('tahun', type=int)
        if not tahun or tahun < 2020 or tahun > tahun_sekarang:
            flash('Tahun tidak valid.', 'danger')
            return redirect(url_for('pengaturan.tutup_buku'))

        if str(tahun) in tutup_buku_map:
            flash(f'Tahun {tahun} sudah ditutup sebelumnya.', 'warning')
            return redirect(url_for('pengaturan.tutup_buku'))

        tgl_akhir = date(tahun, 12, 31)

        laba_ditahan = AkunCOA.query.filter_by(kode='3.3.01.01').first()
        if not laba_ditahan:
            flash('Akun Saldo Laba Tidak Dicadangkan (3.3.01.01) tidak ditemukan!', 'danger')
            return redirect(url_for('pengaturan.tutup_buku'))

        akun_list = AkunCOA.query.filter(
            AkunCOA.golongan.in_([4, 5, 6, 7]),
            AkunCOA.bisa_jurnal == True,
            AkunCOA.aktif == True
        ).all()

        details = []
        total_debit = 0
        total_kredit = 0

        for akun in akun_list:
            saldo = akun.get_saldo(None, tgl_akhir, exclude_tipe=['tutup_buku'])
            if saldo == 0:
                continue
            if akun.saldo_normal == 'kredit':
                details.append({'akun': akun, 'debit': saldo, 'kredit': 0})
                total_debit += saldo
            else:
                details.append({'akun': akun, 'debit': 0, 'kredit': saldo})
                total_kredit += saldo

        selisih = total_debit - total_kredit
        if selisih > 0:
            details.append({'akun': laba_ditahan, 'debit': 0, 'kredit': selisih})
            total_kredit += selisih
        elif selisih < 0:
            details.append({'akun': laba_ditahan, 'debit': -selisih, 'kredit': 0})
            total_debit += -selisih

        if not details:
            flash('Tidak ada saldo yang perlu ditutup untuk tahun ini.', 'info')
            return redirect(url_for('pengaturan.tutup_buku'))

        if total_debit != total_kredit:
            flash('Jurnal penutup tidak balance!', 'danger')
            return redirect(url_for('pengaturan.tutup_buku'))

        no_jurnal = f"JU-TB/{tahun}/{date.today().strftime('%m%d')}/001"
        jurnal = JurnalUmum(
            no_jurnal=no_jurnal,
            tanggal=tgl_akhir,
            keterangan=f'Jurnal Penutup Tahun Buku {tahun}',
            referensi='Tutup Buku',
            tipe='tutup_buku',
            status='posted',
            total_debit=total_debit,
            total_kredit=total_kredit,
            created_by=current_user.id
        )
        db.session.add(jurnal)

        for d in details:
            jd = JurnalDetail(
                jurnal=jurnal,
                akun_id=d['akun'].id,
                debit=d['debit'],
                kredit=d['kredit'],
                keterangan=f'Penutupan {d["akun"].nama}'
            )
            db.session.add(jd)

        tutup_buku_map[str(tahun)] = {
            'tanggal': tgl_akhir.isoformat(),
            'laba_berjalan': abs(selisih),
            'dicatat_oleh': current_user.nama_lengkap or current_user.username
        }
        Pengaturan.set('tutup_buku', json.dumps(tutup_buku_map), 'Tahun-tahun yang sudah ditutup')
        db.session.commit()

        flash(f'Tutup buku tahun {tahun} berhasil. {len(details)} akun ditutup.', 'success')
        return redirect(url_for('pengaturan.tutup_buku'))

    tahun_list = sorted([t for t in range(2020, tahun_sekarang + 1)], reverse=True)

    ringkasan = {}
    for t in tahun_list:
        str_t = str(t)
        if str_t in tutup_buku_map:
            ringkasan[t] = {'status': 'ditutup', 'info': tutup_buku_map[str_t], 'data': None}
        else:
            tgl = date(t, 12, 31)
            laba = (_sum_golongan_pengaturan(4, tgl) + _sum_golongan_pengaturan(7, tgl)
                    - _sum_golongan_pengaturan(5, tgl) - _sum_golongan_pengaturan(6, tgl))
            ringkasan[t] = {'status': 'terbuka', 'info': None, 'data': {'laba_berjalan': laba}}

    return render_template('pengaturan/tutup_buku.html',
        tahun_sekarang=tahun_sekarang,
        tahun_list=tahun_list,
        ringkasan=ringkasan)


def _sum_golongan_pengaturan(gol, tgl_sampai):
    """Helper untuk menghitung total golongan di pengaturan route."""
    akuns = AkunCOA.query.filter_by(golongan=gol, bisa_jurnal=True, aktif=True).all()
    return sum(a.get_saldo(None, tgl_sampai, exclude_tipe=['tutup_buku']) for a in akuns)
