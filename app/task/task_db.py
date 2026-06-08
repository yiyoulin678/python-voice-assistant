import sqlite3


class TaskDB:

    def __init__(self, db_path):

        self.conn = sqlite3.connect(
            db_path
        )

        self.create_table()

    def create_table(self):

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_tasks
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT,
                result TEXT
            )
            """
        )

        self.conn.commit()

    def create_task(
        self,
        user_id: int,
        title: str,
        prompt: str
    ):

        cursor = self.conn.execute(
            """
            INSERT INTO ai_tasks(
                user_id,
                title,
                prompt,
                status
            )
            VALUES(?,?,?,?)
            """,
            (
                user_id,
                title,
                prompt,
                "pending"
            )
        )

        self.conn.commit()

        return cursor.lastrowid

    def get_all_tasks(self):

        cursor = self.conn.execute(
            """
            SELECT
                id,
                user_id,
                title,
                status
            FROM ai_tasks
            ORDER BY id DESC
            """
        )

        return cursor.fetchall()
    
    def get_tasks_by_user(
        self,
        user_id: int
    ):

        cursor = self.conn.execute(
            """
            SELECT
                id,
                title,
                status
            FROM ai_tasks
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (user_id,)
        )

        return cursor.fetchall()
    
    def update_task_status(
        self,
        task_id: int,
        status: str
    ):

        self.conn.execute(
            """
            UPDATE ai_tasks
            SET status=?
            WHERE id=?
            """,
            (
                status,
                task_id
            )
        )

        self.conn.commit()

    def update_task_result(
        self,
        task_id: int,
        result: str
    ):

        self.conn.execute(
            """
            UPDATE ai_tasks
            SET result=?
            WHERE id=?
            """,
            (
                result,
                task_id
            )
        )

        self.conn.commit()

    def delete_task(
        self,
        task_id: int
    ):

        self.conn.execute(
            """
            DELETE FROM ai_tasks
            WHERE id=?
            """,
            (task_id,)
        )

        self.conn.commit()

    def get_task_by_id(
        self,
        task_id: int
    ):

        cursor = self.conn.execute(
            """
            SELECT
                id,
                user_id,
                title,
                prompt,
                status,
                result
            FROM ai_tasks
            WHERE id=?
            """,
            (task_id,)
        )

        return cursor.fetchone()