from __future__ import annotations

import shutil
import uuid
from pathlib import Path


def chat_audio_dir(base_dir: Path, character_id: str) -> Path:
    return base_dir / "data" / "chat_audio" / character_id


def archive_chat_audio(source: Path, base_dir: Path, character_id: str) -> str:
    """复制临时 TTS 音频到持久目录，返回相对 base_dir 的路径。"""
    if not source.exists():
        raise FileNotFoundError(f"音频不存在：{source}")

    destination_dir = chat_audio_dir(base_dir, character_id)
    destination_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix or ".wav"
    destination = destination_dir / f"{uuid.uuid4().hex}{suffix}"
    shutil.copy2(source, destination)
    return destination.relative_to(base_dir).as_posix()
