import os

LINE_CHANNEL_ID = os.getenv('LINE_CHANNEL_ID')
LIFF_ID = os.getenv('LIFF_ID')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'charset': 'utf8mb4',
}

_REQUIRED = {
    'FLASK_SECRET_KEY': os.getenv('FLASK_SECRET_KEY'),
    'LINE_CHANNEL_ID': LINE_CHANNEL_ID,
    'DB_NAME': os.getenv('DB_NAME'),
    'DB_USER': os.getenv('DB_USER'),
    'DB_PASSWORD': os.getenv('DB_PASSWORD'),
}


def validate_config():
    missing = [k for k, v in _REQUIRED.items() if not v]
    if missing:
        raise RuntimeError(f"缺少必要環境變數：{', '.join(missing)}")
