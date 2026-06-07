from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ai.metrics import AiMetricsRecorder
from app.llm.chat_reply import ChatReply, ChatReplyParseResult, parse_chat_reply_result

_metrics: AiMetricsRecorder | None = None


def configure_reply_metrics(recorder: AiMetricsRecorder | None) -> None:
    global _metrics
    _metrics = recorder


@dataclass(frozen=True)
class ValidatedChatReply:
    reply: ChatReply
    ok: bool
    needs_retry: bool
    reason: str
    repaired: bool
    raw_content: str

    @property
    def parse_result(self) -> ChatReplyParseResult:
        return ChatReplyParseResult(
            self.reply,
            ok=self.ok,
            needs_retry=self.needs_retry,
            reason=self.reason,
            repaired=self.repaired,
        )


def validate_chat_reply(
    content: str,
    *,
    strict_correspondence: bool = False,
    source: str = "api_chat",
) -> ValidatedChatReply:
    """解析并校验模型回复，必要时记录修复事件。"""
    parsed = parse_chat_reply_result(content, strict_correspondence=strict_correspondence)
    _record_validation_event(
        source=source,
        content=content,
        reason=parsed.reason,
        needs_retry=parsed.needs_retry,
        repaired=parsed.repaired,
        ok=parsed.ok,
        segment_count=len(parsed.reply.segments),
    )
    return ValidatedChatReply(
        reply=parsed.reply,
        ok=parsed.ok,
        needs_retry=parsed.needs_retry,
        reason=parsed.reason,
        repaired=parsed.repaired,
        raw_content=content,
    )


def _record_validation_event(
    *,
    source: str,
    content: str,
    reason: str,
    needs_retry: bool,
    repaired: bool,
    ok: bool,
    segment_count: int,
) -> None:
    if _metrics is None:
        return
    if not needs_retry and not repaired and ok:
        return
    payload: dict[str, Any] = {
        "source": source,
        "reason": reason,
        "needs_retry": needs_retry,
        "repaired": repaired,
        "ok": ok,
        "segment_count": segment_count,
        "content_preview": content[:240],
    }
    event_type = "reply_parse_retry" if needs_retry else "reply_parse_repaired"
    _metrics.record(event_type, payload)
