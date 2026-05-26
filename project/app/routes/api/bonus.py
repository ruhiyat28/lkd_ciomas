from flask import jsonify
from flask_jwt_extended import jwt_required
from ...models import db, BonusPetugas, BonusPembina
from . import api_bp, get_current_user

@api_bp.route('/bonus/saya', methods=['GET'])
@jwt_required()
def bonus_saya():
    user = get_current_user()
    if not user:
        return jsonify(success=False, message='Unauthorized'), 401

    bonus_list = BonusPetugas.query.filter_by(petugas_id=user.id)\
        .order_by(BonusPetugas.tanggal_hitung.desc()).all()

    bonus_pembina = BonusPembina.query.filter(
        db.or_(BonusPembina.kader_id == user.id, BonusPembina.pembina_id == user.id)
    ).order_by(BonusPembina.tanggal_hitung.desc()).all()

    items = []
    for b in bonus_list:
        items.append({
            'id': b.id,
            'pembayaran_id': b.pembayaran_id,
            'tahun_tunggakan': b.tahun_tunggakan,
            'jumlah_bayar': b.jumlah_bayar,
            'persen_bonus': b.persen_bonus,
            'jumlah_bonus': b.jumlah_bonus,
            'status': b.status,
            'tanggal_hitung': b.tanggal_hitung.isoformat() if b.tanggal_hitung else None,
            'tanggal_klaim': b.tanggal_klaim.isoformat() if b.tanggal_klaim else None,
            'tipe': 'bonus_petugas',
        })
    for b in bonus_pembina:
        items.append({
            'id': b.id,
            'pembayaran_id': b.pembayaran_id,
            'tahun_tunggakan': None,
            'jumlah_bayar': None,
            'persen_bonus': b.persen_potongan,
            'jumlah_bonus': b.jumlah_bonus_pembina,
            'status': b.status,
            'tanggal_hitung': b.tanggal_hitung.isoformat() if b.tanggal_hitung else None,
            'tanggal_klaim': b.tanggal_klaim.isoformat() if b.tanggal_klaim else None,
            'tipe': 'bonus_pembina',
        })

    items.sort(key=lambda x: x['tanggal_hitung'] or '', reverse=True)

    total_bonus = sum(item['jumlah_bonus'] for item in items if item['status'] in ('belum_diklaim', 'menunggu_klaim'))
    total_diklaim = sum(item['jumlah_bonus'] for item in items if item['status'] == 'diklaim')
    total_semua = sum(item['jumlah_bonus'] for item in items)

    return jsonify(success=True, data={
        'items': items,
        'total_bonus': total_bonus,
        'total_diklaim': total_diklaim,
        'total_semua': total_semua,
    })
