from flask import jsonify
from config import Config
from . import api_bp

@api_bp.route('/config', methods=['GET'])
def get_config():
    return jsonify(success=True, data={
        'desa_list': [{'kode': k, 'nama': n} for k, n in Config.DESA_LIST],
        'lembaga': {
            'nama': Config.LEMBAGA_NAMA,
            'alamat': Config.LEMBAGA_ALAMAT,
            'telp': Config.LEMBAGA_TELP,
            'wa': Config.LEMBAGA_WA,
        },
        'tenor_options': Config.TENOR_OPTIONS,
    })
