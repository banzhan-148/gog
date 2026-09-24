from flask import Blueprint, jsonify, request

from config import Config
from extensions import limiter
from db import q
from utils import login_required, clean_text

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/clients')
@login_required
@limiter.limit(Config.API_LIMIT)
def clients():
    term = clean_text(request.args.get('q', ''), 100)
    if len(term) < 2:
        return jsonify([])
    like = f'%{term}%'
    rows = q("SELECT id, full_name, phone FROM clients "
             "WHERE is_deleted=0 AND (full_name LIKE ? OR phone LIKE ?) LIMIT 20",
             (like, like))
    return jsonify([{'id': r['id'], 'name': r['full_name'], 'phone': r['phone']}
                    for r in rows])