import os
from pathlib import Path
from flask import Flask, request
from .core.config import Config, validate_config

_FRONTEND_DIST = Path(__file__).parent.parent.parent / 'frontend' / 'dist'


def create_app():
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder=str(_FRONTEND_DIST),
        static_url_path='/static',
    )

    app.config.from_object(Config)
    validate_config(app)

    from .api import register_routes
    register_routes(app)

    @app.after_request
    def set_static_cache_headers(response):
        if request.path.startswith('/static/'):
            if app.debug:
                response.headers['Cache-Control'] = 'no-cache, must-revalidate'
            else:
                response.headers['Cache-Control'] = 'no-cache'
        return response

    return app
