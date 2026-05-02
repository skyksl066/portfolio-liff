from flask import Blueprint

bp = Blueprint('system', __name__)


@bp.get('/health')
def health():
    return 'ok'
