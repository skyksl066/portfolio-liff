import os
from flask import Flask, request

from core.config import validate_config
from routes.api import api_bp
from routes.pages import pages_bp

validate_config()

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']
app.config['LIFF_ID'] = os.getenv('LIFF_ID')
app.json.ensure_ascii = False

app.register_blueprint(pages_bp)
app.register_blueprint(api_bp, url_prefix='/api')


@app.after_request
def set_static_cache_headers(response):
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return response


@app.get('/health')
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(debug=False)
