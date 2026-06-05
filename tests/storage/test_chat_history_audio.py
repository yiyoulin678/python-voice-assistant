from __future__ import annotations

import uuid
from pathlib import Path

from app.storage.chat_audio import archive_chat_audio, chat_audio_dir
from app.storage.chat_history import ChatHistoryStore


def _history_path(root: Path) -> Path:
    return root / "data" / "chat_history" / f"{uuid.uuid4().hex}.jsonl"


def test_chat_history_store_round_trips_audio_path() -> None:
    root = Path(__file__).resolve().parents[2] / "temp" / "test_runtime" / uuid.uuid4().hex
    store = ChatHistoryStore(_history_path(root))

    store.append("assistant", "こんばんは", "晚上好", "中性", "微笑", audio_path="data/chat_audio/test.wav")

    entries = store.load()
    assert len(entries) == 1
    assert entries[0].audio_path == "data/chat_audio/test.wav"


def test_attach_audio_to_latest_matching_assistant_updates_jsonl() -> None:
    root = Path(__file__).resolve().parents[2] / "temp" / "test_runtime" / uuid.uuid4().hex
    store = ChatHistoryStore(_history_path(root))
    store.append("assistant", "一つ目", "第一段", "中性", "微笑")
    store.append("assistant", "二つ目", "第二段", "困惑", "疑问")

    attached_first = store.attach_audio_to_latest_matching_assistant(
        "一つ目",
        "第一段",
        "中性",
        "微笑",
        "data/chat_audio/first.wav",
    )
    attached_second = store.attach_audio_to_latest_matching_assistant(
        "二つ目",
        "第二段",
        "困惑",
        "疑问",
        "data/chat_audio/second.wav",
    )

    entries = store.load()
    assert attached_first is True
    assert attached_second is True
    assert entries[0].audio_path == "data/chat_audio/first.wav"
    assert entries[1].audio_path == "data/chat_audio/second.wav"


def test_archive_chat_audio_copies_file_under_character_dir() -> None:
    root = Path(__file__).resolve().parents[2] / "temp" / "test_runtime" / uuid.uuid4().hex
    source = root / "tmp.wav"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"RIFFdemo")

    relative_path = archive_chat_audio(source, root, "anan")

    archived = root / relative_path
    assert archived.exists()
    assert archived.read_bytes() == b"RIFFdemo"
    assert archived.parent == chat_audio_dir(root, "anan")


def test_clear_history_removes_archived_audio_files() -> None:
    root = Path(__file__).resolve().parents[2] / "temp" / "test_runtime" / uuid.uuid4().hex
    character_id = "anan"
    store = ChatHistoryStore(root / "data" / "chat_history" / f"{character_id}.jsonl")
    archive_dir = chat_audio_dir(root, character_id)
    archive_dir.mkdir(parents=True, exist_ok=True)
    audio_file = archive_dir / "sample.wav"
    audio_file.write_bytes(b"RIFFdemo")
    store.append("assistant", "测试", audio_path=str(audio_file.relative_to(root)))

    store.clear()

    assert store.load() == []
    assert not audio_file.exists()
