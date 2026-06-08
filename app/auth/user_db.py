from pathlib import Path
import sqlite3
import hashlib


class UserDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT
        )
        """)

        conn.commit()
        conn.close()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM users"
        )

        count = cursor.fetchone()[0]

        if count == 0:
            conn.execute(
                """
                INSERT INTO users(
                    username,
                    password_hash,
                    role
                )
                VALUES(?,?,?)
                """,
                (
                    "admin",
                    self.hash_password("admin123"),
                    "admin"
                )
            )
            conn.commit()
        conn.close()

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "user"
    ):
        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            INSERT INTO users(username,password_hash,role)
            VALUES(?,?,?)
            """,
            (
                username,
                self.hash_password(password),
                role
            )
        )

        conn.commit()
        conn.close()

    def verify_user(
        self,
        username: str,
        password: str
    ):
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """
            SELECT id,role,password_hash
            FROM users
            WHERE username=?
            """,
            (username,)
        )

        row = cursor.fetchone()

        conn.close()

        if not row:
            return None

        user_id, role, password_hash = row

        if password_hash == self.hash_password(password):
            return user_id, role

        return None
    
    def user_exists(self, username: str) -> bool:

        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """
            SELECT 1
            FROM users
            WHERE username=?
            """,
            (username,)
        )

        result = cursor.fetchone()

        conn.close()

        return result is not None
    
    def get_all_users(self):

        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """
            SELECT
                id,
                username,
                role
            FROM users
            ORDER BY id
            """
        )

        users = cursor.fetchall()

        conn.close()

        return users
    
    def delete_user(self, user_id: int):

        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            DELETE FROM users
            WHERE id=?
            """,
            (user_id,)
        )

        conn.commit()
        conn.close()

    def get_user_by_id(self, user_id: int):

        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """
            SELECT
                id,
                username,
                role
            FROM users
            WHERE id=?
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        conn.close()

        return user
    
    def user_exists(
        self,
        username: str
    ):

        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username=?
            """,
            (username,)
        )

        result = cursor.fetchone()

        conn.close()

        return result is not None
    
    def reset_password(
        self,
        user_id: int,
        new_password: str
    ):

        conn = sqlite3.connect(
            self.db_path
        )

        conn.execute(
            """
            UPDATE users
            SET password_hash=?
            WHERE id=?
            """,
            (
                self.hash_password(
                    new_password
                ),
                user_id
            )
        )

        conn.commit()

        conn.close()

    def get_user(
        self,
        username: str,
        password: str
    ):

        conn = sqlite3.connect(
            self.db_path
        )

        cursor = conn.execute(
            """
            SELECT
                id,
                username,
                role,
                password_hash
            FROM users
            WHERE username=?
            """,
            (username,)
        )

        row = cursor.fetchone()

        conn.close()

        if row is None:
            return None

        user_id, username, role, password_hash = row

        if password_hash != self.hash_password(password):
            return None

        return (
            user_id,
            username,
            role
        )