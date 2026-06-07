from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Live2DMotionEntry:
    group: str
    index: int
    name: str
    file_name: str


def load_motion_catalog(model_json_path: Path) -> dict[str, Live2DMotionEntry]:
    """从 model3.json 读取动作名 → (组, 索引) 映射，对齐 Alife DeskPet 的 motion 指令。"""
    try:
        data = json.loads(model_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}

    motions = data.get("FileReferences", {}).get("Motions")
    if not isinstance(motions, dict):
        return {}

    catalog: dict[str, Live2DMotionEntry] = {}
    for group, entries in motions.items():
        if not isinstance(group, str) or not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("Name", "")).strip()
            file_name = str(entry.get("File", "")).strip()
            if not name:
                continue
            catalog[name] = Live2DMotionEntry(
                group=group,
                index=index,
                name=name,
                file_name=file_name,
            )
    return catalog


def resolve_motion_file(model_dir: Path, file_name: str) -> Path | None:
    if not file_name:
        return None
    candidate = model_dir / file_name
    return candidate if candidate.is_file() else None
