from __future__ import annotations

from pathlib import Path

from app.ai.session_summary import (
    SessionTurn,
    append_session_summary,
    session_summary_note_path,
    should_summarize_turn,
)


def test_should_summarize_turn_requires_both_sides() -> None:
    assert should_summarize_turn(SessionTurn("你好", "这是一段足够长的助手回复。"))
    assert not should_summarize_turn(SessionTurn("", "回复"))
    assert not should_summarize_turn(SessionTurn("你好", ""))


def test_append_session_summary_writes_markdown_block(tmp_path: Path) -> None:
    note_path = session_summary_note_path(tmp_path, "anan_1")
    append_session_summary(
        note_path,
        "- 讨论了课设要求\n- 下一步做统计图",
        timestamp="2026-06-03 12:00",
    )
    text = note_path.read_text(encoding="utf-8")
    assert "## [2026-06-03 12:00]" in text
    assert "课设要求" in text
