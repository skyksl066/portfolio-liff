import os
import sys

# When loaded via passenger_wsgi.py, this file's directory (backend/) is not
# automatically on sys.path, so we add it explicitly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()
application = app  # Passenger expects the WSGI callable to be named 'application'

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'production')
    debug = env == 'development'
    app.run(debug=debug)
