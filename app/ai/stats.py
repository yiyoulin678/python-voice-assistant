from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AiMetricsSummary:
    total_events: int = 0
    chat_completed: int = 0
    reply_parse_retry: int = 0
    reply_parse_repaired: int = 0
    average_latency_ms: int = 0
    tone_counts: dict[str, int] = field(default_factory=dict)
    tool_counts: dict[str, int] = field(default_factory=dict)
    rag_hit_events: int = 0


def load_ai_events(path: Path, *, limit: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines[-limit:]:
        text = line.strip()
        if not text:
            continue
        try:
            item = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def summarize_ai_events(events: list[dict[str, Any]]) -> AiMetricsSummary:
    if not events:
        return AiMetricsSummary()

    chat_completed = 0
    reply_parse_retry = 0
    reply_parse_repaired = 0
    latency_total = 0
    latency_count = 0
    tone_counter: Counter[str] = Counter()
    tool_counter: Counter[str] = Counter()
    rag_hit_events = 0

    for event in events:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        if event_type == "chat_completed":
            chat_completed += 1
            latency = payload.get("latency_ms")
            if isinstance(latency, (int, float)) and latency >= 0:
                latency_total += int(latency)
                latency_count += 1
            for tone in payload.get("tones") or []:
                if isinstance(tone, str) and tone.strip():
                    tone_counter[tone.strip()] += 1
            for tool in payload.get("tools") or []:
                if isinstance(tool, str) and tool.strip():
                    tool_counter[tool.strip()] += 1
            rag_sources = payload.get("rag_sources") or []
            if isinstance(rag_sources, list) and rag_sources:
                rag_hit_events += 1
        elif event_type == "reply_parse_retry":
            reply_parse_retry += 1
        elif event_type == "reply_parse_repaired":
            reply_parse_repaired += 1

    average_latency = int(latency_total / latency_count) if latency_count else 0
    return AiMetricsSummary(
        total_events=len(events),
        chat_completed=chat_completed,
        reply_parse_retry=reply_parse_retry,
        reply_parse_repaired=reply_parse_repaired,
        average_latency_ms=average_latency,
        tone_counts=dict(tone_counter),
        tool_counts=dict(tool_counter),
        rag_hit_events=rag_hit_events,
    )


def format_event_brief(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type", "")).strip() or "unknown"
    created_at = str(event.get("created_at", "")).strip()
    payload = event.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    if event_type == "chat_completed":
        preview = str(payload.get("reply_preview", "")).strip()
        latency = payload.get("latency_ms")
        return f"对话完成 · {latency}ms · {preview[:80]}"
    if event_type.startswith("reply_parse"):
        reason = str(payload.get("reason", "")).strip()
        return f"输出校验 · {reason or event_type}"
    return json.dumps(payload, ensure_ascii=False)[:120]


def format_event_time(event: dict[str, Any]) -> str:
    created_at = str(event.get("created_at", "")).strip()
    if not created_at:
        return ""
    try:
        parsed = datetime.fromisoformat(created_at)
        return parsed.strftime("%m-%d %H:%M")
    except ValueError:
        return created_at[:16]
