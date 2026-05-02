from .holdings import bp as holdings_bp
from .users import bp as users_bp
from .pages import bp as pages_bp
from .system import bp as system_bp


def register_routes(app):
    app.register_blueprint(system_bp)
    app.register_blueprint(holdings_bp, url_prefix='/api')
    app.register_blueprint(users_bp, url_prefix='/api')
    app.register_blueprint(pages_bp)
