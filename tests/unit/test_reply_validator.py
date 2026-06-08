from __future__ import annotations

from pathlib import Path

from app.ai.metrics import AiMetricsRecorder
from app.llm.reply_validator import configure_reply_metrics, validate_chat_reply


def test_validate_chat_reply_records_parse_retry(tmp_path: Path) -> None:
    configure_reply_metrics(AiMetricsRecorder(tmp_path))
    validated = validate_chat_reply("", source="test")
    assert validated.needs_retry is True
    assert validated.reason == "empty"

    events_path = tmp_path / "data" / "metrics" / "ai_events.jsonl"
    assert events_path.exists()


def test_validate_chat_reply_accepts_valid_json() -> None:
    configure_reply_metrics(None)
    validated = validate_chat_reply(
        '{"segments":[{"ja":"こんにちは","zh":"你好","tone":"中性","portrait":"站立待机"}]}',
        source="test",
    )
    assert validated.ok is True
    assert validated.reply.text == "こんにちは"
