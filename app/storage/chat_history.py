from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ChatHistoryEntry:
    created_at: str
    role: str
    content: str
    translation: str = ""
    tone: str = ""
    portrait: str = ""
    audio_path: str = ""

    def display_content(self, subtitle_language: str) -> str:
        if self.role == "assistant" and subtitle_language == "zh" and self.translation.strip():
            return self.translation.strip()
        return self.content


class ChatHistoryStore:
    """按 JSONL 保存聊天历史，避免单条坏记录影响整体读取。"""

    def __init__(self, path: Path, assistant_name: str = "桜") -> None:
        self.path = path
        self.assistant_name = assistant_name

    def append(
        self,
        role: str,
        content: str,
        translation: str = "",
        tone: str = "",
        portrait: str = "",
        audio_path: str = "",
        _debug: dict | None = None,
    ) -> None:
        entry = {
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "role": role,
            "content": content,
        }
        if translation.strip():
            entry["translation"] = translation.strip()
        if tone.strip():
            entry["tone"] = tone.strip()
        if portrait.strip():
            entry["portrait"] = portrait.strip()
        if audio_path.strip():
            entry["audio_path"] = audio_path.strip()
        if _debug is not None:
            entry["_debug"] = _debug
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @property
    def audio_archive_dir(self) -> Path:
        return self.path.parent.parent / "chat_audio" / self.path.stem

    def attach_audio_to_latest_matching_assistant(
        self,
        content: str,
        translation: str = "",
        tone: str = "",
        portrait: str = "",
        audio_path: str = "",
    ) -> bool:
        if not audio_path.strip() or not self.path.exists():
            return False

        normalized = _normalized_segment_fields(content, translation, tone, portrait)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        target_index: int | None = None
        for index in range(len(lines) - 1, -1, -1):
            line = lines[index].strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("role") != "assistant":
                continue
            if str(data.get("audio_path", "")).strip():
                continue
            entry_fields = _normalized_segment_fields(
                str(data.get("content", "")),
                str(data.get("translation", "")),
                str(data.get("tone", "")),
                str(data.get("portrait", "")),
            )
            if entry_fields == normalized:
                target_index = index
                break

        if target_index is None:
            return False

        data = json.loads(lines[target_index])
        data["audio_path"] = audio_path.strip()
        lines[target_index] = json.dumps(data, ensure_ascii=False)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True

    def load(self) -> list[ChatHistoryEntry]:
        if not self.path.exists():
            return []

        entries: list[ChatHistoryEntry] = []
        for raw_line in self.path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue

            created_at = data.get("created_at")
            role = data.get("role")
            content = data.get("content")
            translation = data.get("translation", "")
            tone = data.get("tone", "")
            portrait = data.get("portrait", "")
            audio_path = data.get("audio_path", "")
            if not all(isinstance(value, str) for value in (created_at, role, content)):
                continue
            if not isinstance(translation, str):
                translation = ""
            if not isinstance(tone, str):
                tone = ""
            if not isinstance(portrait, str):
                portrait = ""
            if not isinstance(audio_path, str):
                audio_path = ""
            entries.append(
                ChatHistoryEntry(
                    created_at=created_at,
                    role=role,
                    content=content,
                    translation=translation,
                    tone=tone,
                    portrait=portrait,
                    audio_path=audio_path,
                )
            )
        return entries

    def clear(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        archive_dir = self.audio_archive_dir
        if archive_dir.exists():
            for audio_file in archive_dir.iterdir():
                if audio_file.is_file():
                    audio_file.unlink(missing_ok=True)
        self.path.write_text("", encoding="utf-8")


def _normalized_segment_fields(
    content: str,
    translation: str,
    tone: str,
    portrait: str,
) -> tuple[str, str, str, str]:
    return (
        content.strip(),
        translation.strip(),
        tone.strip(),
        portrait.strip(),
    )
