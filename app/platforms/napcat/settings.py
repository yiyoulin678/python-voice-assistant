from __future__ import annotations

from dataclasses import dataclass


DEFAULT_NAPCAT_HOST = "127.0.0.1"
DEFAULT_NAPCAT_PORT = 6199
DEFAULT_NAPCAT_PATH = "/ws"
DEFAULT_NAPCAT_HISTORY_LIMIT = 20


@dataclass(frozen=True)
class NapCatSettings:
    """NapCat / OneBot v11 反向 WebSocket 接入配置。"""

    enabled: bool = False
    host: str = DEFAULT_NAPCAT_HOST
    port: int = DEFAULT_NAPCAT_PORT
    path: str = DEFAULT_NAPCAT_PATH
    token: str = ""
    allow_private: bool = True
    allow_group: bool = False
    history_limit: int = DEFAULT_NAPCAT_HISTORY_LIMIT
    busy_reply_text: str = "稍等一下，我还在回复上一条消息。"

    def normalized(self) -> "NapCatSettings":
        port = int(self.port)
        if port < 1 or port > 65535:
            port = DEFAULT_NAPCAT_PORT
        path = str(self.path or DEFAULT_NAPCAT_PATH).strip() or DEFAULT_NAPCAT_PATH
        if not path.startswith("/"):
            path = f"/{path}"
        history_limit = max(2, min(100, int(self.history_limit)))
        return NapCatSettings(
            enabled=bool(self.enabled),
            host=str(self.host or DEFAULT_NAPCAT_HOST).strip() or DEFAULT_NAPCAT_HOST,
            port=port,
            path=path,
            token=str(self.token or "").strip(),
            allow_private=bool(self.allow_private),
            allow_group=bool(self.allow_group),
            history_limit=history_limit,
            busy_reply_text=str(self.busy_reply_text or "").strip()
            or "稍等一下，我还在回复上一条消息。",
        )

    def websocket_url_hint(self) -> str:
        normalized = self.normalized()
        return f"ws://{normalized.host}:{normalized.port}{normalized.path}"
