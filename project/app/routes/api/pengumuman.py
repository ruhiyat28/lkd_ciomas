from flask import jsonify
from flask_jwt_extended import jwt_required
from ...models import db, Pengumuman
from . import api_bp, get_current_user
from datetime import datetime, timezone

@api_bp.route('/pengumuman', methods=['GET'])
@jwt_required()
def list_pengumuman():
    user = get_current_user()
    now = datetime.now(timezone.utc)

    q = Pengumuman.query.filter(
        Pengumuman.aktif == True,
        db.or_(Pengumuman.expires_at == None, Pengumuman.expires_at > now)
    )

    if user.is_nasabah() and user.nasabah:
        q = q.filter(
            db.or_(
                Pengumuman.target == 'semua',
                Pengumuman.nasabah_id_fk == user.nasabah.id
            )
        )
    else:
        q = q.filter_by(target='semua')

    q = q.order_by(Pengumuman.created_at.desc()).limit(20)

    result = [{
        'id': p.id,
        'judul': p.judul,
        'isi': p.isi,
        'tipe': p.tipe,
        'created_at': str(p.created_at) if p.created_at else '',
    } for p in q.all()]

    return jsonify(success=True, data=result)
