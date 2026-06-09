from __future__ import annotations

from datetime import datetime
import sqlite3

from app.task.constants import STATUS_DONE, STATUS_FAILED, STATUS_PENDING


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

        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        cursor = self.conn.execute(
            """
            INSERT INTO ai_tasks(
                user_id,
                title,
                prompt,
                status,
                created_at
            )
            VALUES(?,?,?,?,?)
            """,
            (
                user_id,
                title,
                prompt,
                STATUS_PENDING,
                created_at,
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
    
    def get_task_count(self):

        cursor = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM ai_tasks
            """
        )

        return cursor.fetchone()[0]
    
    def get_pending_count(self):

        cursor = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM ai_tasks
            WHERE status='pending'
            """
        )

        return cursor.fetchone()[0]
    
    def get_done_count(self):

        cursor = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM ai_tasks
            WHERE status IN ('done', 'finished')
            """
        )

        return cursor.fetchone()[0]

    def list_runnable_task_ids(
        self,
        *,
        user_id: int | None = None,
    ) -> list[int]:
        query = """
            SELECT id
            FROM ai_tasks
            WHERE status IN (?, ?)
        """
        params: list[object] = [STATUS_PENDING, STATUS_FAILED]
        if user_id is not None:
            query += " AND user_id=?"
            params.append(user_id)
        query += " ORDER BY id ASC"
        cursor = self.conn.execute(query, params)
        return [int(row[0]) for row in cursor.fetchall()]