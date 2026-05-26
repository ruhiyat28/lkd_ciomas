from flask import request, jsonify, url_for, current_app
from flask_jwt_extended import jwt_required
from ...models import db, Nasabah
from ...utils.helpers import save_file
from . import api_bp, get_current_user
import logging

logger = logging.getLogger(__name__)

FIELD_MAP = {
    'foto': ('foto', True),
    'ktp': ('ktp', False),
    'kk': ('kk', False),
    'surat_usaha': ('sku', False),
    'bukti_penghasilan': ('penghasilan', False),
    'jaminan': ('jaminan', False),
    'jaminan_docs': ('jaminan_docs', False),
    'tanda_tangan': ('ttd_nasabah', False),
}


@api_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    user = get_current_user()

    if 'file' not in request.files:
        return jsonify(success=False, message='Tidak ada file yang diupload'), 400

    file = request.files['file']
    if not file.filename:
        return jsonify(success=False, message='File tidak valid'), 400

    field = request.form.get('field', 'foto')
    nasabah_id = request.form.get('nasabah_id', type=int)

    if field not in FIELD_MAP:
        return jsonify(success=False, message=f'Field tidak dikenal. Pilihan: {", ".join(FIELD_MAP.keys())}'), 400

    subfolder, force_portrait = FIELD_MAP[field]

    prefix = ''
    if nasabah_id:
        n = db.session.get(Nasabah, nasabah_id)
        if n:
            if user.is_kader() and n.kode_desa != user.kode_desa:
                return jsonify(success=False, message='Forbidden'), 403
            prefix = n.nasabah_id.replace('-', '')
        else:
            return jsonify(success=False, message='Nasabah tidak ditemukan'), 404
    else:
        import uuid
        prefix = uuid.uuid4().hex[:12]

    saved_path = save_file(file, subfolder, prefix, force_portrait=force_portrait)
    if not saved_path:
        return jsonify(success=False, message='Gagal menyimpan file. Format tidak didukung (png/jpg/jpeg/gif/pdf/webp)'), 400

    if nasabah_id and field != 'tanda_tangan':
        n = db.session.get(Nasabah, nasabah_id)
        if n:
            setattr(n, field, saved_path)
            db.session.commit()

    return jsonify(success=True, message='File berhasil diupload', data={
        'file_path': saved_path,
        'url': url_for('static', filename=saved_path, _external=True),
        'field': field,
    }), 201


@api_bp.route('/upload/ganti-foto', methods=['POST'])
@jwt_required()
def ganti_foto_nasabah():
    user = get_current_user()
    if not user.can_write_nasabah():
        return jsonify(success=False, message='Forbidden'), 403

    if 'file' not in request.files:
        return jsonify(success=False, message='Tidak ada file'), 400

    file = request.files['file']
    if not file.filename:
        return jsonify(success=False, message='File tidak valid'), 400

    data = request.form
    nasabah_id = data.get('nasabah_id', type=int)
    field = data.get('field', 'foto')

    if not nasabah_id:
        return jsonify(success=False, message='nasabah_id diperlukan'), 400
    if field not in FIELD_MAP:
        return jsonify(success=False, message=f'Field tidak dikenal'), 400

    n = db.session.get(Nasabah, nasabah_id)
    if not n:
        return jsonify(success=False, message='Nasabah tidak ditemukan'), 404
    if user.is_kader() and n.kode_desa != user.kode_desa:
        return jsonify(success=False, message='Forbidden'), 403

    subfolder, force_portrait = FIELD_MAP[field]
    prefix = n.nasabah_id.replace('-', '')
    saved_path = save_file(file, subfolder, prefix, force_portrait=force_portrait)
    if not saved_path:
        return jsonify(success=False, message='Gagal menyimpan file'), 400

    setattr(n, field, saved_path)
    db.session.commit()

    return jsonify(success=True, message=f'{field} berhasil diperbarui', data={
        'file_path': saved_path,
        'url': url_for('static', filename=saved_path, _external=True),
    })
