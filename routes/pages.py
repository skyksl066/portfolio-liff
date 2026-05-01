import os
from flask import Blueprint, render_template, current_app

pages_bp = Blueprint('pages', __name__)


@pages_bp.get('/')
def index():
    return render_template(
        'index.html',
        liff_id=current_app.config.get('LIFF_ID') or '',
        dev_mode=(os.getenv('FLASK_ENV') == 'development'),
        script_root=os.getenv('SCRIPT_NAME', ''),
    )
