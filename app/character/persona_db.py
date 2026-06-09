from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3

from app.config.character_loader import (
    CharacterConfigError,
    CharacterProfile,
    CharacterRegistry,
    read_character_card,
)


@dataclass(frozen=True)
class CharacterPersonaRecord:
    id: int
    character_id: str
    display_name: str
    persona_text: str
    initial_message: str
    is_enabled: bool
    created_at: str
    updated_at: str
    updated_by_user_id: int | None


class CharacterPersonaDB:
    """SQLite 角色人设 CRUD，与 users.db 共用同一数据库文件。"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.init_db()

    def init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS character_personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                persona_text TEXT NOT NULL,
                initial_message TEXT NOT NULL DEFAULT '',
                is_enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by_user_id INTEGER
            )
            """
        )
        conn.commit()
        conn.close()

    def upsert(
        self,
        character_id: str,
        display_name: str,
        persona_text: str,
        *,
        initial_message: str = "",
        is_enabled: bool = True,
        updated_by_user_id: int | None = None,
    ) -> int:
        normalized_id = character_id.strip()
        normalized_name = display_name.strip()
        normalized_text = persona_text.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized_id:
            raise ValueError("角色 ID 不能为空。")
        if not normalized_name:
            raise ValueError("显示名称不能为空。")
        if not normalized_text.strip():
            raise ValueError("人设内容不能为空。")

        now = _now_iso()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            INSERT INTO character_personas (
                character_id,
                display_name,
                persona_text,
                initial_message,
                is_enabled,
                created_at,
                updated_at,
                updated_by_user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(character_id) DO UPDATE SET
                display_name=excluded.display_name,
                persona_text=excluded.persona_text,
                initial_message=excluded.initial_message,
                is_enabled=excluded.is_enabled,
                updated_at=excluded.updated_at,
                updated_by_user_id=excluded.updated_by_user_id
            """,
            (
                normalized_id,
                normalized_name,
                normalized_text,
                initial_message.strip(),
                1 if is_enabled else 0,
                now,
                now,
                updated_by_user_id,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        if row_id in (None, 0):
            row_id = self._id_for_character_id(conn, normalized_id)
        conn.close()
        return int(row_id)

    def get_by_character_id(self, character_id: str) -> CharacterPersonaRecord | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT
                id,
                character_id,
                display_name,
                persona_text,
                initial_message,
                is_enabled,
                created_at,
                updated_at,
                updated_by_user_id
            FROM character_personas
            WHERE character_id=?
            """,
            (character_id.strip(),),
        )
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return _row_to_record(row)

    def get_by_id(self, record_id: int) -> CharacterPersonaRecord | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT
                id,
                character_id,
                display_name,
                persona_text,
                initial_message,
                is_enabled,
                created_at,
                updated_at,
                updated_by_user_id
            FROM character_personas
            WHERE id=?
            """,
            (record_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return _row_to_record(row)

    def get_all(self) -> list[CharacterPersonaRecord]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT
                id,
                character_id,
                display_name,
                persona_text,
                initial_message,
                is_enabled,
                created_at,
                updated_at,
                updated_by_user_id
            FROM character_personas
            ORDER BY id
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return [_row_to_record(row) for row in rows]

    def delete_by_character_id(self, character_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            DELETE FROM character_personas
            WHERE character_id=?
            """,
            (character_id.strip(),),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def delete_by_id(self, record_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            DELETE FROM character_personas
            WHERE id=?
            """,
            (record_id,),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM character_personas")
        count = int(cursor.fetchone()[0])
        conn.close()
        return count

    def seed_missing_from_registry(self, registry: CharacterRegistry) -> int:
        """将角色包内 card 文件导入数据库（仅补缺，不覆盖已有记录）。"""
        seeded = 0
        for profile in registry.all():
            if self.get_by_character_id(profile.id) is not None:
                continue
            try:
                persona_text = read_character_card(profile)
            except CharacterConfigError:
                continue
            self.upsert(
                profile.id,
                profile.display_name,
                persona_text,
                initial_message=profile.initial_message,
            )
            seeded += 1
        return seeded

    def import_from_profile(self, profile: CharacterProfile) -> int:
        """强制用角色包 card 覆盖数据库记录。"""
        persona_text = read_character_card(profile)
        return self.upsert(
            profile.id,
            profile.display_name,
            persona_text,
            initial_message=profile.initial_message,
        )

    def _id_for_character_id(self, conn: sqlite3.Connection, character_id: str) -> int:
        cursor = conn.execute(
            "SELECT id FROM character_personas WHERE character_id=?",
            (character_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"未找到人设记录：{character_id}")
        return int(row[0])


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _row_to_record(row: tuple[object, ...]) -> CharacterPersonaRecord:
    return CharacterPersonaRecord(
        id=int(row[0]),
        character_id=str(row[1]),
        display_name=str(row[2]),
        persona_text=str(row[3]),
        initial_message=str(row[4]),
        is_enabled=bool(row[5]),
        created_at=str(row[6]),
        updated_at=str(row[7]),
        updated_by_user_id=int(row[8]) if row[8] is not None else None,
    )
