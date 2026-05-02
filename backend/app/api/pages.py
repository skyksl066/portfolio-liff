import os
from flask import Blueprint, render_template, current_app

bp = Blueprint('pages', __name__)


@bp.get('/')
def index():
    return render_template('index.html', app_config={
        'liffId': current_app.config.get('LIFF_ID') or '',
        'devMode': os.getenv('FLASK_ENV') == 'development',
        'scriptRoot': os.getenv('SCRIPT_NAME', ''),
    })
