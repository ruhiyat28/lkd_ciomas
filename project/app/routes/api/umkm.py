from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
import os, uuid, logging
from datetime import datetime, timezone
from ...models import db, Nasabah, User, ProdukUMKM, PesananUMKM, DetailPesananUMKM, RekeningPembayaran, PengajuanPenjual
from ...utils.helpers import save_file
from . import api_bp, get_current_user

logger = logging.getLogger(__name__)

def _get_penjual(user):
    if user.is_nasabah():
        return db.session.get(Nasabah, user.nasabah_id_fk)
    return None

def _penjual_or_403(user):
    if not user.is_nasabah():
        return None, (jsonify(success=False, message='Hanya untuk nasabah'), 403)
    penjual = _get_penjual(user)
    if not penjual:
        return None, (jsonify(success=False, message='Data nasabah tidak ditemukan'), 404)
    return penjual, None

# ─── Status / Daftar Penjual ──────────────────────────────

@api_bp.route('/umkm/penjual/status', methods=['GET'])
@jwt_required()
def umkm_penjual_status():
    user = get_current_user()
    if not user.is_nasabah():
        return jsonify(success=True, data={'terdaftar': False, 'message': 'Bukan akun nasabah'})

    penjual = _get_penjual(user)
    if not penjual:
        return jsonify(success=True, data={'terdaftar': False})

    pengajuan = PengajuanPenjual.query.filter_by(nasabah_id=penjual.id).order_by(PengajuanPenjual.tanggal_ajuan.desc()).first()
    if pengajuan:
        return jsonify(success=True, data={
            'terdaftar': pengajuan.status == 'disetujui',
            'status_pengajuan': pengajuan.status,
            'status_label': pengajuan.status_label(),
            'id': pengajuan.id,
            'nama_usaha': pengajuan.nama_usaha,
            'jenis_usaha': pengajuan.jenis_usaha or '',
            'deskripsi': pengajuan.deskripsi or '',
            'catatan_admin': pengajuan.catatan_admin or '',
        })
    return jsonify(success=True, data={'terdaftar': False, 'status_pengajuan': None})


@api_bp.route('/umkm/penjual/daftar', methods=['POST'])
@jwt_required()
def umkm_penjual_daftar():
    user = get_current_user()
    penjual, err = _penjual_or_403(user)
    if err: return err

    data = request.get_json()
    if not data: return jsonify(success=False, message='Data wajib diisi'), 400

    nama_usaha = (data.get('nama_usaha') or '').strip()
    if not nama_usaha:
        return jsonify(success=False, message='Nama usaha wajib diisi'), 400

    existing = PengajuanPenjual.query.filter_by(nasabah_id=penjual.id, status='menunggu').first()
    if existing:
        return jsonify(success=False, message='Anda masih memiliki pengajuan yang menunggu'), 400

    p = PengajuanPenjual(
        nasabah_id=penjual.id,
        nama_usaha=nama_usaha,
        jenis_usaha=data.get('jenis_usaha', ''),
        deskripsi=data.get('deskripsi', ''),
        no_hp_usaha=data.get('no_hp_usaha', ''),
        alamat_usaha=data.get('alamat_usaha', ''),
    )
    db.session.add(p)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal daftar penjual')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message='Pengajuan penjual berhasil dikirim', data={'id': p.id}), 201


# ─── Daftar Penjual Terverifikasi ────────────────────────

@api_bp.route('/umkm/penjual', methods=['GET'])
@jwt_required()
def umkm_penjual_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = PengajuanPenjual.query.filter_by(status='disetujui')
    if q:
        query = query.join(Nasabah).filter(Nasabah.nama.ilike(f'%{q}%'))

    pagination = query.order_by(PengajuanPenjual.tanggal_ajuan.desc()).paginate(page=page, per_page=per_page)
    items = [{
        'id': p.id,
        'nasabah_id': p.nasabah_id,
        'nama_usaha': p.nama_usaha,
        'jenis_usaha': p.jenis_usaha or '',
        'deskripsi': p.deskripsi or '',
        'no_hp_usaha': p.no_hp_usaha or '',
        'alamat_usaha': p.alamat_usaha or '',
        'nama_penjual': p.nasabah.nama,
        'desa': p.nasabah.nama_desa,
    } for p in pagination.items]

    return jsonify(success=True, data={
        'list': items,
        'pagination': {'page': page, 'per_page': per_page, 'total': pagination.total, 'pages': pagination.pages},
    })


# ─── Produk UMKM ──────────────────────────────────────────

@api_bp.route('/umkm/produk', methods=['GET'])
@jwt_required()
def umkm_produk_list():
    q = request.args.get('q', '').strip()
    kategori = request.args.get('kategori', '').strip()
    penjual_id = request.args.get('penjual_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)

    query = ProdukUMKM.query.filter_by(aktif=True)
    if q:
        query = query.filter(ProdukUMKM.nama_produk.ilike(f'%{q}%'))
    if kategori:
        query = query.filter_by(kategori=kategori)
    if penjual_id:
        query = query.filter_by(penjual_id=penjual_id)

    pagination = query.order_by(ProdukUMKM.tanggal_dibuat.desc()).paginate(page=page, per_page=per_page)
    items = [{
        'id': p.id,
        'penjual_id': p.penjual_id,
        'nama_produk': p.nama_produk,
        'deskripsi': p.deskripsi or '',
        'kategori': p.kategori or '',
        'kategori_label': p.kategori_label(),
        'harga': p.harga,
        'stok': p.stok,
        'satuan': p.satuan or 'pcs',
        'gambar': p.gambar or '',
        'nama_penjual': p.penjual.nama,
        'desa': p.penjual.nama_desa,
    } for p in pagination.items]

    return jsonify(success=True, data={
        'list': items,
        'pagination': {'page': page, 'per_page': per_page, 'total': pagination.total, 'pages': pagination.pages},
    })


@api_bp.route('/umkm/produk/<int:produk_id>', methods=['GET'])
@jwt_required()
def umkm_produk_detail(produk_id):
    p = db.session.get(ProdukUMKM, produk_id)
    if not p or not p.aktif:
        return jsonify(success=False, message='Produk tidak ditemukan'), 404

    return jsonify(success=True, data={
        'id': p.id,
        'penjual_id': p.penjual_id,
        'nama_produk': p.nama_produk,
        'deskripsi': p.deskripsi or '',
        'kategori': p.kategori or '',
        'kategori_label': p.kategori_label(),
        'harga': p.harga,
        'stok': p.stok,
        'satuan': p.satuan or 'pcs',
        'gambar': p.gambar or '',
        'aktif': p.aktif,
        'tanggal_dibuat': p.tanggal_dibuat.isoformat() if p.tanggal_dibuat else '',
        'nama_penjual': p.penjual.nama,
        'no_hp_penjual': p.penjual.no_hp or '',
        'desa': p.penjual.nama_desa,
        'alamat_penjual': p.penjual.alamat or '',
    })


@api_bp.route('/umkm/produk', methods=['POST'])
@jwt_required()
def umkm_produk_create():
    user = get_current_user()
    penjual, err = _penjual_or_403(user)
    if err: return err

    pengajuan = PengajuanPenjual.query.filter_by(nasabah_id=penjual.id, status='disetujui').first()
    if not pengajuan:
        return jsonify(success=False, message='Anda belum terdaftar sebagai penjual'), 403

    data = request.get_json()
    if not data: return jsonify(success=False, message='Data wajib diisi'), 400

    nama = (data.get('nama_produk') or '').strip()
    try:
        harga = int(data['harga']) if data.get('harga') is not None else None
    except (ValueError, TypeError):
        harga = None
    if not nama or not harga or harga <= 0:
        return jsonify(success=False, message='Nama produk dan harga wajib diisi'), 400

    p = ProdukUMKM(
        penjual_id=penjual.id,
        nama_produk=nama,
        deskripsi=data.get('deskripsi', ''),
        kategori=data.get('kategori', 'lainnya'),
        harga=harga,
        stok=data.get('stok', 0),
        satuan=data.get('satuan', 'pcs'),
    )
    db.session.add(p)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal buat produk')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message='Produk berhasil ditambahkan', data={'id': p.id}), 201


@api_bp.route('/umkm/produk/<int:produk_id>', methods=['PUT'])
@jwt_required()
def umkm_produk_update(produk_id):
    user = get_current_user()
    penjual, err = _penjual_or_403(user)
    if err: return err

    p = db.session.get(ProdukUMKM, produk_id)
    if not p or p.penjual_id != penjual.id:
        return jsonify(success=False, message='Produk tidak ditemukan'), 404

    data = request.get_json()
    if not data: return jsonify(success=False, message='Data wajib diisi'), 400

    if 'nama_produk' in data and data['nama_produk']:
        p.nama_produk = data['nama_produk'].strip()
    if 'deskripsi' in data: p.deskripsi = data['deskripsi']
    if 'kategori' in data: p.kategori = data['kategori']
    if 'harga' in data and data['harga']: p.harga = int(data['harga'])
    if 'stok' in data: p.stok = int(data.get('stok', 0))
    if 'satuan' in data: p.satuan = data['satuan']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal update produk')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message='Produk diperbarui')


@api_bp.route('/umkm/produk/<int:produk_id>', methods=['DELETE'])
@jwt_required()
def umkm_produk_delete(produk_id):
    user = get_current_user()
    penjual, err = _penjual_or_403(user)
    if err: return err

    p = db.session.get(ProdukUMKM, produk_id)
    if not p or p.penjual_id != penjual.id:
        return jsonify(success=False, message='Produk tidak ditemukan'), 404

    p.aktif = False
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal hapus produk')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message='Produk dinonaktifkan')


@api_bp.route('/umkm/produk/<int:produk_id>/gambar', methods=['POST'])
@jwt_required()
def umkm_produk_upload_gambar(produk_id):
    user = get_current_user()
    penjual, err = _penjual_or_403(user)
    if err: return err

    p = db.session.get(ProdukUMKM, produk_id)
    if not p or p.penjual_id != penjual.id:
        return jsonify(success=False, message='Produk tidak ditemukan'), 404

    if 'gambar' not in request.files:
        return jsonify(success=False, message='File gambar tidak ditemukan'), 400

    f = request.files['gambar']
    path = save_file(f, 'umkm', f'produk_{produk_id}')
    if not path:
        return jsonify(success=False, message='Format file tidak didukung (png/jpg/jpeg/gif/pdf/webp)'), 400

    p.gambar = path
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal simpan gambar')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message='Gambar berhasil diupload', data={'gambar': p.gambar})


# ─── Pesanan UMKM ─────────────────────────────────────────

@api_bp.route('/umkm/pesanan', methods=['POST'])
@jwt_required()
def umkm_pesanan_create():
    user = get_current_user()
    if not user.is_nasabah():
        return jsonify(success=False, message='Hanya nasabah yang bisa memesan'), 403

    pembeli = db.session.get(Nasabah, user.nasabah_id_fk)
    if not pembeli:
        return jsonify(success=False, message='Data nasabah tidak ditemukan'), 404

    data = request.get_json()
    if not data: return jsonify(success=False, message='Data wajib diisi'), 400

    try:
        penjual_id = int(data['penjual_id']) if data.get('penjual_id') is not None else None
    except (ValueError, TypeError):
        penjual_id = None
    items = data.get('items', [])
    alamat = (data.get('alamat_pengiriman') or '').strip()
    catatan = data.get('catatan_pembeli', '')

    if not penjual_id or not items:
        return jsonify(success=False, message='Penjual dan item pesanan wajib diisi'), 400

    penjual = db.session.get(Nasabah, penjual_id)
    if not penjual:
        return jsonify(success=False, message='Penjual tidak ditemukan'), 404

    detail_list = []
    total = 0
    for it in items:
        try:
            produk_id = int(it['produk_id']) if it.get('produk_id') is not None else None
        except (ValueError, TypeError):
            produk_id = None
        try:
            jumlah = int(it['jumlah']) if it.get('jumlah') is not None else None
        except (ValueError, TypeError):
            jumlah = None
        if not produk_id or not jumlah or jumlah <= 0:
            continue
        produk = db.session.get(ProdukUMKM, produk_id)
        if not produk or not produk.aktif or produk.penjual_id != penjual_id:
            return jsonify(success=False, message=f'Produk ID {produk_id} tidak valid'), 400
        if produk.stok < jumlah:
            return jsonify(success=False, message=f'Stok {produk.nama_produk} tidak mencukupi (sisa {produk.stok})'), 400
        subtotal = produk.harga * jumlah
        detail_list.append({
            'produk': produk,
            'jumlah': jumlah,
            'harga_satuan': produk.harga,
            'subtotal': subtotal,
        })
        total += subtotal

    if not detail_list:
        return jsonify(success=False, message='Tidak ada item valid'), 400

    from ...models import get_next_no_pesanan_umkm
    nomor = get_next_no_pesanan_umkm()

    pesanan = PesananUMKM(
        nomor_pesanan=nomor,
        pembeli_id=pembeli.id,
        penjual_id=penjual_id,
        total_harga=total,
        alamat_pengiriman=alamat,
        catatan_pembeli=catatan,
    )
    db.session.add(pesanan)
    db.session.flush()

    for d in detail_list:
        det = DetailPesananUMKM(
            pesanan_id=pesanan.id,
            produk_id=d['produk'].id,
            jumlah=d['jumlah'],
            harga_satuan=d['harga_satuan'],
            subtotal=d['subtotal'],
        )
        db.session.add(det)
        d['produk'].stok -= d['jumlah']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal buat pesanan')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message='Pesanan berhasil dibuat', data={'nomor_pesanan': nomor, 'id': pesanan.id}), 201


@api_bp.route('/umkm/pesanan', methods=['GET'])
@jwt_required()
def umkm_pesanan_list():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', '').strip()
    role_filter = request.args.get('role', '').strip()

    query = PesananUMKM.query

    if user.is_nasabah() and user.nasabah_id_fk:
        nasabah_id = user.nasabah_id_fk
        penjual = PengajuanPenjual.query.filter_by(nasabah_id=nasabah_id, status='disetujui').first()
        if role_filter == 'penjual' and penjual:
            query = query.filter_by(penjual_id=nasabah_id)
        elif role_filter == 'pembeli':
            query = query.filter_by(pembeli_id=nasabah_id)
        else:
            query = query.filter(
                db.or_(PesananUMKM.pembeli_id == nasabah_id, PesananUMKM.penjual_id == nasabah_id)
            )

    if status_filter:
        query = query.filter_by(status=status_filter)

    pagination = query.order_by(PesananUMKM.tanggal_pesanan.desc()).paginate(page=page, per_page=per_page)

    items = []
    for pes in pagination.items:
        detail = [{
            'id': d.id,
            'produk_id': d.produk_id,
            'nama_produk': d.produk.nama_produk,
            'jumlah': d.jumlah,
            'harga_satuan': d.harga_satuan,
            'subtotal': d.subtotal,
            'gambar': d.produk.gambar or '',
        } for d in pes.detail_list]

        items.append({
            'id': pes.id,
            'nomor_pesanan': pes.nomor_pesanan,
            'pembeli_id': pes.pembeli_id,
            'pembeli_nama': pes.pembeli.nama,
            'penjual_id': pes.penjual_id,
            'penjual_nama': pes.penjual.nama,
            'tanggal_pesanan': pes.tanggal_pesanan.isoformat() if pes.tanggal_pesanan else '',
            'status': pes.status,
            'status_label': pes.status_label(),
            'total_harga': pes.total_harga,
            'status_pembayaran': pes.status_pembayaran,
            'status_pembayaran_label': pes.status_pembayaran_label(),
            'metode_pembayaran': pes.metode_pembayaran or '',
            'bukti_pembayaran': pes.bukti_pembayaran or '',
            'detail': detail,
            'alamat_pengiriman': pes.alamat_pengiriman or '',
            'catatan_pembeli': pes.catatan_pembeli or '',
            'catatan_penjual': pes.catatan_penjual or '',
        })

    return jsonify(success=True, data={
        'list': items,
        'pagination': {'page': page, 'per_page': per_page, 'total': pagination.total, 'pages': pagination.pages},
    })


@api_bp.route('/umkm/pesanan/<int:pesanan_id>', methods=['GET'])
@jwt_required()
def umkm_pesanan_detail(pesanan_id):
    user = get_current_user()
    pes = db.session.get(PesananUMKM, pesanan_id)
    if not pes:
        return jsonify(success=False, message='Pesanan tidak ditemukan'), 404

    if not user.is_admin():
        if not user.is_nasabah() or (user.nasabah_id_fk not in (pes.pembeli_id, pes.penjual_id)):
            return jsonify(success=False, message='Forbidden'), 403

    detail = [{
        'id': d.id,
        'produk_id': d.produk_id,
        'nama_produk': d.produk.nama_produk,
        'jumlah': d.jumlah,
        'harga_satuan': d.harga_satuan,
        'subtotal': d.subtotal,
        'gambar': d.produk.gambar or '',
    } for d in pes.detail_list]

    return jsonify(success=True, data={
        'id': pes.id,
        'nomor_pesanan': pes.nomor_pesanan,
        'pembeli_id': pes.pembeli_id,
        'pembeli_nama': pes.pembeli.nama,
        'pembeli_hp': pes.pembeli.no_hp or '',
        'penjual_id': pes.penjual_id,
        'penjual_nama': pes.penjual.nama,
        'penjual_hp': pes.penjual.no_hp or '',
        'tanggal_pesanan': pes.tanggal_pesanan.isoformat() if pes.tanggal_pesanan else '',
        'tanggal_diproses': pes.tanggal_diproses.isoformat() if pes.tanggal_diproses else '',
        'tanggal_selesai': pes.tanggal_selesai.isoformat() if pes.tanggal_selesai else '',
        'status': pes.status,
        'status_label': pes.status_label(),
        'total_harga': pes.total_harga,
        'status_pembayaran': pes.status_pembayaran,
        'status_pembayaran_label': pes.status_pembayaran_label(),
        'metode_pembayaran': pes.metode_pembayaran or '',
        'metode_pembayaran_label': pes.metode_pembayaran_label(),
        'bukti_pembayaran': pes.bukti_pembayaran or '',
        'kurir': pes.kurir or '',
        'nomor_resi': pes.nomor_resi or '',
        'alamat_pengiriman': pes.alamat_pengiriman or '',
        'catatan_pembeli': pes.catatan_pembeli or '',
        'catatan_penjual': pes.catatan_penjual or '',
        'detail': detail,
    })


@api_bp.route('/umkm/pesanan/<int:pesanan_id>/status', methods=['PUT'])
@jwt_required()
def umkm_pesanan_update_status(pesanan_id):
    user = get_current_user()
    pes = db.session.get(PesananUMKM, pesanan_id)
    if not pes:
        return jsonify(success=False, message='Pesanan tidak ditemukan'), 404

    data = request.get_json()
    if not data: return jsonify(success=False, message='Data wajib diisi'), 400

    new_status = data.get('status', '').strip()
    catatan = data.get('catatan', '')

    valid_transitions = {
        'menunggu': ['diproses', 'dibatalkan'],
        'diproses': ['dikirim', 'dibatalkan'],
        'dikirim': ['selesai'],
    }

    if new_status not in valid_transitions.get(pes.status, []):
        return jsonify(success=False, message=f'Tidak bisa ubah status dari "{pes.status}" ke "{new_status}"'), 400

    is_penjual = user.is_nasabah() and user.nasabah_id_fk == pes.penjual_id
    is_pembeli = user.is_nasabah() and user.nasabah_id_fk == pes.pembeli_id
    is_admin = user.is_admin()

    if new_status == 'diproses' and (is_penjual or is_admin):
        pes.status = 'diproses'
        pes.tanggal_diproses = datetime.now(timezone.utc)
    elif new_status == 'dikirim' and (is_penjual or is_admin):
        pes.status = 'dikirim'
        pes.tanggal_kirim = datetime.now(timezone.utc)
        if data.get('kurir'): pes.kurir = data['kurir']
        if data.get('nomor_resi'): pes.nomor_resi = data['nomor_resi']
    elif new_status == 'selesai' and (is_pembeli or is_admin):
        pes.status = 'selesai'
        pes.tanggal_selesai = datetime.now(timezone.utc)
    elif new_status == 'dibatalkan' and (is_pembeli or is_admin):
        pes.status = 'dibatalkan'
        for d in pes.detail_list:
            d.produk.stok += d.jumlah
    else:
        return jsonify(success=False, message='Anda tidak memiliki izin untuk aksi ini'), 403

    if catatan:
        if is_penjual or is_admin:
            pes.catatan_penjual = (pes.catatan_penjual or '') + ('\n' if pes.catatan_penjual else '') + catatan
        else:
            pes.catatan_pembeli = (pes.catatan_pembeli or '') + ('\n' if pes.catatan_pembeli else '') + catatan

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal update status pesanan')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message=f'Pesanan {new_status}', data={'status': pes.status})


@api_bp.route('/umkm/pesanan/<int:pesanan_id>/bukti', methods=['POST'])
@jwt_required()
def umkm_pesanan_upload_bukti(pesanan_id):
    user = get_current_user()
    pes = db.session.get(PesananUMKM, pesanan_id)
    if not pes:
        return jsonify(success=False, message='Pesanan tidak ditemukan'), 404

    if not user.is_nasabah() or user.nasabah_id_fk != pes.pembeli_id:
        return jsonify(success=False, message='Hanya pembeli yang bisa upload bukti'), 403

    if 'bukti' not in request.files:
        return jsonify(success=False, message='File bukti tidak ditemukan'), 400

    f = request.files['bukti']
    path = save_file(f, 'umkm', f'bayar_{pesanan_id}')
    if not path:
        return jsonify(success=False, message='Format file tidak didukung (png/jpg/jpeg/gif/pdf/webp)'), 400

    pes.bukti_pembayaran = path
    metode = request.form.get('metode', 'transfer_bank')
    if metode not in PesananUMKM.METODE_PEMBAYARAN_LABELS:
        metode = 'transfer_bank'
    pes.metode_pembayaran = metode
    pes.status_pembayaran = 'menunggu_konfirmasi'

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('Gagal upload bukti')
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message='Bukti pembayaran diupload', data={'bukti': pes.bukti_pembayaran})


# ─── Rekening Pembayaran ─────────────────────────────────

@api_bp.route('/umkm/rekening', methods=['GET'])
@jwt_required()
def umkm_rekening_list():
    rek = RekeningPembayaran.query.filter_by(aktif=True).order_by(RekeningPembayaran.urutan).all()
    items = [{
        'id': r.id,
        'nama_bank': r.nama_bank,
        'nama_rekening': r.nama_rekening,
        'nomor_rekening': r.nomor_rekening,
    } for r in rek]
    return jsonify(success=True, data={'list': items})


# ─── Admin: Daftar Semua Pengajuan Penjual ──────────────

@api_bp.route('/umkm/penjual/all', methods=['GET'])
@jwt_required()
def umkm_penjual_all():
    user = get_current_user()
    if not (user.is_admin() or user.is_manajer() or user.is_staf()):
        return jsonify(success=False, message='Forbidden'), 403

    status_filter = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    q = PengajuanPenjual.query
    if status_filter:
        q = q.filter_by(status=status_filter)

    pagination = q.order_by(PengajuanPenjual.tanggal_ajuan.desc()).paginate(page=page, per_page=per_page)
    items = [{
        'id': p.id,
        'nasabah_id': p.nasabah_id,
        'nama_usaha': p.nama_usaha,
        'jenis_usaha': p.jenis_usaha or '',
        'deskripsi': p.deskripsi or '',
        'no_hp_usaha': p.no_hp_usaha or '',
        'alamat_usaha': p.alamat_usaha or '',
        'status': p.status,
        'status_label': p.status_label(),
        'tanggal_ajuan': p.tanggal_ajuan.isoformat() if p.tanggal_ajuan else '',
        'nama_penjual': p.nasabah.nama if p.nasabah else '',
        'desa': p.nasabah.nama_desa if p.nasabah else '',
        'catatan_admin': p.catatan_admin or '',
    } for p in pagination.items]

    return jsonify(success=True, data={
        'list': items,
        'pagination': {'page': page, 'per_page': per_page, 'total': pagination.total, 'pages': pagination.pages},
    })


# ─── Admin: Proses Pengajuan Penjual ─────────────────────

@api_bp.route('/umkm/penjual/<int:id>/proses', methods=['POST'])
@jwt_required()
def umkm_penjual_proses(id):
    user = get_current_user()
    if not (user.is_admin() or user.is_manajer() or user.is_staf()):
        return jsonify(success=False, message='Forbidden'), 403

    pengajuan = db.session.get(PengajuanPenjual, id)
    if not pengajuan:
        return jsonify(success=False, message='Pengajuan tidak ditemukan'), 404

    if pengajuan.status != 'menunggu':
        return jsonify(success=False, message=f'Status sudah "{pengajuan.status}"'), 400

    data = request.get_json() or {}
    action = (data.get('action') or '').strip()
    if action not in ('setujui', 'tolak'):
        return jsonify(success=False, message='Aksi harus "setujui" atau "tolak"'), 400

    pengajuan.status = 'disetujui' if action == 'setujui' else 'ditolak'
    pengajuan.admin_id = user.id
    pengajuan.tanggal_respon = datetime.now(timezone.utc)
    pengajuan.catatan_admin = data.get('catatan_admin', '')

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message=f'Pengajuan {"disetujui" if action == "setujui" else "ditolak"}')


# ─── Admin: Konfirmasi Pembayaran Pesanan UMKM ──────────

@api_bp.route('/umkm/pesanan/<int:pesanan_id>/konfirmasi-bayar', methods=['POST'])
@jwt_required()
def umkm_pesanan_konfirmasi_bayar(pesanan_id):
    user = get_current_user()
    if not (user.is_admin() or user.is_manajer() or user.is_staf()):
        return jsonify(success=False, message='Forbidden'), 403

    pes = db.session.get(PesananUMKM, pesanan_id)
    if not pes:
        return jsonify(success=False, message='Pesanan tidak ditemukan'), 404

    if pes.status_pembayaran != 'menunggu_konfirmasi':
        return jsonify(success=False, message=f'Status pembayaran "{pes.status_pembayaran}" tidak perlu konfirmasi'), 400

    data = request.get_json() or {}
    action = (data.get('action') or '').strip()
    if action not in ('terima', 'tolak'):
        return jsonify(success=False, message='Aksi harus "terima" atau "tolak"'), 400

    if action == 'terima':
        pes.status_pembayaran = 'lunas'
        pes.tanggal_lunas = datetime.now(timezone.utc)
    else:
        pes.status_pembayaran = 'gagal'
        pes.catatan_penjual = (pes.catatan_penjual or '') + f'\nPembayaran ditolak: {data.get("alasan", "")}'

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f'Gagal: {str(e)}'), 500

    return jsonify(success=True, message=f'Pembayaran {"diterima" if action == "terima" else "ditolak"}')
