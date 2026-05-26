from flask import Blueprint, jsonify
from flask_jwt_extended import JWTManager
from ...models import db, User

api_bp = Blueprint('api', __name__, url_prefix='/api')
jwt = JWTManager()

@jwt.user_identity_loader
def user_identity_lookup(user_id_str):
    return user_id_str

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data['sub']
    return db.session.get(User, int(identity))

@api_bp.errorhandler(400)
def bad_request(e):
    return jsonify(success=False, message=str(e)), 400

@api_bp.errorhandler(401)
def unauthorized(e):
    return jsonify(success=False, message='Unauthorized'), 401

@api_bp.errorhandler(403)
def forbidden(e):
    return jsonify(success=False, message='Forbidden'), 403

@api_bp.errorhandler(404)
def not_found(e):
    return jsonify(success=False, message='Not found'), 404

@api_bp.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify(success=False, message='Internal server error'), 500

def get_current_user():
    from flask_jwt_extended import get_jwt_identity
    identity = get_jwt_identity()
    if not identity:
        return None
    return db.session.get(User, int(identity))

from . import auth
from . import nasabah
from . import pinjaman
from . import pembayaran
from . import tabungan
from . import dashboard
from . import upload
from . import fcm
from . import umkm
from . import bonus
from . import pengumuman
from . import media
from . import config
