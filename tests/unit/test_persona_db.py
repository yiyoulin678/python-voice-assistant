from __future__ import annotations

from pathlib import Path

import pytest

from app.character.persona_db import CharacterPersonaDB
from app.character.persona_service import read_effective_persona, save_persona
from app.config.character_loader import (
    CharacterProfile,
    CharacterRegistry,
    load_character_system_prompt,
    read_character_card,
)


def _profile(card_path: Path, *, character_id: str = "test") -> CharacterProfile:
    return CharacterProfile(
        id=character_id,
        display_name="测试角色",
        package_dir=card_path.parent,
        card_path=card_path,
        initial_message="你好",
        default_portrait_path=card_path.parent / "portraits" / "normal.png",
    )


def _build_registry(root: Path) -> CharacterRegistry:
    package_dir = root / "characters" / "demo"
    package_dir.mkdir(parents=True)
    card_path = package_dir / "card.md"
    card_path.write_text("文件人设", encoding="utf-8")
    (package_dir / "portraits").mkdir()
    (package_dir / "portraits" / "normal.png").write_bytes(b"png")
    manifest = {
        "id": "demo",
        "display_name": "演示",
        "card": "card.md",
        "initial_message": "嗨",
        "portrait": {"default": "portraits/normal.png"},
    }
    import json

    (package_dir / "character.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    return CharacterRegistry(root)


def test_persona_db_crud_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "users.db"
    db = CharacterPersonaDB(db_path)

    record_id = db.upsert("sakura", "桜", "数据库人设\n")
    assert record_id > 0
    assert db.count() == 1

    record = db.get_by_character_id("sakura")
    assert record is not None
    assert record.display_name == "桜"
    assert record.persona_text == "数据库人设\n"

    db.upsert("sakura", "桜改", "更新后的人设")
    updated = db.get_by_character_id("sakura")
    assert updated is not None
    assert updated.display_name == "桜改"
    assert updated.persona_text == "更新后的人设"

    assert db.delete_by_character_id("sakura")
    assert db.get_by_character_id("sakura") is None


def test_persona_db_rejects_empty_content(tmp_path: Path) -> None:
    db = CharacterPersonaDB(tmp_path / "users.db")
    with pytest.raises(ValueError, match="不能为空"):
        db.upsert("demo", "演示", "   ")


def test_seed_missing_from_registry(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    db = CharacterPersonaDB(tmp_path / "users.db")
    seeded = db.seed_missing_from_registry(registry)
    assert seeded == 1
    record = db.get_by_character_id("demo")
    assert record is not None
    assert record.persona_text == "文件人设"

    assert db.seed_missing_from_registry(registry) == 0


def test_read_effective_persona_prefers_database(tmp_path: Path) -> None:
    card_path = tmp_path / "card.md"
    card_path.write_text("文件人设", encoding="utf-8")
    profile = _profile(card_path)
    db_path = tmp_path / "users.db"
    CharacterPersonaDB(db_path).upsert(profile.id, profile.display_name, "数据库优先")

    assert read_effective_persona(profile, db_path) == "数据库优先"


def test_save_persona_syncs_file_and_database(tmp_path: Path) -> None:
    card_path = tmp_path / "card.md"
    card_path.write_text("旧内容", encoding="utf-8")
    profile = _profile(card_path)
    db_path = tmp_path / "users.db"

    save_persona(profile, "新内容\n", db_path)

    assert read_character_card(profile) == "新内容\n"
    record = CharacterPersonaDB(db_path).get_by_character_id(profile.id)
    assert record is not None
    assert record.persona_text == "新内容\n"


def test_load_character_system_prompt_uses_database(tmp_path: Path) -> None:
    card_path = tmp_path / "card.md"
    card_path.write_text("文件", encoding="utf-8")
    profile = _profile(card_path)
    db_path = tmp_path / "users.db"
    CharacterPersonaDB(db_path).upsert(profile.id, profile.display_name, "来自 SQLite")

    prompt = load_character_system_prompt(
        profile,
        append_desktop_pet_rules=False,
        db_path=db_path,
    )
    assert prompt == "来自 SQLite"
