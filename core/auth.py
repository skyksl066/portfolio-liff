import os
from functools import wraps
from flask import request, jsonify, g
import requests

from core import config
from core.db import get_conn

LINE_PROFILE_URL = 'https://api.line.me/v2/profile'


def verify_access_token(access_token: str):
    """用 Access Token 呼叫 LINE Profile API 取得 userId。
    Access Token 由 LIFF SDK 自動刷新，不會像 ID Token 一樣短暫過期。
    回傳 {'sub': userId, 'name': displayName}；失敗回 None。
    """
    # 本地開發繞過驗證
    if (os.getenv('FLASK_ENV') == 'development'
            and os.getenv('DEV_MODE_ENABLED') == 'true'):
        from flask import request as _req
        if _req.host.split(':')[0] in ('localhost', '127.0.0.1'):
            return {'sub': 'U_dev_test_user', 'name': 'Dev User'}

    try:
        resp = requests.get(
            LINE_PROFILE_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if 'userId' not in data:
            return None
        return {'sub': data['userId'], 'name': data.get('displayName')}
    except requests.RequestException:
        return None


def is_whitelisted(line_user_id: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT 1 FROM whitelist_users WHERE line_user_id=%s LIMIT 1',
                (line_user_id,),
            )
            return cur.fetchone() is not None


def require_line_auth(f):
    """API decorator：驗證 Access Token + 白名單，通過後將 userId 放入 g.user_id"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'UNAUTHORIZED', 'message': '缺少 token'}), 401

        access_token = auth.removeprefix('Bearer ').strip()
        if not access_token:
            return jsonify({'error': 'UNAUTHORIZED', 'message': '缺少 token'}), 401

        payload = verify_access_token(access_token)
        if not payload:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'token 無效，請重新開啟'}), 401

        user_id = payload['sub']
        if not is_whitelisted(user_id):
            return jsonify({
                'error': 'FORBIDDEN',
                'message': '不在白名單',
                'userId': user_id,
            }), 403

        g.user_id = user_id
        g.display_name = payload.get('name')
        return f(*args, **kwargs)

    return wrapper
