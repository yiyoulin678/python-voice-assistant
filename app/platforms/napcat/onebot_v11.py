from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NapCatInboundMessage:
    """从 OneBot v11 消息事件中提取的入站文本。"""

    session_id: str
    message_type: str
    user_id: int
    group_id: int | None
    text: str
    self_id: int | None
    raw_event: dict[str, Any]


def extract_message_text(message: Any) -> str:
    if isinstance(message, str):
        return message.strip()
    if not isinstance(message, list):
        return ""
    parts: list[str] = []
    for segment in message:
        if not isinstance(segment, dict):
            continue
        if str(segment.get("type", "")).lower() != "text":
            continue
        data = segment.get("data")
        if isinstance(data, dict):
            text = str(data.get("text", "")).strip()
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def parse_message_event(payload: dict[str, Any]) -> NapCatInboundMessage | None:
    if str(payload.get("post_type", "")).lower() != "message":
        return None
    message_type = str(payload.get("message_type", "")).lower()
    if message_type not in {"private", "group"}:
        return None
    try:
        user_id = int(payload.get("user_id"))
    except (TypeError, ValueError):
        return None
    group_id: int | None
    try:
        group_id = int(payload["group_id"]) if message_type == "group" else None
    except (TypeError, ValueError, KeyError):
        group_id = None
    text = extract_message_text(payload.get("message"))
    if not text:
        text = str(payload.get("raw_message", "")).strip()
    if not text:
        return None
    self_id: int | None
    try:
        self_id = int(payload.get("self_id"))
    except (TypeError, ValueError):
        self_id = None
    session_id = (
        f"group:{group_id}"
        if message_type == "group" and group_id is not None
        else f"private:{user_id}"
    )
    return NapCatInboundMessage(
        session_id=session_id,
        message_type=message_type,
        user_id=user_id,
        group_id=group_id,
        text=text,
        self_id=self_id,
        raw_event=payload,
    )


def build_record_segment(record_path: Path) -> dict[str, Any]:
    resolved = record_path.resolve()
    file_value = resolved.as_uri()
    if resolved.drive:
        # NapCat/QQ 在 Windows 上更稳定地接受正斜杠绝对路径。
        file_value = resolved.as_posix()
    return {
        "type": "record",
        "data": {"file": file_value},
    }


def build_record_only_message(record_path: Path) -> list[dict[str, Any]]:
    return [build_record_segment(record_path)]


def build_send_action(
    message: NapCatInboundMessage,
    reply_payload: str | list[dict[str, Any]],
) -> dict[str, Any]:
    if message.message_type == "group" and message.group_id is not None:
        return {
            "action": "send_group_msg",
            "params": {
                "group_id": message.group_id,
                "message": reply_payload,
            },
        }
    return {
        "action": "send_private_msg",
        "params": {
            "user_id": message.user_id,
            "message": reply_payload,
        },
    }


def dumps_api_call(action: dict[str, Any], *, echo: str) -> str:
    payload = dict(action)
    payload["echo"] = echo
    return json.dumps(payload, ensure_ascii=False)


def format_agent_reply_text(
    segments: list[Any],
    *,
    prefer_translation: bool = True,
) -> str:
    parts: list[str] = []
    for segment in segments:
        translation = str(getattr(segment, "translation", "") or "").strip()
        text = str(getattr(segment, "text", "") or "").strip()
        if prefer_translation and translation:
            parts.append(translation)
        elif text:
            parts.append(text)
        elif translation:
            parts.append(translation)
    return "\n".join(parts).strip()
