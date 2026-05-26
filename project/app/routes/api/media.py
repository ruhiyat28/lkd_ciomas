from flask import send_from_directory, jsonify, current_app
from flask_jwt_extended import jwt_required
from . import api_bp
import os

@api_bp.route('/media/<path:filename>', methods=['GET'])
@jwt_required()
def serve_media(filename):
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    file_path = os.path.join(upload_dir, filename)
    if not os.path.isfile(file_path):
        return jsonify(success=False, message='File tidak ditemukan'), 404
    dirname = os.path.dirname(filename)
    basename = os.path.basename(filename)
    full_dir = os.path.join(upload_dir, dirname)
    return send_from_directory(full_dir, basename)
