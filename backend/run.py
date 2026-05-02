import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'production')
    debug = env == 'development'
    app.run(debug=debug)
