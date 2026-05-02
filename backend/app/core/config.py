import os


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    LIFF_ID = os.getenv('LIFF_ID')
    JSON_AS_ASCII = False
    LINE_CHANNEL_ID = os.getenv('LINE_CHANNEL_ID')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '3306'))


LIFF_ID = Config.LIFF_ID

DB_CONFIG = {
    'host': Config.DB_HOST,
    'port': Config.DB_PORT,
    'database': Config.DB_NAME,
    'user': Config.DB_USER,
    'password': Config.DB_PASSWORD,
    'charset': 'utf8mb4',
}

_REQUIRED_KEYS = ['SECRET_KEY', 'LIFF_ID', 'LINE_CHANNEL_ID', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']


def validate_config(app):
    missing = [k for k in _REQUIRED_KEYS if not app.config.get(k)]
    if missing:
        raise RuntimeError(f'缺少必要環境變數：{", ".join(missing)}')
