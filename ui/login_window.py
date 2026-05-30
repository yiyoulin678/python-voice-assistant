"""简易登录 / 进入界面（课设阶段：本地昵称，不接数据库）。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.chat_window import ChatWindow
from db.database import DatabaseManager

class LoginWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("语音 AI 虚拟女友 — 登录")
        self.setFixedSize(400, 280)
        self._chat: ChatWindow | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        title = QLabel("语音 AI 虚拟女友")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        sub = QLabel("基于 Python · PyQt5 · Whisper")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #666;")

        hint = QLabel("请输入昵称（课设演示，本地免密）")
        hint.setAlignment(Qt.AlignCenter)

        self.input = QLineEdit()
        self.input.setPlaceholderText("例如：小明")
        self.input.returnPressed.connect(self._on_enter)

        self.btn = QPushButton("进入聊天")
        self.btn.setMinimumHeight(40)
        self.btn.setStyleSheet(
            "QPushButton { background: #ff6b9d; color: white; border-radius: 8px; font-size: 14px; }"
            "QPushButton:hover { background: #ff5088; }"
        )
        self.btn.clicked.connect(self._on_enter)

        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addStretch()
        layout.addWidget(hint)
        layout.addWidget(self.input)
        layout.addWidget(self.btn)
        layout.addStretch()

    def _on_enter(self) -> None:
        name = self.input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入昵称。")
            return
        db = DatabaseManager()
        user_id = db.create_user_if_not_exists(name)
        self._chat = ChatWindow(
            user_id=user_id,
            username=name
        )
        self._chat.show()
        self.close()
