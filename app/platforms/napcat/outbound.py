from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.platforms.napcat.onebot_v11 import NapCatInboundMessage

_OUTBOUND_DIRECTIVE_RE = re.compile(r"^@([^\s]+)\s+(.+)$", re.DOTALL)


@dataclass(frozen=True)
class NapCatOutboundDirective:
    recipient: str
    text: str


def parse_outbound_directive(text: str) -> NapCatOutboundDirective | None:
    match = _OUTBOUND_DIRECTIVE_RE.match(text.strip())
    if match is None:
        return None
    recipient = match.group(1).strip()
    body = match.group(2).strip()
    if not recipient or not body:
        return None
    return NapCatOutboundDirective(recipient=recipient, text=body)


def build_private_target(
    user_id: int,
    *,
    sender_name: str | None = None,
    self_id: int | None = None,
) -> NapCatInboundMessage:
    display_name = (sender_name or str(user_id)).strip() or str(user_id)
    return NapCatInboundMessage(
        session_id=f"private:{user_id}",
        message_type="private",
        user_id=user_id,
        group_id=None,
        text="",
        sender_name=display_name,
        self_id=self_id,
        raw_event={},
    )


def build_group_target(
    group_id: int,
    *,
    sender_name: str | None = None,
    self_id: int | None = None,
) -> NapCatInboundMessage:
    display_name = (sender_name or f"群{group_id}").strip() or str(group_id)
    return NapCatInboundMessage(
        session_id=f"group:{group_id}",
        message_type="group",
        user_id=0,
        group_id=group_id,
        text="",
        sender_name=display_name,
        self_id=self_id,
        raw_event={},
    )


def resolve_outbound_recipient(
    recipient: str,
    *,
    known_messages: list[NapCatInboundMessage],
) -> NapCatInboundMessage | None:
    token = recipient.strip()
    if not token:
        return None

    lowered = token.lower()
    if lowered.startswith("private:"):
        try:
            user_id = int(token.split(":", 1)[1])
        except (TypeError, ValueError):
            return None
        return _match_private_target(user_id, known_messages)

    if lowered.startswith("group:"):
        try:
            group_id = int(token.split(":", 1)[1])
        except (TypeError, ValueError):
            return None
        return _match_group_target(group_id, known_messages)

    if token.isdigit():
        user_id = int(token)
        return _match_private_target(user_id, known_messages)

    for message in known_messages:
        if message.sender_name.casefold() == token.casefold():
            return message
    return None


def _match_private_target(
    user_id: int,
    known_messages: list[NapCatInboundMessage],
) -> NapCatInboundMessage:
    for message in known_messages:
        if message.message_type == "private" and message.user_id == user_id:
            return message
    return build_private_target(user_id)


def _match_group_target(
    group_id: int,
    known_messages: list[NapCatInboundMessage],
) -> NapCatInboundMessage:
    for message in known_messages:
        if message.message_type == "group" and message.group_id == group_id:
            return message
    return build_group_target(group_id)


def format_outbound_pet_display(target: NapCatInboundMessage, text: str) -> str:
    return f"→{target.sender_name}：{text}"


def known_contact_labels(known_messages: list[NapCatInboundMessage]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for message in known_messages:
        label = message.sender_name.strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels
