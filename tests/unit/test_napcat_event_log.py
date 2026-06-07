from __future__ import annotations

from app.platforms.napcat.event_log import NapCatEventLog


def test_napcat_event_log_keeps_recent_entries() -> None:
    log = NapCatEventLog()
    for index in range(510):
        log.append(f"line-{index}")
    entries = log.entries()
    assert len(entries) == 500
    assert entries[0].message == "line-10"
    assert entries[-1].message == "line-509"


def test_napcat_log_entry_format_includes_detail() -> None:
    log = NapCatEventLog()
    entry = log.append("收到 QQ 消息", {"text": "你好"})
    formatted = entry.format_line()
    assert "收到 QQ 消息" in formatted
    assert "你好" in formatted
