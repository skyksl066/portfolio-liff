#!/usr/bin/env python3
"""FTP deployment script for portfolio-liff.

Uploads all required project files to the shared hosting server and
touches tmp/restart.txt to trigger a Passenger application reload.

Required environment variables:
    FTP_HOST, FTP_USER, FTP_PASSWORD
"""
import ftplib
import os
import sys
from datetime import datetime, timezone

FILES_TO_UPLOAD = [
    ('app.py',                    'app.py'),
    ('requirements.txt',          'requirements.txt'),
    # core package
    ('core/__init__.py',          'core/__init__.py'),
    ('core/auth.py',              'core/auth.py'),
    ('core/config.py',            'core/config.py'),
    ('core/db.py',                'core/db.py'),
    # routes package
    ('routes/__init__.py',        'routes/__init__.py'),
    ('routes/api.py',             'routes/api.py'),
    ('routes/pages.py',           'routes/pages.py'),
    # templates
    ('templates/base.html',       'templates/base.html'),
    ('templates/index.html',      'templates/index.html'),
    # static (compiled output only — no source files)
    ('static/css/style.css',      'static/css/style.css'),
    ('static/dist/bundle.js',     'static/dist/bundle.js'),
]


def ensure_dir(ftp: ftplib.FTP, path: str) -> None:
    """Recursively create remote directories if they don't exist."""
    parts = path.replace('\\', '/').split('/')
    for i, part in enumerate(parts):
        if not part:
            continue
        current = '/'.join(parts[:i + 1])
        try:
            ftp.mkd(current)
        except ftplib.error_perm as e:
            if not str(e).startswith('550'):
                raise


def upload_file(ftp: ftplib.FTP, local_path: str, remote_path: str) -> None:
    remote_dir = '/'.join(remote_path.replace('\\', '/').split('/')[:-1])
    if remote_dir:
        ensure_dir(ftp, remote_dir)
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_path}', f)
    print(f'[FTP] Uploaded: {remote_path}')


def upload_restart_flag(ftp: ftplib.FTP) -> None:
    """Touch tmp/restart.txt to trigger Passenger reload."""
    import io
    ensure_dir(ftp, 'tmp')
    content = datetime.now(timezone.utc).isoformat().encode()
    ftp.storbinary('STOR tmp/restart.txt', io.BytesIO(content))
    print('[FTP] Triggered restart: tmp/restart.txt')


def main() -> None:
    ftp_host = os.getenv('FTP_HOST')
    ftp_user = os.getenv('FTP_USER')
    ftp_password = os.getenv('FTP_PASSWORD')

    missing = [k for k, v in {
        'FTP_HOST': ftp_host,
        'FTP_USER': ftp_user,
        'FTP_PASSWORD': ftp_password,
    }.items() if not v]
    if missing:
        print(f'[FTP] Missing env vars: {", ".join(missing)}')
        sys.exit(1)

    try:
        with ftplib.FTP(ftp_host) as ftp:
            ftp.login(ftp_user, ftp_password)
            print(f'[FTP] Connected to {ftp_host}')

            for local_path, remote_path in FILES_TO_UPLOAD:
                if not os.path.exists(local_path):
                    print(f'[FTP] SKIP (not found): {local_path}')
                    continue
                upload_file(ftp, local_path, remote_path)

            upload_restart_flag(ftp)

        print('[FTP] Deployment completed successfully')
    except ftplib.all_errors as e:
        print(f'[FTP] Error: {type(e).__name__}: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
