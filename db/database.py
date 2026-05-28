import sqlite3

from utils.config import DATABASE_PATH
from utils.logger import log_info, log_error

class DatabaseManager:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.conn.cursor()

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
    
        # 用户注册
    def register_user(self, username, password):

        try:

            self.cursor.execute("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
            """, (username, password))

            self.conn.commit()

            log_info(f"用户注册成功: {username}")

            return True

        except Exception as e:

            log_error(f"用户注册失败: {e}")

            return False
        
        # 用户登录验证
    def check_login(self, username, password):

        try:

            self.cursor.execute("""
            SELECT * FROM users
            WHERE username = ? AND password = ?
            """, (username, password))

            user = self.cursor.fetchone()

            if user:

                log_info(f"用户登录成功: {username}")

                return True

            else:

                log_error(f"用户登录失败: 用户名或密码错误")

                return False

        except Exception as e:

            log_error(f"登录验证异常: {e}")

            return False
        
        # 保存聊天记录
    def save_history(self, user_id, speech_text, ai_response):

        try:

            self.cursor.execute("""
            INSERT INTO history (
                user_id,
                speech_text,
                ai_response
            )
            VALUES (?, ?, ?)
            """, (user_id, speech_text, ai_response))

            self.conn.commit()

            log_info("聊天记录保存成功")

            return True

        except Exception as e:

            log_error(f"聊天记录保存失败: {e}")

            return False