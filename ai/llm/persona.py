"""虚拟女友人设配置。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai.config import AI_SETTINGS_PATH, PERSONA_PATH


def load_persona(path: Path | None = None) -> dict[str, Any]:
    p = path or PERSONA_PATH
    if not p.is_file():
        raise FileNotFoundError(f"人设文件不存在: {p}")
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(persona: dict[str, Any], user_nickname: str) -> str:
    tpl = persona.get("system_prompt_template", "")
    return tpl.format(
        name=persona.get("name", "小音"),
        role=persona.get("role", "语音AI虚拟女友"),
        personality=persona.get("personality", ""),
        speaking_style=persona.get("speaking_style", ""),
        user_nickname=user_nickname or persona.get("user_title", "你"),
        forbidden=persona.get("forbidden", ""),
    )


def build_messages(
    user_text: str,
    user_nickname: str = "你",
    history: list[dict[str, str]] | None = None,
    persona_path: Path | None = None,
) -> list[dict[str, str]]:
    persona = load_persona(persona_path)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(persona, user_nickname)},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages
