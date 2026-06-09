from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.brand import APP_NAME
from app.ui.auth_dialog_common import (
    apply_auth_dialog_theme,
    build_auth_card,
    build_auth_field,
    build_auth_header,
)


class RegisterDialog(QDialog):
    def __init__(
        self,
        user_db,
        *,
        theme_id: str | None = None,
        parent=None,  # type: ignore[no-untyped-def]
    ) -> None:
        super().__init__(parent)
        self.user_db = user_db
        self.username: str | None = None
        self.role: str | None = None
        self.password = ""
        apply_auth_dialog_theme(self, theme_id)

        self.setWindowTitle(f"{APP_NAME} · 注册")
        self.setModal(True)
        self.setMinimumSize(440, 580)
        self.resize(460, 600)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(16)

        title_label, subtitle_label = build_auth_header(
            self,
            title="创建账号",
            subtitle="注册为普通用户，登录后即可使用桌宠与 AI 功能",
        )
        root.addWidget(title_label)
        root.addWidget(subtitle_label)

        card, card_layout = build_auth_card(self)
        username_label, self.username_edit = build_auth_field(
            card,
            label="用户名",
            placeholder="设置你的用户名",
        )
        password_label, self.password_edit = build_auth_field(
            card,
            label="密码",
            placeholder="设置登录密码",
            password=True,
        )
        confirm_label, self.confirm_edit = build_auth_field(
            card,
            label="确认密码",
            placeholder="再次输入密码",
            password=True,
        )
        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username_edit)
        card_layout.addSpacing(4)
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_edit)
        card_layout.addSpacing(4)
        card_layout.addWidget(confirm_label)
        card_layout.addWidget(self.confirm_edit)
        card_layout.addSpacing(8)

        self.register_button = QPushButton("注册并登录", card)
        self.register_button.setObjectName("authPrimaryButton")
        self.register_button.setDefault(True)
        card_layout.addWidget(self.register_button)

        self.back_button = QPushButton("返回登录", card)
        self.back_button.setObjectName("authSecondaryButton")
        card_layout.addWidget(self.back_button)
        root.addWidget(card)

        hint = QLabel("注册成功后将自动登录进入桌宠。", self)
        hint.setObjectName("authHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(hint)
        root.addStretch(1)

        self.register_button.clicked.connect(self.register)
        self.back_button.clicked.connect(self.reject)
        self.confirm_edit.returnPressed.connect(self.register)

    def register(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()

        if not username:
            QMessageBox.warning(self, "错误", "用户名不能为空。")
            self.username_edit.setFocus()
            return

        if not password:
            QMessageBox.warning(self, "错误", "密码不能为空。")
            self.password_edit.setFocus()
            return

        if password != confirm:
            QMessageBox.warning(self, "错误", "两次密码不一致。")
            self.confirm_edit.clear()
            self.confirm_edit.setFocus()
            return

        if self.user_db.user_exists(username):
            QMessageBox.warning(self, "错误", "用户名已存在，请换一个。")
            self.username_edit.setFocus()
            return

        self.user_db.create_user(username, password, "user")
        self.username = username
        self.role = "user"
        self.password = password
        QMessageBox.information(self, "注册成功", "账号已创建，正在为你登录。")
        self.accept()
