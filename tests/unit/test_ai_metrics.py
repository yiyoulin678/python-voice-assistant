from __future__ import annotations

import json
from pathlib import Path

from app.ai.metrics import AiMetricsRecorder


def test_ai_metrics_writes_jsonl(tmp_path: Path) -> None:
    recorder = AiMetricsRecorder(tmp_path)
    recorder.record("chat_completed", {"segment_count": 2, "tones": ["中性"]})

    events_path = tmp_path / "data" / "metrics" / "ai_events.jsonl"
    assert events_path.exists()
    line = events_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["event_type"] == "chat_completed"
    assert payload["payload"]["segment_count"] == 2
