import pymysql
import pymysql.cursors
from contextlib import contextmanager
from . import config


@contextmanager
def get_conn():
    try:
        conn = pymysql.connect(
            **config.DB_CONFIG,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    except pymysql.Error as e:
        raise RuntimeError(f'資料庫連線失敗：{e}') from e
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
