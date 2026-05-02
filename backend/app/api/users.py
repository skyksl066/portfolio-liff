from flask import Blueprint, request, jsonify, g

from ..core.auth import require_line_auth
from ..core.db import get_conn

bp = Blueprint('users', __name__)


@bp.get('/me')
@require_line_auth
def me():
    return jsonify({'userId': g.user_id, 'displayName': g.display_name})


@bp.get('/strategy')
@require_line_auth
def get_strategy():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT strategy FROM whitelist_users WHERE line_user_id=%s',
                (g.user_id,),
            )
            row = cur.fetchone()
    return jsonify({'strategy': (row.get('strategy') if row else None) or ''})


@bp.put('/strategy')
@require_line_auth
def update_strategy():
    data = request.get_json(silent=True) or {}
    raw = data.get('strategy')
    if raw is None:
        raw = ''
    if not isinstance(raw, str):
        return jsonify({'error': 'BAD_REQUEST', 'message': 'strategy 必須為字串'}), 400
    strategy = raw.strip()
    if len(strategy) > 4000:
        return jsonify({'error': 'BAD_REQUEST', 'message': 'strategy 長度不可超過 4000'}), 400

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE whitelist_users SET strategy=%s WHERE line_user_id=%s',
                (strategy or None, g.user_id),
            )
    return jsonify({'strategy': strategy})
