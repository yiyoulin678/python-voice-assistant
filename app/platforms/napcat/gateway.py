from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections.abc import Callable
from typing import Any

from app.core.debug_log import debug_log
from app.platforms.napcat.onebot_v11 import (
    NapCatInboundMessage,
    build_send_action,
    dumps_api_call,
    parse_message_event,
)
from app.platforms.napcat.settings import NapCatSettings


EventCallback = Callable[[NapCatInboundMessage], None]


class OneBotV11ReverseGateway:
    """OneBot v11 反向 WebSocket 服务端，供 NapCat 作为客户端连入。"""

    def __init__(
        self,
        settings: NapCatSettings,
        *,
        on_message: EventCallback,
    ) -> None:
        self.settings = settings.normalized()
        self._on_message = on_message
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._clients: set[Any] = set()
        self._server: Any = None
        self._started = threading.Event()
        self._start_error: str | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._started.clear()
        self._start_error = None
        self._thread = threading.Thread(target=self._run_loop, name="napcat-gateway", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout=5.0):
            raise RuntimeError("NapCat 反向 WebSocket 启动超时。")
        if self._start_error:
            raise RuntimeError(self._start_error)

    def stop(self) -> None:
        loop = self._loop
        if loop is not None:
            loop.call_soon_threadsafe(loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._thread = None
        self._loop = None
        self._server = None
        self._clients.clear()

    def send_reply(self, message: NapCatInboundMessage, reply_text: str) -> None:
        text = reply_text.strip()
        if not text:
            return
        loop = self._loop
        if loop is None:
            return
        action = build_send_action(message, text)
        asyncio.run_coroutine_threadsafe(self._broadcast_api(action), loop)

    def _run_loop(self) -> None:
        try:
            import websockets
        except ImportError as exc:
            self._start_error = (
                "缺少 websockets 依赖，请先执行：runtime\\python.exe -m pip install websockets"
            )
            self._started.set()
            debug_log("NapCat", "启动失败", {"error": self._start_error, "import_error": str(exc)})
            return

        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._serve(websockets))
        except Exception as exc:  # noqa: BLE001
            self._start_error = str(exc)
            debug_log("NapCat", "网关循环异常退出", {"error": str(exc)})
        finally:
            loop.close()
            self._loop = None

    async def _serve(self, websockets_module: Any) -> None:
        settings = self.settings
        try:
            self._server = await websockets_module.serve(
                self._handle_connection,
                settings.host,
                settings.port,
                process_request=self._authorize_connection,
            )
        except OSError as exc:
            self._start_error = f"无法监听 {settings.host}:{settings.port}：{exc}"
            self._started.set()
            debug_log("NapCat", "监听失败", {"error": self._start_error})
            return

        debug_log(
            "NapCat",
            "反向 WebSocket 已启动",
            {
                "host": settings.host,
                "port": settings.port,
                "path": settings.path,
                "url": settings.websocket_url_hint(),
            },
        )
        self._started.set()
        try:
            await asyncio.Future()
        finally:
            self._server.close()
            await self._server.wait_closed()

    def _authorize_connection(
        self,
        connection: Any,
        request: Any,
    ) -> Any | tuple[int, list[tuple[bytes, bytes]], bytes]:
        settings = self.settings
        raw_path = request.path.decode("utf-8", errors="replace")
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(raw_path if "://" in raw_path else f"http://local{raw_path}")
        if parsed.path != settings.path:
            return connection.respond(404, "Not Found")
        if settings.token:
            auth_header = request.headers.get("Authorization", "")
            bearer = f"Bearer {settings.token}"
            query_token = parse_qs(parsed.query).get("access_token", [""])[0]
            if auth_header != bearer and query_token != settings.token:
                return connection.respond(403, "Forbidden")
        return None

    async def _handle_connection(self, websocket: Any) -> None:
        self._clients.add(websocket)
        debug_log(
            "NapCat",
            "OneBot 客户端已连接",
            {"remote": str(getattr(websocket, "remote_address", ""))},
        )
        try:
            async for raw in websocket:
                self._dispatch_payload(raw)
        except Exception as exc:  # noqa: BLE001
            debug_log("NapCat", "连接处理异常", {"error": str(exc)})
        finally:
            self._clients.discard(websocket)
            debug_log("NapCat", "OneBot 客户端已断开", {})

    def _dispatch_payload(self, raw: str | bytes) -> None:
        try:
            if isinstance(raw, bytes):
                text = raw.decode("utf-8")
            else:
                text = raw
            payload = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            debug_log("NapCat", "忽略无法解析的 WebSocket 消息", {"error": str(exc)})
            return
        if not isinstance(payload, dict):
            return
        post_type = str(payload.get("post_type", "")).lower()
        if post_type == "meta_event":
            debug_log("NapCat", "收到 meta_event", {"meta_event_type": payload.get("meta_event_type")})
            return
        message = parse_message_event(payload)
        if message is None:
            return
        if message.self_id is not None and message.user_id == message.self_id:
            return
        try:
            self._on_message(message)
        except Exception as exc:  # noqa: BLE001
            debug_log("NapCat", "处理入站消息失败", {"error": str(exc), "session_id": message.session_id})

    async def _broadcast_api(self, action: dict[str, Any]) -> None:
        if not self._clients:
            debug_log("NapCat", "没有已连接的 OneBot 客户端，无法发送回复", {"action": action.get("action")})
            return
        payload = dumps_api_call(action, echo=str(uuid.uuid4()))
        for client in list(self._clients):
            try:
                await client.send(payload)
            except Exception as exc:  # noqa: BLE001
                debug_log("NapCat", "发送 API 调用失败", {"error": str(exc)})
