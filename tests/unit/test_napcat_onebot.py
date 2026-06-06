from __future__ import annotations

from pathlib import Path

from app.platforms.napcat.onebot_v11 import (
    build_record_only_message,
    build_record_segment,
    build_send_action,
    extract_message_text,
    format_agent_reply_text,
    parse_message_event,
)
from app.platforms.napcat.gateway import OneBotV11ReverseGateway
from app.platforms.napcat.settings import NapCatSettings


def test_extract_message_text_from_string_and_segments() -> None:
    assert extract_message_text("你好") == "你好"
    assert (
        extract_message_text(
            [
                {"type": "text", "data": {"text": "你好"}},
                {"type": "image", "data": {"url": "https://example.com/a.png"}},
                {"type": "text", "data": {"text": "安安"}},
            ]
        )
        == "你好 安安"
    )


def test_parse_private_message_event() -> None:
    message = parse_message_event(
        {
            "post_type": "message",
            "message_type": "private",
            "user_id": 10001,
            "self_id": 20002,
            "message": [{"type": "text", "data": {"text": "在吗"}}],
        }
    )
    assert message is not None
    assert message.session_id == "private:10001"
    assert message.text == "在吗"


def test_build_record_segment_uses_stable_local_path() -> None:
    path = Path("C:/tmp/voice.wav")
    segment = build_record_segment(path)
    assert segment["type"] == "record"
    assert segment["data"]["file"] == "C:/tmp/voice.wav"
    assert build_record_only_message(path) == [segment]


def test_build_send_action_for_group_and_private() -> None:
    private = parse_message_event(
        {
            "post_type": "message",
            "message_type": "private",
            "user_id": 1,
            "message": "hi",
        }
    )
    group = parse_message_event(
        {
            "post_type": "message",
            "message_type": "group",
            "user_id": 1,
            "group_id": 99,
            "message": "hi",
        }
    )
    assert private is not None
    assert group is not None
    assert build_send_action(private, "reply")["action"] == "send_private_msg"
    assert build_send_action(group, "reply")["action"] == "send_group_msg"


def test_format_agent_reply_text_prefers_translation() -> None:
    class Segment:
        def __init__(self, text: str, translation: str) -> None:
            self.text = text
            self.translation = translation

    text = format_agent_reply_text(
        [Segment("こんにちは", "你好")],
        prefer_translation=True,
    )
    assert text == "你好"


def test_gateway_request_path_accepts_str_and_bytes() -> None:
    gateway = OneBotV11ReverseGateway(
        NapCatSettings(),
        on_message=lambda _message: None,
    )

    class StrRequest:
        path = "/ws"

    class BytesRequest:
        path = b"/ws?access_token=abc"

    assert gateway._request_path(StrRequest()) == "/ws"
    assert gateway._request_path(BytesRequest()) == "/ws?access_token=abc"
    assert gateway._path_allowed("/ws")
    assert gateway._path_allowed("/")


def test_napcat_settings_rejects_virtual_adapter_connect_host() -> None:
    settings = NapCatSettings(
        enabled=True,
        port=6199,
        connect_host="172.23.144.1",
    ).normalized()
    assert settings.resolve_connect_host() != "172.23.144.1"
    assert settings.websocket_url_hint().startswith("ws://")


def test_napcat_settings_websocket_url_hint() -> None:
    settings = NapCatSettings(
        enabled=True,
        port=6199,
        connect_host="10.21.220.187",
    ).normalized()
    assert settings.websocket_url_hint() == "ws://10.21.220.187:6199/ws"
    assert settings.bind_host() == "0.0.0.0"
