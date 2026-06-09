from __future__ import annotations

from pathlib import Path

from app.auth.session import UserSession
from app.character.persona_db import CharacterPersonaDB
from app.config.character_loader import (
    CharacterConfigError,
    CharacterProfile,
    read_character_card,
    write_character_card,
)


def read_effective_persona(profile: CharacterProfile, db_path: Path) -> str:
    """优先读取 SQLite 人设，缺失时回退到角色包 card 文件。"""
    record = CharacterPersonaDB(db_path).get_by_character_id(profile.id)
    if record is not None and record.is_enabled and record.persona_text.strip():
        return record.persona_text
    return read_character_card(profile)


def save_persona(
    profile: CharacterProfile,
    content: str,
    db_path: Path,
    *,
    updated_by_user_id: int | None = None,
) -> None:
    """同时写入角色包 card 与 SQLite。"""
    write_character_card(profile, content)
    user_id = updated_by_user_id
    if user_id is None and UserSession.user_id is not None:
        user_id = UserSession.user_id
    CharacterPersonaDB(db_path).upsert(
        profile.id,
        profile.display_name,
        content,
        initial_message=profile.initial_message,
        updated_by_user_id=user_id,
    )


def resolve_persona_text(
    profile: CharacterProfile,
    db_path: Path | None,
) -> str:
    if db_path is None:
        return read_character_card(profile)
    try:
        return read_effective_persona(profile, db_path)
    except CharacterConfigError:
        record = CharacterPersonaDB(db_path).get_by_character_id(profile.id)
        if record is not None and record.is_enabled and record.persona_text.strip():
            return record.persona_text
        raise
