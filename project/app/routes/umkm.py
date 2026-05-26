from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ..models import db, Nasabah, ProdukUMKM, PesananUMKM, DetailPesananUMKM, PengajuanPenjual, RekeningPembayaran
from ..utils.helpers import save_file
from datetime import datetime

umkm_bp = Blueprint('umkm', __name__, url_prefix='/umkm')

def get_or_create_nasabah_for_kader():
    """Get or create a Nasabah record for kader user (for UMKM purposes)."""
    if not (current_user.is_nasabah() or current_user.is_kader()):
        return None
    
    if current_user.is_nasabah():
        if current_user.nasabah_id_fk:
            return current_user.nasabah_id_fk
        if current_user.nasabah:
            return current_user.nasabah.id
        return None
    
    if current_user.is_kader():
        if current_user.nasabah_id_fk:
            return current_user.nasabah_id_fk
        
        existing = Nasabah.query.filter(
            Nasabah.nik == f'KADER-{current_user.id}',
            Nasabah.jenis == 'perorangan'
        ).first()
        
        if existing:
            return existing.id
        
        from ..utils.helpers import get_next_nasabah_id
        from config import Config
        kode_desa = current_user.kode_desa or list(Config.DESA_LIST)[0][0] if Config.DESA_LIST else 'DESA001'
        nama_desa = dict(Config.DESA_LIST).get(kode_desa, 'Unknown')
        nasabah_id = get_next_nasabah_id(kode_desa, start_from=899)
        
        new_nasabah = Nasabah(
            nasabah_id=nasabah_id,
            jenis='perorangan',
            kode_desa=kode_desa,
            nama_desa=nama_desa,
            nama=current_user.nama_lengkap or f'KADER-{current_user.username}',
            nik=f'KADER-{current_user.id}',
            status='aktif',
            keterangan_status='Akun kader otomatis untuk fitur UMKM.',
            created_by=current_user.id
        )
        db.session.add(new_nasabah)
        db.session.flush()
        
        current_user.nasabah_id_fk = new_nasabah.id
        db.session.commit()
        
        return new_nasabah.id

def get_current_nasabah_id():
    """Safely get current user for umum purposes."""
    if not (current_user.is_nasabah() or current_user.is_kader()):
        return None
    if current_user.nasabah_id_fk:
        return current_user.nasabah_id_fk
    if current_user.nasabah:
        return current_user.nasabah.id
    return None




# ═══════════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════════

@umkm_bp.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.can_edit_delete():
        abort(403)
    
    total_produk = ProdukUMKM.query.count()
    produk_aktif = ProdukUMKM.query.filter_by(aktif=True).count()
    total_pesanan = PesananUMKM.query.count()
    pesanan_menunggu = PesananUMKM.query.filter_by(status='menunggu').count()
    pengajuan_menunggu = PengajuanPenjual.query.filter_by(status='menunggu').count()
    pesanan_belum_bayar = PesananUMKM.query.filter_by(status='menunggu', status_pembayaran='belum_bayar').count()
    pesanan_menunggu_konfirmasi = PesananUMKM.query.filter_by(status_pembayaran='menunggu_konfirmasi').count()
    
    return render_template('umkm/admin/dashboard.html',
                          total_produk=total_produk,
                          produk_aktif=produk_aktif,
                          total_pesanan=total_pesanan,
                          pesanan_menunggu=pesanan_menunggu,
                          pengajuan_menunggu=pengajuan_menunggu,
                          pesanan_belum_bayar=pesanan_belum_bayar,
                          pesanan_menunggu_konfirmasi=pesanan_menunggu_konfirmasi)


@umkm_bp.route('/admin/produk')
@login_required
def admin_produk():
    if not current_user.can_edit_delete():
        abort(403)
    
    kategori = request.args.get('kategori', '')
    status = request.args.get('status', '')
    
    query = ProdukUMKM.query
    
    if kategori:
        query = query.filter_by(kategori=kategori)
    if status == 'aktif':
        query = query.filter_by(aktif=True)
    elif status == 'nonaktif':
        query = query.filter_by(aktif=False)
    
    produk_list = query.order_by(ProdukUMKM.tanggal_dibuat.desc()).all()
    
    return render_template('umkm/admin/produk.html',
                          produk_list=produk_list,
                          kategori=kategori,
                          status=status)


@umkm_bp.route('/admin/produk/tambah', methods=['GET', 'POST'])
@login_required
def admin_tambah_produk():
    if not current_user.can_edit_delete():
        abort(403)
    
    if request.method == 'POST':
        penjual_id = request.form.get('penjual_id')
        nama_produk = request.form.get('nama_produk')
        deskripsi = request.form.get('deskripsi', '')
        kategori = request.form.get('kategori')
        harga = int(request.form.get('harga', 0))
        stok = int(request.form.get('stok', 0))
        satuan = request.form.get('satuan', 'pcs')
        aktif = request.form.get('aktif') == 'on'
        
        produk = ProdukUMKM(
            penjual_id=penjual_id,
            nama_produk=nama_produk,
            deskripsi=deskripsi,
            kategori=kategori,
            harga=harga,
            stok=stok,
            satuan=satuan,
            aktif=aktif
        )
        db.session.add(produk)
        db.session.flush()
        
        gambar = request.files.get('gambar')
        if gambar and gambar.filename:
            produk.gambar = save_file(gambar, 'umkm', f'admin_produk_{produk.id}')
        
        db.session.commit()
        flash('Produk berhasil ditambahkan.', 'success')
        return redirect(url_for('umkm.admin_produk'))
    
    penjual_list = Nasabah.query.join(PengajuanPenjual).filter(
        PengajuanPenjual.status == 'disetujui'
    ).distinct().all()
    
    return render_template('umkm/admin/form_produk.html',
                          penjual_list=penjual_list,
                          produk=None)


@umkm_bp.route('/admin/produk/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_produk(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    produk = ProdukUMKM.query.get_or_404(id)
    
    if request.method == 'POST':
        produk.penjual_id = request.form.get('penjual_id')
        produk.nama_produk = request.form.get('nama_produk')
        produk.deskripsi = request.form.get('deskripsi', '')
        produk.kategori = request.form.get('kategori')
        produk.harga = int(request.form.get('harga', 0))
        produk.stok = int(request.form.get('stok', 0))
        produk.satuan = request.form.get('satuan', 'pcs')
        produk.aktif = request.form.get('aktif') == 'on'
        
        gambar = request.files.get('gambar')
        if gambar and gambar.filename:
            produk.gambar = save_file(gambar, 'umkm', f'admin_produk_{produk.id}')
        
        db.session.commit()
        flash('Produk berhasil diperbarui.', 'success')
        return redirect(url_for('umkm.admin_produk'))
    
    penjual_list = Nasabah.query.join(PengajuanPenjual).filter(
        PengajuanPenjual.status == 'disetujui'
    ).distinct().all()
    
    return render_template('umkm/admin/form_produk.html',
                          penjual_list=penjual_list,
                          produk=produk)


@umkm_bp.route('/admin/produk/<int:id>/hapus', methods=['POST'])
@login_required
def admin_hapus_produk(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    produk = ProdukUMKM.query.get_or_404(id)
    db.session.delete(produk)
    db.session.commit()
    flash('Produk berhasil dihapus.', 'success')
    return redirect(url_for('umkm.admin_produk'))


@umkm_bp.route('/admin/pesanan')
@login_required
def admin_pesanan():
    if not current_user.can_edit_delete():
        abort(403)
    
    tab = request.args.get('tab', 'pesanan')
    status = request.args.get('status', '')
    status_pembayaran = request.args.get('status_pembayaran', '')
    
    query = PesananUMKM.query
    
    if tab == 'pesanan' and status:
        query = query.filter_by(status=status)
    elif tab == 'pembayaran' and status_pembayaran:
        query = query.filter_by(status_pembayaran=status_pembayaran)
    
    pesanan_list = query.order_by(PesananUMKM.tanggal_pesanan.desc()).all()
    
    return render_template('umkm/admin/pesanan.html',
                          pesanan_list=pesanan_list,
                          status=status,
                          status_pembayaran=status_pembayaran,
                          tab=tab)


@umkm_bp.route('/admin/pesanan/<id>/detail')
@login_required
def admin_detail_pesanan(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    pesanan = PesananUMKM.query.filter_by(nomor_pesanan=id).first_or_404()
    
    return render_template('umkm/admin/detail_pesanan.html', pesanan=pesanan)


@umkm_bp.route('/admin/pesanan/<id>/proses', methods=['POST'])
@login_required
def admin_proses_pesanan(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    pesanan = PesananUMKM.query.filter_by(nomor_pesanan=id).first_or_404()
    
    # Update status pesanan
    status_baru = request.form.get('status')
    if status_baru and status_baru != pesanan.status:
        pesanan.status = status_baru
        if status_baru == 'diproses':
            pesanan.tanggal_diproses = datetime.utcnow()
        elif status_baru == 'selesai':
            pesanan.tanggal_selesai = datetime.utcnow()
    
    # Update status pembayaran
    status_pembayaran = request.form.get('status_pembayaran')
    if status_pembayaran and status_pembayaran != pesanan.status_pembayaran:
        pesanan.status_pembayaran = status_pembayaran
        if status_pembayaran == 'lunas':
            pesanan.tanggal_lunas = datetime.utcnow()
    
    # Update info pengiriman
    pesanan.kurir = request.form.get('kurir', '').strip() or None
    pesanan.nomor_resi = request.form.get('nomor_resi', '').strip() or None
    pesanan.alamat_pengiriman = request.form.get('alamat_pengiriman', '').strip() or None
    
    if (request.form.get('tanggal_kirim') and 
        pesanan.status == 'dikirim' and 
        not pesanan.tanggal_kirim):
        pesanan.tanggal_kirim = datetime.utcnow()
    
    # Catatan admin
    pesanan.catatan_admin = request.form.get('catatan_admin', '').strip() or None
    
    db.session.commit()
    flash('Pesanan berhasil diperbarui.', 'success')
    return redirect(url_for('umkm.admin_detail_pesanan', id=pesanan.nomor_pesanan))


@umkm_bp.route('/admin/pesanan/<id>/konfirmasi-pembayaran', methods=['POST'])
@login_required
def admin_konfirmasi_pembayaran(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    pesanan = PesananUMKM.query.filter_by(nomor_pesanan=id).first_or_404()
    
    if pesanan.status_pembayaran != 'menunggu_konfirmasi':
        flash('Pesanan tidak menunggu konfirmasi pembayaran.', 'warning')
        return redirect(url_for('umkm.admin_detail_pesanan', id=pesanan.nomor_pesanan))
    
    action = request.form.get('action')
    
    if action == 'terima':
        pesanan.status_pembayaran = 'lunas'
        pesanan.tanggal_lunas = datetime.utcnow()
        flash('Pembayaran telah dikonfirmasi. Pesanan siap diproses.', 'success')
    elif action == 'tolak':
        pesanan.status_pembayaran = 'gagal'
        pesanan.catatan_admin = (pesanan.catatan_admin or '') + f"\n[Pembayaran Ditolak] " + request.form.get('alasan', '')
        flash('Pembayaran ditolak.', 'warning')
    
    db.session.commit()
    return redirect(url_for('umkm.admin_detail_pesanan', id=pesanan.nomor_pesanan))


@umkm_bp.route('/admin/pembayaran')
@login_required
def admin_pembayaran():
    if not current_user.can_edit_delete():
        abort(403)
    
    rekening_list = RekeningPembayaran.query.order_by(RekeningPembayaran.urutan).all()
    return render_template('umkm/admin/pembayaran.html', rekening_list=rekening_list)


@umkm_bp.route('/admin/pembayaran/tambah', methods=['POST'])
@login_required
def admin_tambah_rekening():
    if not current_user.can_edit_delete():
        abort(403)
    
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
    return redirect(url_for('umkm.admin_pembayaran'))


@umkm_bp.route('/admin/pembayaran/<int:id>/edit', methods=['POST'])
@login_required
def admin_edit_rekening(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    rekening = RekeningPembayaran.query.get_or_404(id)
    rekening.nama_bank = request.form.get('nama_bank')
    rekening.nama_rekening = request.form.get('nama_rekening')
    rekening.nomor_rekening = request.form.get('nomor_rekening')
    rekening.aktif = request.form.get('aktif') == 'on'
    rekening.urutan = int(request.form.get('urutan', 0))
    db.session.commit()
    flash('Rekening pembayaran berhasil diperbarui.', 'success')
    return redirect(url_for('umkm.admin_pembayaran'))


@umkm_bp.route('/admin/pembayaran/<int:id>/hapus', methods=['POST'])
@login_required
def admin_hapus_rekening(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    rekening = RekeningPembayaran.query.get_or_404(id)
    db.session.delete(rekening)
    db.session.commit()
    flash('Rekening pembayaran berhasil dihapus.', 'success')
    return redirect(url_for('umkm.admin_pembayaran'))


@umkm_bp.route('/admin/penjual')
@login_required
def admin_penjual():
    if not current_user.can_edit_delete():
        abort(403)
    
    status = request.args.get('status', 'menunggu')
    
    query = PengajuanPenjual.query
    
    if status != 'semua':
        query = query.filter_by(status=status)
    
    pengajuan_list = query.order_by(PengajuanPenjual.tanggal_ajuan.desc()).all()
    
    return render_template('umkm/admin/penjual.html',
                          pengajuan_list=pengajuan_list,
                          status=status)


@umkm_bp.route('/admin/penjual/<int:id>/proses', methods=['POST'])
@login_required
def admin_proses_penjual(id):
    if not current_user.can_edit_delete():
        abort(403)
    
    pengajuan = PengajuanPenjual.query.get_or_404(id)
    action = request.form.get('action')
    catatan = request.form.get('catatan', '')
    
    if action == 'setujui':
        pengajuan.status = 'disetujui'
        pengajuan.tanggal_respon = datetime.utcnow()
        pengajuan.admin_id = current_user.id
        pengajuan.catatan_admin = catatan
        flash(f'Pengajuan penjual untuk {pengajuan.nasabah.nama} telah disetujui.', 'success')
    elif action == 'tolak':
        pengajuan.status = 'ditolak'
        pengajuan.tanggal_respon = datetime.utcnow()
        pengajuan.admin_id = current_user.id
        pengajuan.catatan_admin = catatan
        flash(f'Pengajuan penjual untuk {pengajuan.nasabah.nama} telah ditolak.', 'warning')
    
    db.session.commit()
    return redirect(url_for('umkm.admin_penjual', status=request.args.get('status', 'menunggu')))


# ═══════════════════════════════════════════════
# NASABAH ROUTES
# ═══════════════════════════════════════════════

@umkm_bp.route('/')
@login_required
def katalog():
    kategori = request.args.get('kategori', '')
    cari = request.args.get('cari', '')
    
    query = ProdukUMKM.query.filter_by(aktif=True)
    
    if kategori:
        query = query.filter_by(kategori=kategori)
    if cari:
        query = query.filter(ProdukUMKM.nama_produk.ilike(f'%{cari}%'))
    
    produk_list = query.order_by(ProdukUMKM.tanggal_dibuat.desc()).all()
    
    return render_template('umkm/nasabah/katalog.html',
                          produk_list=produk_list,
                          kategori=kategori,
                          cari=cari)


@umkm_bp.route('/produk/<int:id>')
@login_required
def detail_produk(id):
    produk = ProdukUMKM.query.get_or_404(id)
    
    if not produk.aktif:
        flash('Produk tidak tersedia.', 'warning')
        return redirect(url_for('umkm.katalog'))
    
    return render_template('umkm/nasabah/detail_produk.html', produk=produk)


@umkm_bp.route('/pesan', methods=['GET', 'POST'])
@login_required
def pesan():
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    if request.method == 'POST':
        from flask import current_app
        target_nasabah_id = get_or_create_nasabah_for_kader()
        if not target_nasabah_id:
            flash('Data rekening tidak ditemukan.', 'danger')
            return redirect(url_for('umkm.katalog'))
        
        pesanan_belum_selesai = PesananUMKM.query.filter(
            PesananUMKM.pembeli_id == target_nasabah_id,
            PesananUMKM.status.in_(['menunggu', 'diproses', 'dikirim'])
        ).first()
        
        if pesanan_belum_selesai:
            flash(f'Anda memiliki pesanan yang belum selesai (No. {pesanan_belum_selesai.nomor_pesanan}). Selesaikan atau batalkan pesanan tersebut terlebih dahulu sebelum melakukan pemesanan baru.', 'warning')
            return redirect(url_for('umkm.pesanan_saya'))
        
        produk_id = request.form.get('produk_id')
        if not produk_id:
            flash('Produk tidak ditemukan.', 'danger')
            return redirect(url_for('umkm.katalog'))
        
        try:
            produk_id = int(produk_id)
        except (ValueError, TypeError):
            flash('Produk tidak valid.', 'danger')
            return redirect(url_for('umkm.katalog'))
        
        try:
            jumlah = int(request.form.get('jumlah', 1))
            if jumlah < 1:
                flash('Jumlah pesanan minimal 1.', 'danger')
                return redirect(url_for('umkm.katalog'))
        except (ValueError, TypeError):
            flash('Jumlah pesanan tidak valid.', 'danger')
            return redirect(url_for('umkm.katalog'))
        
        catatan = request.form.get('catatan', '') or ''
        
        try:
            produk = ProdukUMKM.query.get_or_404(produk_id)
        except Exception as e:
            flash(f'Produk tidak ditemukan: {str(e)}', 'danger')
            return redirect(url_for('umkm.katalog'))
        
        if not produk.aktif:
            flash('Produk tidak tersedia.', 'danger')
            return redirect(url_for('umkm.katalog'))
        
        if produk.stok < jumlah:
            flash(f'Stok tidak mencukupi. Stok tersedia: {produk.stok}', 'danger')
            return redirect(url_for('umkm.detail_produk', id=produk.id))
        
        try:
            nomor_pesanan = f"UMKM-{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}-{target_nasabah_id}"
             
            pesanan = PesananUMKM(
                nomor_pesanan=nomor_pesanan,
                pembeli_id=target_nasabah_id,
                penjual_id=produk.penjual_id,
                total_harga=produk.harga * jumlah,
                catatan_pembeli=catatan
            )
            db.session.add(pesanan)
            db.session.flush()
            
            detail = DetailPesananUMKM(
                pesanan_id=pesanan.id,
                produk_id=produk.id,
                jumlah=jumlah,
                harga_satuan=produk.harga,
                subtotal=produk.harga * jumlah
            )
            db.session.add(detail)
            
            produk.stok -= jumlah
            db.session.commit()
            
            flash('Pesanan berhasil dibuat! Silakan lakukan pembayaran.', 'success')
            return redirect(url_for('umkm.bayar_pesanan', id=pesanan.nomor_pesanan))
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal membuat pesanan: {str(e)}', 'danger')
            return redirect(url_for('umkm.katalog'))
    
    return redirect(url_for('umkm.katalog'))


@umkm_bp.route('/pesanan-saya')
@login_required
def pesanan_saya():
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pesanan_list = PesananUMKM.query.filter_by(
        pembeli_id=target_nasabah_id
    ).order_by(PesananUMKM.tanggal_pesanan.desc()).all()
    
    return render_template('umkm/nasabah/pesanan_saya.html',
                          pesanan_list=pesanan_list)


@umkm_bp.route('/pesanan/<id>/batal', methods=['POST'])
@login_required
def batal_pesanan(id):
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pesanan = PesananUMKM.query.filter_by(
        nomor_pesanan=id,
        pembeli_id=target_nasabah_id
    ).first()
    
    if not pesanan:
        flash('Pesanan tidak ditemukan.', 'danger')
        return redirect(url_for('umkm.pesanan_saya'))
    
    if pesanan.status_pembayaran != 'belum_bayar':
        flash('Pesanan sudah dibayar dan tidak dapat dibatalkan.', 'danger')
        return redirect(url_for('umkm.pesanan_saya'))
    
    if pesanan.status == 'dibatalkan':
        flash('Pesanan sudah dibatalkan.', 'warning')
        return redirect(url_for('umkm.pesanan_saya'))
    
    pesanan.status = 'dibatalkan'
    pesanan.status_pembayaran = 'dibatalkan'
    
    for detail in pesanan.detail_list:
        produk = detail.produk
        produk.stok += detail.jumlah
    
    db.session.commit()
    flash('Pesanan berhasil dibatalkan.', 'success')
    return redirect(url_for('umkm.pesanan_saya'))


@umkm_bp.route('/pesanan/<id>')
@login_required
def detail_pesanan_nasabah(id):
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pesanan = PesananUMKM.query.filter_by(
        nomor_pesanan=id,
        pembeli_id=target_nasabah_id
    ).first_or_404()
    
    return render_template('umkm/nasabah/detail_pesanan.html', pesanan=pesanan)


@umkm_bp.route('/pesanan/<id>/bayar', methods=['GET', 'POST'])
@login_required
def bayar_pesanan(id):
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    try:
        target_nasabah_id = get_or_create_nasabah_for_kader()
        if not target_nasabah_id:
            flash('Data rekening tidak ditemukan.', 'danger')
            return redirect(url_for('umkm.pesanan_saya'))
        
        pesanan = PesananUMKM.query.filter_by(
            nomor_pesanan=id,
            pembeli_id=target_nasabah_id
        ).first()
        
        if not pesanan:
            flash('Pesanan tidak ditemukan.', 'warning')
            return redirect(url_for('umkm.pesanan_saya'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('umkm.pesanan_saya'))
    
    if pesanan.status_pembayaran not in ['belum_bayar', 'gagal']:
        flash('Pesanan ini sudah dibayar atau tidak dapat dibayar.', 'warning')
        return redirect(url_for('umkm.detail_pesanan_nasabah', id=pesanan.nomor_pesanan))
    
    rekening_list = RekeningPembayaran.query.filter_by(aktif=True).order_by(RekeningPembayaran.urutan).all()
    rekening_data = [{
        'id': r.id,
        'nama_bank': r.nama_bank,
        'nama_rekening': r.nama_rekening,
        'nomor_rekening': r.nomor_rekening
    } for r in rekening_list]
    
    if request.method == 'POST':
        pesanan.metode_pembayaran = request.form.get('metode_pembayaran')
        
        if not pesanan.metode_pembayaran:
            flash('Silakan pilih metode pembayaran.', 'warning')
            return render_template('umkm/nasabah/bayar_pesanan.html', 
                                  pesanan=pesanan, 
                                  rekening_list=rekening_list,
                                  rekening_data=rekening_data)
        
        if pesanan.metode_pembayaran == 'cod':
            pesanan.status_pembayaran = 'menunggu_konfirmasi'
            flash('Pesanan COD telah dipesan. Silakan disiapkan uang saat paket diterima.', 'success')
        else:
            bukti = request.files.get('bukti_pembayaran')
            if bukti and bukti.filename:
                try:
                    pesanan.bukti_pembayaran = save_file(bukti, 'umkm', f'bukti_{pesanan.id}')
                    pesanan.status_pembayaran = 'menunggu_konfirmasi'
                    flash('Bukti pembayaran berhasil dikirim. Menunggu konfirmasi admin.', 'success')
                except Exception as e:
                    flash(f'Gagal upload bukti: {str(e)}', 'danger')
                    return render_template('umkm/nasabah/bayar_pesanan.html', 
                                          pesanan=pesanan, 
                                          rekening_list=rekening_list,
                                          rekening_data=rekening_data)
            else:
                flash('Silakan upload bukti pembayaran.', 'warning')
                return render_template('umkm/nasabah/bayar_pesanan.html', 
                                      pesanan=pesanan, 
                                      rekening_list=rekening_list,
                                      rekening_data=rekening_data)
        
        try:
            db.session.commit()
            return redirect(url_for('umkm.detail_pesanan_nasabah', id=pesanan.nomor_pesanan))
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal menyimpan: {str(e)}', 'danger')
            return render_template('umkm/nasabah/bayar_pesanan.html', 
                                  pesanan=pesanan, 
                                  rekening_list=rekening_list,
                                  rekening_data=rekening_data)
    
    return render_template('umkm/nasabah/bayar_pesanan.html', 
                          pesanan=pesanan, 
                          rekening_list=rekening_list,
                          rekening_data=rekening_data)


@umkm_bp.route('/pesanan/<id>/konfirmasi-bayar', methods=['POST'])
@login_required
def konfirmasi_bayar(id):
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pesanan = PesananUMKM.query.filter_by(
        nomor_pesanan=id,
        pembeli_id=target_nasabah_id
    ).first_or_404()
    
    if pesanan.status_pembayaran != 'menunggu_konfirmasi':
        flash('Pesanan tidak menunggu konfirmasi pembayaran.', 'warning')
        return redirect(url_for('umkm.detail_pesanan_nasabah', id=pesanan.nomor_pesanan))
    
    bukti = request.files.get('bukti_pembayaran')
    if bukti and bukti.filename:
        pesanan.bukti_pembayaran = save_file(bukti, 'umkm', f'bukti_{pesanan.id}')
    
    db.session.commit()
    flash('Bukti pembayaran berhasil diupload.', 'success')
    return redirect(url_for('umkm.detail_pesanan_nasabah', id=pesanan.nomor_pesanan))


@umkm_bp.route('/penjual/ajukan', methods=['GET', 'POST'])
@login_required
def ajukan_penjual():
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    existing = PengajuanPenjual.query.filter_by(
        nasabah_id=target_nasabah_id,
        status='menunggu'
    ).first()
    
    if existing:
        flash('Anda sudah memiliki pengajuan yang menunggu persetujuan.', 'warning')
        return redirect(url_for('umkm.status_penjual'))
    
    approved = PengajuanPenjual.query.filter_by(
        nasabah_id=target_nasabah_id,
        status='disetujui'
    ).first()
    
    if approved:
        flash('Anda sudah terdaftar sebagai penjual.', 'info')
        return redirect(url_for('umkm.status_penjual'))
    
    if request.method == 'POST':
        pengajuan = PengajuanPenjual(
            nasabah_id=target_nasabah_id,
            nama_usaha=request.form.get('nama_usaha'),
            jenis_usaha=request.form.get('jenis_usaha', ''),
            deskripsi=request.form.get('deskripsi', ''),
            no_hp_usaha=request.form.get('no_hp_usaha', ''),
            alamat_usaha=request.form.get('alamat_usaha', '')
        )
        db.session.add(pengajuan)
        db.session.commit()
        
        flash('Pengajuan penjual berhasil dikirim. Menunggu persetujuan admin.', 'success')
        return redirect(url_for('umkm.status_penjual'))
    
    return render_template('umkm/nasabah/form_pengajuan_penjual.html')


@umkm_bp.route('/penjual/status')
@login_required
def status_penjual():
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pengajuan_list = PengajuanPenjual.query.filter_by(
        nasabah_id=target_nasabah_id
    ).order_by(PengajuanPenjual.tanggal_ajuan.desc()).all()
    
    is_penjual = any(p.status == 'disetujui' for p in pengajuan_list)
    
    return render_template('umkm/nasabah/status_penjual.html',
                          pengajuan_list=pengajuan_list,
                          is_penjual=is_penjual)


@umkm_bp.route('/penjual/produk')
@login_required
def penjual_produk():
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pengajuan = PengajuanPenjual.query.filter_by(
        nasabah_id=target_nasabah_id,
        status='disetujui'
    ).first()
    
    if not pengajuan:
        flash('Anda belum terdaftar sebagai penjual.', 'warning')
        return redirect(url_for('umkm.ajukan_penjual'))
    
    produk_list = ProdukUMKM.query.filter_by(
        penjual_id=target_nasabah_id
    ).order_by(ProdukUMKM.tanggal_dibuat.desc()).all()
    
    return render_template('umkm/nasabah/penjual_produk.html',
                          produk_list=produk_list)


@umkm_bp.route('/penjual/produk/tambah', methods=['GET', 'POST'])
@login_required
def penjual_tambah_produk():
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pengajuan = PengajuanPenjual.query.filter_by(
        nasabah_id=target_nasabah_id,
        status='disetujui'
    ).first()
    
    if not pengajuan:
        flash('Anda belum terdaftar sebagai penjual.', 'warning')
        return redirect(url_for('umkm.ajukan_penjual'))
    
    if request.method == 'POST':
        produk = ProdukUMKM(
            penjual_id=target_nasabah_id,
            nama_produk=request.form.get('nama_produk'),
            deskripsi=request.form.get('deskripsi', ''),
            kategori=request.form.get('kategori'),
            harga=int(request.form.get('harga', 0)),
            stok=int(request.form.get('stok', 0)),
            satuan=request.form.get('satuan', 'pcs'),
            aktif=request.form.get('aktif') == 'on'
        )
        db.session.add(produk)
        db.session.flush()
        
        gambar = request.files.get('gambar')
        if gambar and gambar.filename:
            produk.gambar = save_file(gambar, 'umkm', f'produk_{produk.id}')
        
        db.session.commit()
        flash('Produk berhasil ditambahkan.', 'success')
        return redirect(url_for('umkm.penjual_produk'))
    
    return render_template('umkm/nasabah/form_produk_penjual.html', produk=None)


@umkm_bp.route('/penjual/pesanan')
@login_required
def penjual_pesanan():
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    target_nasabah_id = get_or_create_nasabah_for_kader()
    if not target_nasabah_id:
        flash('Data rekening tidak ditemukan.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pengajuan = PengajuanPenjual.query.filter_by(
        nasabah_id=target_nasabah_id,
        status='disetujui'
    ).first()
    
    if not pengajuan:
        flash('Anda belum terdaftar sebagai penjual.', 'warning')
        return redirect(url_for('umkm.ajukan_penjual'))
    
    pesanan_list = PesananUMKM.query.filter_by(
        penjual_id=target_nasabah_id
    ).order_by(PesananUMKM.tanggal_pesanan.desc()).all()
    
    return render_template('umkm/nasabah/penjual_pesanan.html',
                          pesanan_list=pesanan_list)


@umkm_bp.route('/penjual/pesanan/<int:id>/proses', methods=['POST'])
@login_required
def penjual_proses_pesanan(id):
    if not (current_user.is_nasabah() or current_user.is_kader()):
        abort(403)
    
    nasabah_id = get_or_create_nasabah_for_kader()
    if not nasabah_id:
        abort(403)
    
    pesanan = PesananUMKM.query.get_or_404(id)
    
    if pesanan.penjual_id != nasabah_id:
        abort(403)
    
    action = request.form.get('action')
    
    if action == 'proses':
        pesanan.status = 'diproses'
        pesanan.tanggal_diproses = datetime.utcnow()
        flash('Pesanan telah diproses.', 'success')
    elif action == 'kirim':
        pesanan.status = 'dikirim'
        flash('Pesanan telah dikirim.', 'success')
    elif action == 'selesai':
        pesanan.status = 'selesai'
        pesanan.tanggal_selesai = datetime.utcnow()
        flash('Pesanan telah selesai.', 'success')
    
    db.session.commit()
    return redirect(url_for('umkm.penjual_pesanan'))
