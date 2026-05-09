import re

from flask import Blueprint, request, jsonify, g

from ..core.auth import require_line_auth
from ..core.db import get_conn

bp = Blueprint('holdings', __name__)

VALID_MARKETS = {'TW', 'US'}
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


def _valid_uuid(val):
    return bool(_UUID_RE.match(str(val or '')))


@bp.get('/holdings')
@require_line_auth
def list_holdings():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT LOWER(INSERT(INSERT(INSERT(INSERT(HEX(id),9,0,'-'),14,0,'-'),19,0,'-'),24,0,'-')) AS id,
                          market, symbol, name, category, shares, avg_price,
                          purchase_date, note
                   FROM stock_holdings
                   WHERE line_user_id=%s
                   ORDER BY category, symbol''',
                (g.user_id,),
            )
            rows = cur.fetchall()
    return jsonify([_serialize_row(r) for r in rows])


@bp.post('/holdings')
@require_line_auth
def create_holding():
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return jsonify({'error': 'BAD_REQUEST', 'message': err}), 400

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SET @new_id = UNHEX(REPLACE(UUID(), \'-\', \'\'))')
            cur.execute(
                '''INSERT INTO stock_holdings
                   (id, line_user_id, market, symbol, name, category, shares, avg_price, purchase_date, note)
                   VALUES (@new_id,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (g.user_id, *_normalize(data)),
            )
            cur.execute(
                "SELECT LOWER(INSERT(INSERT(INSERT(INSERT(HEX(@new_id),9,0,'-'),14,0,'-'),19,0,'-'),24,0,'-')) AS id"
            )
            new_id = cur.fetchone()['id']
    return jsonify({'id': new_id}), 201


@bp.put('/holdings/<string:hid>')
@require_line_auth
def update_holding(hid):
    if not _valid_uuid(hid):
        return jsonify({'error': 'NOT_FOUND'}), 404
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return jsonify({'error': 'BAD_REQUEST', 'message': err}), 400

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE stock_holdings
                   SET market=%s, symbol=%s, name=%s, category=%s,
                       shares=%s, avg_price=%s, purchase_date=%s, note=%s
                   WHERE id=UNHEX(REPLACE(%s, '-', '')) AND line_user_id=%s''',
                (*_normalize(data), hid, g.user_id),
            )
            if cur.rowcount == 0:
                return jsonify({'error': 'NOT_FOUND'}), 404
    return jsonify({'id': hid})


@bp.delete('/holdings/<string:hid>')
@require_line_auth
def delete_holding(hid):
    if not _valid_uuid(hid):
        return jsonify({'error': 'NOT_FOUND'}), 404
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'DELETE FROM stock_holdings WHERE id=UNHEX(REPLACE(%s, \'-\', \'\')) AND line_user_id=%s',
                (hid, g.user_id),
            )
            if cur.rowcount == 0:
                return jsonify({'error': 'NOT_FOUND'}), 404
    return jsonify({'ok': True})


@bp.get('/categories')
@require_line_auth
def list_categories():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT DISTINCT category FROM stock_holdings
                   WHERE line_user_id=%s AND category IS NOT NULL AND category<>''
                   ORDER BY category''',
                (g.user_id,),
            )
            return jsonify([row['category'] for row in cur.fetchall()])


def _normalize(data):
    return (
        data['market'],
        data['symbol'].strip().upper(),
        _str_or_none(data.get('name')),
        _str_or_none(data.get('category')),
        float(data['shares']),
        float(data['avg_price']),
        data.get('purchase_date') or None,
        _str_or_none(data.get('note')),
    )


def _serialize_row(r):
    return {
        **r,
        'shares': float(r['shares']) if r['shares'] is not None else None,
        'avg_price': float(r['avg_price']) if r['avg_price'] is not None else None,
        'purchase_date': r['purchase_date'].isoformat() if r['purchase_date'] is not None else None,
    }


def _validate(data):
    if data.get('market') not in VALID_MARKETS:
        return 'market 必須為 TW 或 US'
    symbol = data.get('symbol')
    if not symbol or not str(symbol).strip():
        return 'symbol 必填'
    if len(str(symbol).strip()) > 20:
        return 'symbol 長度不可超過 20'
    name = data.get('name')
    if name is not None and len(str(name).strip()) > 100:
        return 'name 長度不可超過 100'
    try:
        shares = float(data.get('shares'))
        avg = float(data.get('avg_price'))
    except (TypeError, ValueError):
        return 'shares / avg_price 必須為數字'
    if shares <= 0 or shares >= 1e14:
        return 'shares 必須介於 0 到 100,000,000,000,000 之間'
    if avg < 0 or avg >= 1e14:
        return 'avg_price 必須介於 0 到 100,000,000,000,000 之間'
    return None


def _str_or_none(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None
