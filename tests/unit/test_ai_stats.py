from __future__ import annotations

import json
from pathlib import Path

from app.ai.stats import load_ai_events, summarize_ai_events


def test_summarize_ai_events(tmp_path: Path) -> None:
    events_path = tmp_path / "ai_events.jsonl"
    events_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "chat_completed",
                        "created_at": "2026-06-03T12:00:00+08:00",
                        "payload": {
                            "latency_ms": 1200,
                            "tones": ["开心", "中性"],
                            "tools": ["knowledge_search"],
                            "rag_sources": ["课设基础要求.md"],
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "event_type": "reply_parse_retry",
                        "created_at": "2026-06-03T12:01:00+08:00",
                        "payload": {"reason": "empty"},
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    events = load_ai_events(events_path)
    summary = summarize_ai_events(events)
    assert summary.chat_completed == 1
    assert summary.reply_parse_retry == 1
    assert summary.average_latency_ms == 1200
    assert summary.tone_counts["开心"] == 1
    assert summary.tool_counts["knowledge_search"] == 1
    assert summary.rag_hit_events == 1
