from __future__ import annotations

from dataclasses import dataclass

from app.platforms.napcat.network import (
    is_loopback_host,
    is_unspecified_bind_host,
    normalize_connect_host,
    primary_local_ipv4,
)

DEFAULT_NAPCAT_BIND_HOST = "0.0.0.0"
DEFAULT_NAPCAT_HOST = DEFAULT_NAPCAT_BIND_HOST
DEFAULT_NAPCAT_PORT = 6199
DEFAULT_NAPCAT_PATH = "/ws"
DEFAULT_NAPCAT_HISTORY_LIMIT = 20

NAPCAT_REPLY_BOTH = "both"
NAPCAT_REPLY_TEXT_ONLY = "text_only"
NAPCAT_REPLY_VOICE_ONLY = "voice_only"
_SUPPORTED_NAPCAT_REPLY_MODES = {
    NAPCAT_REPLY_BOTH,
    NAPCAT_REPLY_TEXT_ONLY,
    NAPCAT_REPLY_VOICE_ONLY,
}


@dataclass(frozen=True)
class NapCatSettings:
    """NapCat / OneBot v11 反向 WebSocket 接入配置。"""

    enabled: bool = False
    host: str = DEFAULT_NAPCAT_BIND_HOST
    port: int = DEFAULT_NAPCAT_PORT
    path: str = DEFAULT_NAPCAT_PATH
    connect_host: str = ""
    token: str = ""
    allow_private: bool = True
    allow_group: bool = False
    history_limit: int = DEFAULT_NAPCAT_HISTORY_LIMIT
    busy_reply_text: str = "稍等一下，我还在回复上一条消息。"
    reply_mode: str = NAPCAT_REPLY_BOTH

    def normalized(self) -> "NapCatSettings":
        port = int(self.port)
        if port < 1 or port > 65535:
            port = DEFAULT_NAPCAT_PORT
        path = str(self.path or DEFAULT_NAPCAT_PATH).strip() or DEFAULT_NAPCAT_PATH
        if not path.startswith("/"):
            path = f"/{path}"
        history_limit = max(2, min(100, int(self.history_limit)))

        raw_host = str(self.host or "").strip()
        connect_host = str(self.connect_host or "").strip()
        if is_loopback_host(raw_host) or is_unspecified_bind_host(raw_host):
            bind_host = DEFAULT_NAPCAT_BIND_HOST
        else:
            bind_host = raw_host
        if not connect_host:
            connect_host = primary_local_ipv4() or "127.0.0.1"
        connect_host = normalize_connect_host(connect_host, port=port)

        reply_mode = str(self.reply_mode or NAPCAT_REPLY_BOTH).strip().lower()
        if reply_mode not in _SUPPORTED_NAPCAT_REPLY_MODES:
            reply_mode = NAPCAT_REPLY_BOTH

        return NapCatSettings(
            enabled=bool(self.enabled),
            host=bind_host,
            port=port,
            path=path,
            connect_host=connect_host,
            token=str(self.token or "").strip(),
            allow_private=bool(self.allow_private),
            allow_group=bool(self.allow_group),
            history_limit=history_limit,
            busy_reply_text=str(self.busy_reply_text or "").strip()
            or "稍等一下，我还在回复上一条消息。",
            reply_mode=reply_mode,
        )

    def reply_sends_text(self) -> bool:
        return self.normalized().reply_mode in {
            NAPCAT_REPLY_BOTH,
            NAPCAT_REPLY_TEXT_ONLY,
        }

    def reply_sends_voice(self) -> bool:
        return self.normalized().reply_mode in {
            NAPCAT_REPLY_BOTH,
            NAPCAT_REPLY_VOICE_ONLY,
        }

    def bind_host(self) -> str:
        return self.normalized().host

    def resolve_connect_host(self) -> str:
        return self.normalized().connect_host

    def websocket_url_hint(self) -> str:
        normalized = self.normalized()
        return f"ws://{normalized.connect_host}:{normalized.port}{normalized.path}"

    def websocket_url_hint_lines(self) -> list[str]:
        normalized = self.normalized()
        lines = [normalized.websocket_url_hint()]
        loopback = f"ws://127.0.0.1:{normalized.port}{normalized.path}"
        if loopback not in lines:
            lines.append(loopback)
        return lines
