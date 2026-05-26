import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def _generate_secret_key():
    """Generate a random secret key and warn if not set via env."""
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    # Fallback: generate random key (will change on restart if not persisted)
    return secrets.token_hex(32)

class Config:
    SECRET_KEY = _generate_secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or ('sqlite:///' + os.path.join(BASE_DIR, 'instance', 'lkd_ciomas.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Database connection pool management to prevent intermittent 500 errors
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
    }

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ERROR_MESSAGE_KEY = 'message'
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # Password policy
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_REQUIRE_UPPER = False
    PASSWORD_REQUIRE_DIGIT = False
    PASSWORD_REQUIRE_SPECIAL = False

    TENOR_OPTIONS = [3, 6, 10, 12, 18, 24, 36]

    LEMBAGA_NAMA   = "BUM DESA BERSAMA UPK CIOMAS LKD"
    LEMBAGA_ALAMAT = "Jl. Raya Ciomas Km.1 Serang 42164"
    LEMBAGA_TELP   = "(0254)7823984"
    LEMBAGA_WA     = "081324771060"

    DESA_LIST = [
        ("UT","UJUNG TEBU"), ("CS","CISITU"), ("SK","SIKETUG"),
        ("LB","LEBAK"),      ("CM","CITAMAN"),("PK","PONDOK KAHURU"),
        ("SB","SUKABARES"),  ("SD","SUKADANA"),("SR","SUKARENA"),
        ("CP","CEMPLANG"),   ("PJ","PANYAUNGAN JAYA"),
    ]

    KOLEK_CADANGAN = {1:0.01, 2:0.10, 3:0.25, 4:0.50, 5:1.00}

    # Format SPK: SPK-YYYY-XXXXX
    @staticmethod
    def format_spk(tahun, nomor):
        return f"SPK-{tahun}-{nomor:05d}"
