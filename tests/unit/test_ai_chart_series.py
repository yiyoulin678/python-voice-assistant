from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from app.ai.chart_series import (
    build_metrics_chart_series,
    event_type_display_name,
    parse_event_timestamp,
)
from app.ai.stats import load_ai_events


def test_parse_event_timestamp_accepts_isoformat() -> None:
    event = {"created_at": "2026-06-03T12:00:00+08:00"}
    parsed = parse_event_timestamp(event)
    assert parsed is not None
    assert parsed.hour == 12


def test_event_type_display_name_maps_known_types() -> None:
    assert event_type_display_name("chat_completed") == "完成对话"
    assert event_type_display_name("custom_event") == "custom_event"


def test_build_metrics_chart_series_aggregates_events(tmp_path: Path) -> None:
    now = datetime.now().astimezone()
    yesterday = now - timedelta(days=1)
    events_path = tmp_path / "ai_events.jsonl"
    events_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "chat_completed",
                        "created_at": now.isoformat(timespec="seconds"),
                        "payload": {
                            "latency_ms": 1500,
                            "tools": ["knowledge_search", "memory_search"],
                            "rag_sources": ["课设基础要求.md"],
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "event_type": "chat_completed",
                        "created_at": yesterday.isoformat(timespec="seconds"),
                        "payload": {
                            "latency_ms": 900,
                            "tools": ["knowledge_search"],
                            "rag_sources": [],
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "event_type": "reply_parse_retry",
                        "created_at": now.isoformat(timespec="seconds"),
                        "payload": {"reason": "empty"},
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    series = build_metrics_chart_series(load_ai_events(events_path))
    assert sum(series.daily_chat_counts) == 2
    assert series.rag_hit_chats == 1
    assert series.rag_total_chats == 2
    assert series.latency_values_ms == [900, 1500]
    assert series.tool_labels[0] == "knowledge_search"
    assert series.tool_counts[0] == 2
    assert "完成对话" in series.event_type_labels
