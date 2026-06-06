from __future__ import annotations

from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.core.debug_log import debug_log
from app.llm.context_trimming import trim_messages_for_model
from app.platforms.napcat.gateway import OneBotV11ReverseGateway
from app.platforms.napcat.log import napcat_log
from app.platforms.napcat.onebot_v11 import (
    NapCatInboundMessage,
    build_record_only_message,
    build_record_segment,
)
from app.platforms.napcat.outbound import (
    known_contact_labels,
    resolve_outbound_recipient,
)
from app.platforms.napcat.settings import NapCatSettings


class NapCatBridge(QObject):
    """把 NapCat 入站消息交给桌宠主聊天流程，并把回复发回 QQ。"""

    chat_requested = Signal(object, object)
    _inbound = Signal(object)
    connection_changed = Signal(int)

    def __init__(
        self,
        settings: NapCatSettings,
        *,
        is_busy: Callable[[], bool],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings.normalized()
        self._is_busy = is_busy
        self._histories: dict[str, deque[dict[str, str]]] = {}
        self._known_contacts: dict[str, NapCatInboundMessage] = {}
        self._active_sessions: set[str] = set()
        self._last_error: str | None = None
        self._gateway = OneBotV11ReverseGateway(
            self.settings,
            on_message=self._enqueue_inbound,
            on_connection_changed=self._handle_connection_changed,
        )
        self._inbound.connect(self._handle_inbound_on_ui_thread)

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def client_count(self) -> int:
        return self._gateway.client_count

    def start(self) -> bool:
        if not self._gateway.start():
            self._last_error = self._gateway.last_error
            return False
        self._last_error = None
        return True

    def stop(self) -> None:
        self._gateway.stop()
        napcat_log("桥接已停止")

    def release_session(self, session_id: str) -> None:
        self._active_sessions.discard(session_id)

    def known_contact_names(self) -> list[str]:
        return known_contact_labels(list(self._known_contacts.values()))

    def resolve_outbound_recipient(self, recipient: str) -> NapCatInboundMessage | None:
        return resolve_outbound_recipient(
            recipient,
            known_messages=list(self._known_contacts.values()),
        )

    def record_outbound_user_message(
        self,
        target: NapCatInboundMessage,
        text: str,
    ) -> list[dict[str, str]]:
        self._remember_contact(target)
        history = self._histories.setdefault(
            target.session_id,
            deque(maxlen=self.settings.history_limit),
        )
        history.append({"role": "user", "content": text})
        return trim_messages_for_model(list(history))

    def send_busy_reply(self, message: NapCatInboundMessage) -> None:
        self.release_session(message.session_id)
        self._gateway.send_reply(message, self.settings.busy_reply_text)

    def note_assistant_reply(self, message: NapCatInboundMessage, reply_text: str) -> None:
        text = reply_text.strip() or "……"
        self._append_assistant_history(message.session_id, text)

    def deliver_reply(
        self,
        message: NapCatInboundMessage,
        reply_text: str,
        *,
        record_paths: list[Path] | None = None,
        send_text: bool = True,
    ) -> None:
        text = reply_text.strip() or "……"
        self._append_assistant_history(message.session_id, text)
        if send_text:
            payload: str | list[dict[str, Any]]
            if record_paths:
                payload = [{"type": "text", "data": {"text": text}}]
                for record_path in record_paths:
                    payload.append(build_record_segment(record_path))
            else:
                payload = text
            self._gateway.send_reply(message, payload)
        self._active_sessions.discard(message.session_id)
        napcat_log(
            "已回复 QQ",
            {
                "session": message.session_id,
                "sender": message.sender_name,
                "text": text if send_text else "",
                "voice_count": len(record_paths or []),
                "send_text": send_text,
            },
        )
        debug_log(
            "NapCat",
            "QQ 回复已发送",
            {
                "session_id": message.session_id,
                "voice_count": len(record_paths or []),
                "send_text": send_text,
            },
        )

    def deliver_error(self, message: NapCatInboundMessage, error: str) -> None:
        self._active_sessions.discard(message.session_id)
        self._gateway.send_reply(message, f"处理失败：{error}")
        napcat_log("回复失败", {"session": message.session_id, "error": error})
        debug_log("NapCat", "QQ 消息处理失败", {"session_id": message.session_id, "error": error})

    def send_voice_record(self, message: NapCatInboundMessage, record_path: Path) -> None:
        payload = build_record_only_message(record_path)
        self._gateway.send_reply(message, payload)
        napcat_log(
            "发送 QQ 语音",
            {"session": message.session_id, "path": str(record_path)},
        )

    def _remember_contact(self, message: NapCatInboundMessage) -> None:
        self._known_contacts[message.session_id] = message

    def _append_assistant_history(self, session_id: str, text: str) -> None:
        history = self._histories.get(session_id)
        if history is not None:
            history.append({"role": "assistant", "content": text})

    def _handle_connection_changed(self, client_count: int) -> None:
        self.connection_changed.emit(client_count)

    def _enqueue_inbound(self, message: NapCatInboundMessage) -> None:
        self._inbound.emit(message)

    @Slot(object)
    def _handle_inbound_on_ui_thread(self, message: NapCatInboundMessage) -> None:
        if not isinstance(message, NapCatInboundMessage):
            return
        napcat_log(
            "收到 QQ 消息",
            {
                "type": message.message_type,
                "session": message.session_id,
                "sender": message.sender_name,
                "user_id": message.user_id,
                "group_id": message.group_id,
                "text": message.text,
            },
        )
        if message.message_type == "private" and not self.settings.allow_private:
            napcat_log("已忽略：未开启私聊", {"session": message.session_id})
            return
        if message.message_type == "group" and not self.settings.allow_group:
            napcat_log("已忽略：未开启群聊", {"session": message.session_id})
            return
        if message.session_id in self._active_sessions:
            napcat_log("忙碌回复", {"session": message.session_id, "reason": "同会话处理中"})
            self._gateway.send_reply(message, self.settings.busy_reply_text)
            return
        if self._is_busy():
            napcat_log("忙碌回复", {"session": message.session_id, "reason": "桌宠正忙"})
            self._gateway.send_reply(message, self.settings.busy_reply_text)
            return
        self._remember_contact(message)
        self._active_sessions.add(message.session_id)
        history = self._histories.setdefault(message.session_id, deque(maxlen=self.settings.history_limit))
        history.append({"role": "user", "content": message.text})
        request_messages = trim_messages_for_model(list(history))
        napcat_log("开始生成回复", {"session": message.session_id, "history_count": len(history)})
        debug_log(
            "NapCat",
            "请求桌宠生成 QQ 回复",
            {
                "session_id": message.session_id,
                "user_id": message.user_id,
                "group_id": message.group_id,
                "text": message.text,
                "history_count": len(history),
            },
        )
        self.chat_requested.emit(message, request_messages)
