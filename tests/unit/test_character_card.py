from __future__ import annotations

from pathlib import Path

import pytest

from app.config.character_loader import (
    CharacterConfigError,
    CharacterProfile,
    finalize_character_prompt,
    read_character_card,
    write_character_card,
)
from app.llm.prompts.blocks import DESKTOP_PET_CONTEXT


def _profile(card_path: Path) -> CharacterProfile:
    return CharacterProfile(
        id="test",
        display_name="测试",
        package_dir=card_path.parent,
        card_path=card_path,
        initial_message="hello",
        default_portrait_path=card_path.parent / "portraits" / "normal.png",
    )


def test_write_and_read_character_card_roundtrip(tmp_path: Path) -> None:
    card_path = tmp_path / "card.md"
    card_path.write_text("旧人设", encoding="utf-8")
    profile = _profile(card_path)

    write_character_card(profile, "吾輩は猫である。\n")
    assert read_character_card(profile) == "吾輩は猫である。\n"


def test_finalize_character_prompt_skips_desktop_rules_by_default() -> None:
    prompt = finalize_character_prompt("吾輩は猫である", append_desktop_pet_rules=False)
    assert prompt == "吾輩は猫である"
    assert DESKTOP_PET_CONTEXT not in prompt


def test_finalize_character_prompt_appends_desktop_rules_when_enabled() -> None:
    prompt = finalize_character_prompt("吾輣は猫である", append_desktop_pet_rules=True)
    assert "【人格设定】" in prompt
    assert DESKTOP_PET_CONTEXT in prompt


def test_write_character_card_rejects_empty_content(tmp_path: Path) -> None:
    card_path = tmp_path / "card.md"
    card_path.write_text("旧人设", encoding="utf-8")
    profile = _profile(card_path)

    with pytest.raises(CharacterConfigError, match="不能为空"):
        write_character_card(profile, "   \n")
