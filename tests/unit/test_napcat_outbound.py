from __future__ import annotations

from app.platforms.napcat.onebot_v11 import NapCatInboundMessage
from app.platforms.napcat.outbound import (
    format_outbound_pet_display,
    parse_outbound_directive,
    resolve_outbound_recipient,
)


def _private_message(user_id: int, nickname: str) -> NapCatInboundMessage:
    return NapCatInboundMessage(
        session_id=f"private:{user_id}",
        message_type="private",
        user_id=user_id,
        group_id=None,
        text="",
        sender_name=nickname,
        self_id=None,
        raw_event={},
    )


def test_parse_outbound_directive() -> None:
    parsed = parse_outbound_directive("@小樱 晚上好")
    assert parsed is not None
    assert parsed.recipient == "小樱"
    assert parsed.text == "晚上好"
    assert parse_outbound_directive("普通消息") is None


def test_resolve_outbound_recipient_by_nickname_and_qq_id() -> None:
    known = [_private_message(10001, "小樱")]
    by_name = resolve_outbound_recipient("小樱", known_messages=known)
    by_id = resolve_outbound_recipient("10001", known_messages=known)
    assert by_name is not None
    assert by_id is not None
    assert by_name.user_id == 10001
    assert by_id.user_id == 10001


def test_resolve_outbound_recipient_builds_unknown_private_target() -> None:
    target = resolve_outbound_recipient("private:20002", known_messages=[])
    assert target is not None
    assert target.session_id == "private:20002"
    assert target.user_id == 20002


def test_format_outbound_pet_display() -> None:
    target = _private_message(1, "小明")
    assert format_outbound_pet_display(target, "我快到了") == "→小明：我快到了"
