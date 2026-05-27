import sqlite3

from utils.config import DATABASE_PATH
from utils.logger import log_info, log_error


class DatabaseManager:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.conn.cursor()

    def create_tables(self):
        pass

    # 创建数据库表
    def create_tables(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            create_time TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            speech_text TEXT,
            ai_response TEXT,
            create_time TEXT
        )
        """)

        self.conn.commit()

        log_info("数据库表创建成功")