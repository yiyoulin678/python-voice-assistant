from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any


EVENT_TYPE_LABELS: dict[str, str] = {
    "chat_completed": "完成对话",
    "reply_parse_retry": "校验重试",
    "reply_parse_repaired": "校验修复",
    "session_summary_completed": "纪要生成",
}


@dataclass(frozen=True)
class AiMetricsChartSeries:
    daily_labels: list[str] = field(default_factory=list)
    daily_chat_counts: list[int] = field(default_factory=list)
    event_type_labels: list[str] = field(default_factory=list)
    event_type_counts: list[int] = field(default_factory=list)
    latency_labels: list[str] = field(default_factory=list)
    latency_values_ms: list[int] = field(default_factory=list)
    tool_labels: list[str] = field(default_factory=list)
    tool_counts: list[int] = field(default_factory=list)
    rag_hit_chats: int = 0
    rag_total_chats: int = 0


def parse_event_timestamp(event: dict[str, Any]) -> datetime | None:
    created_at = str(event.get("created_at", "")).strip()
    if not created_at:
        return None
    try:
        return datetime.fromisoformat(created_at)
    except ValueError:
        return None


def event_type_display_name(event_type: str) -> str:
    key = event_type.strip()
    if not key:
        return "未知"
    return EVENT_TYPE_LABELS.get(key, key)


def build_metrics_chart_series(
    events: list[dict[str, Any]],
    *,
    daily_days: int = 7,
    latency_limit: int = 20,
    tool_limit: int = 5,
) -> AiMetricsChartSeries:
    if not events:
        return AiMetricsChartSeries()

    today = date.today()
    day_keys = [today - timedelta(days=offset) for offset in range(daily_days - 1, -1, -1)]
    daily_counter: Counter[date] = Counter()
    event_counter: Counter[str] = Counter()
    latency_points: list[tuple[datetime, int]] = []
    tool_counter: Counter[str] = Counter()
    rag_hit_chats = 0
    rag_total_chats = 0

    for event in events:
        event_type = str(event.get("event_type", "")).strip()
        if event_type:
            event_counter[event_type] += 1

        payload = event.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        timestamp = parse_event_timestamp(event)
        if event_type == "chat_completed":
            if timestamp is not None:
                daily_counter[timestamp.date()] += 1
                latency = payload.get("latency_ms")
                if isinstance(latency, (int, float)) and latency >= 0:
                    latency_points.append((timestamp, int(latency)))
            rag_total_chats += 1
            rag_sources = payload.get("rag_sources") or []
            if isinstance(rag_sources, list) and rag_sources:
                rag_hit_chats += 1
            for tool in payload.get("tools") or []:
                if isinstance(tool, str) and tool.strip():
                    tool_counter[tool.strip()] += 1

    daily_labels = [day.strftime("%m-%d") for day in day_keys]
    daily_chat_counts = [daily_counter.get(day, 0) for day in day_keys]

    sorted_event_types = sorted(
        event_counter.items(),
        key=lambda item: (-item[1], item[0]),
    )
    event_type_labels = [event_type_display_name(name) for name, _ in sorted_event_types]
    event_type_counts = [count for _, count in sorted_event_types]

    latency_points.sort(key=lambda item: item[0])
    recent_latency = latency_points[-latency_limit:]
    latency_labels = [point[0].strftime("%m-%d %H:%M") for point in recent_latency]
    latency_values_ms = [point[1] for point in recent_latency]

    top_tools = tool_counter.most_common(tool_limit)
    tool_labels = [name for name, _ in top_tools]
    tool_counts = [count for _, count in top_tools]

    return AiMetricsChartSeries(
        daily_labels=daily_labels,
        daily_chat_counts=daily_chat_counts,
        event_type_labels=event_type_labels,
        event_type_counts=event_type_counts,
        latency_labels=latency_labels,
        latency_values_ms=latency_values_ms,
        tool_labels=tool_labels,
        tool_counts=tool_counts,
        rag_hit_chats=rag_hit_chats,
        rag_total_chats=rag_total_chats,
    )
