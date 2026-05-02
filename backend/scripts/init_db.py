# backend/scripts/init_db.py
import sqlite3  # 或 mysql

with open("../sql/schema.sql", "r") as f:
    sql = f.read()

conn = sqlite3.connect("app.db")
conn.executescript(sql)
conn.close()