from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.platforms.napcat.event_log import NapCatEventLog, NapCatLogEntry, napcat_event_log


class NapCatConsoleWindow(QDialog):
    """NapCat / QQ 接入控制台：查看连接状态与消息收发日志。"""

    def __init__(
        self,
        *,
        client_count_provider: Callable[[], int] | None = None,
        bridge_running_provider: Callable[[], bool] | None = None,
        parent=None,  # type: ignore[no-untyped-def]
    ) -> None:
        super().__init__(parent)
        self._client_count_provider = client_count_provider or (lambda: 0)
        self._bridge_running_provider = bridge_running_provider or (lambda: False)
        self._event_log = napcat_event_log()

        self.setWindowTitle("QQ 控制台")
        self.resize(720, 480)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_view.setFont(QFont("Consolas", 10))

        clear_button = QPushButton("清空日志", self)
        clear_button.clicked.connect(self._clear_logs)
        refresh_button = QPushButton("刷新状态", self)
        refresh_button.clicked.connect(self.refresh_connection_status)

        button_row = QHBoxLayout()
        button_row.addWidget(refresh_button)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_view, 1)
        layout.addLayout(button_row)

        self._event_log.entry_added.connect(self._append_entry)
        self._event_log.cleared.connect(self._reload_logs)
        self._reload_logs()
        self.refresh_connection_status()

    def refresh_connection_status(self) -> None:
        running = self._bridge_running_provider()
        clients = self._client_count_provider()
        if not running:
            status = "QQ 接入：未启用或未启动"
        elif clients > 0:
            status = f"QQ 接入：已连接（{clients} 个 NapCat 客户端）"
        else:
            status = "QQ 接入：已启动，等待 NapCat 连接…"
        self.status_label.setText(
            f"{status}\n"
            "收到私聊/群聊、发送回复、连接变化都会显示在下方日志中。"
        )

    def _append_entry(self, entry: NapCatLogEntry) -> None:
        if not isinstance(entry, NapCatLogEntry):
            return
        self.log_view.append(entry.format_line())
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _reload_logs(self) -> None:
        lines = [entry.format_line() for entry in self._event_log.entries()]
        self.log_view.setPlainText("\n".join(lines))
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear_logs(self) -> None:
        self._event_log.clear()
