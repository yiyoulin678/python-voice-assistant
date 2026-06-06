from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.agent import AgentResult, AgentRuntime
from app.core.chat_pipeline import ChatPipeline
from app.core.chat_worker import ChatWorker
from app.core.debug_log import debug_log
from app.llm.context_trimming import trim_messages_for_model
from app.platforms.napcat.gateway import OneBotV11ReverseGateway
from app.platforms.napcat.onebot_v11 import NapCatInboundMessage, format_agent_reply_text
from app.platforms.napcat.settings import NapCatSettings


class NapCatBridge(QObject):
    """把 NapCat 入站消息接到 AgentRuntime，并把回复发回 QQ。"""

    _inbound = Signal(object)

    def __init__(
        self,
        settings: NapCatSettings,
        *,
        agent_runtime: AgentRuntime,
        is_busy: Callable[[], bool],
        prefer_translation: Callable[[], bool] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings.normalized()
        self.agent_runtime = agent_runtime
        self._is_busy = is_busy
        self._prefer_translation = prefer_translation or (lambda: True)
        self._histories: dict[str, deque[dict[str, str]]] = {}
        self._active_sessions: set[str] = set()
        self._gateway = OneBotV11ReverseGateway(
            self.settings,
            on_message=self._enqueue_inbound,
        )
        self._inbound.connect(self._handle_inbound_on_ui_thread)

    def start(self) -> None:
        self._gateway.start()
        debug_log(
            "NapCat",
            "桥接已启动",
            {
                "url": self.settings.websocket_url_hint(),
                "allow_private": self.settings.allow_private,
                "allow_group": self.settings.allow_group,
            },
        )

    def stop(self) -> None:
        self._gateway.stop()
        debug_log("NapCat", "桥接已停止", {})

    def _enqueue_inbound(self, message: NapCatInboundMessage) -> None:
        self._inbound.emit(message)

    @Slot(object)
    def _handle_inbound_on_ui_thread(self, message: NapCatInboundMessage) -> None:
        if not isinstance(message, NapCatInboundMessage):
            return
        if message.message_type == "private" and not self.settings.allow_private:
            return
        if message.message_type == "group" and not self.settings.allow_group:
            return
        if message.session_id in self._active_sessions:
            self._gateway.send_reply(message, self.settings.busy_reply_text)
            return
        if self._is_busy():
            self._gateway.send_reply(message, self.settings.busy_reply_text)
            return
        self._active_sessions.add(message.session_id)
        history = self._histories.setdefault(message.session_id, deque(maxlen=self.settings.history_limit))
        history.append({"role": "user", "content": message.text})
        request_messages = trim_messages_for_model(list(history))
        debug_log(
            "NapCat",
            "开始处理 QQ 消息",
            {
                "session_id": message.session_id,
                "user_id": message.user_id,
                "group_id": message.group_id,
                "text": message.text,
                "history_count": len(history),
            },
        )
        worker_thread = QThread(self)
        worker = ChatWorker(self.agent_runtime, request_messages)
        worker.moveToThread(worker_thread)
        worker_thread.started.connect(worker.run)

        def _finish(result: AgentResult) -> None:
            reply_text = format_agent_reply_text(
                result.reply.segments,
                prefer_translation=self._prefer_translation(),
            )
            if not reply_text:
                reply_text = "……"
            history.append({"role": "assistant", "content": reply_text})
            self._gateway.send_reply(message, reply_text)
            self._active_sessions.discard(message.session_id)
            debug_log(
                "NapCat",
                "QQ 回复已发送",
                {"session_id": message.session_id, "segments": len(result.reply.segments)},
            )

        def _fail(error: str) -> None:
            self._active_sessions.discard(message.session_id)
            self._gateway.send_reply(message, f"处理失败：{error}")
            debug_log("NapCat", "QQ 消息处理失败", {"session_id": message.session_id, "error": error})

        worker.finished.connect(_finish)
        worker.failed.connect(_fail)
        worker.finished.connect(worker_thread.quit)
        worker.failed.connect(worker_thread.quit)
        worker_thread.finished.connect(worker.deleteLater)
        worker_thread.finished.connect(worker_thread.deleteLater)
        worker_thread.start()
