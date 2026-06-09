from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.auth.session import UserSession
from app.brand import APP_NAME
from app.ui.auth_dialog_common import (
    apply_auth_dialog_theme,
    build_auth_card,
    build_auth_field,
    build_auth_header,
    resolve_auth_ui_theme,
)
from app.ui.register_dialog import RegisterDialog


class LoginDialog(QDialog):
    def __init__(
        self,
        user_db,
        *,
        base_dir: Path | None = None,
        parent=None,  # type: ignore[no-untyped-def]
    ) -> None:
        super().__init__(parent)
        self.user_db = user_db
        self.role: str | None = None
        self.username: str | None = None
        self._theme_id = apply_auth_dialog_theme(
            self,
            resolve_auth_ui_theme(base_dir),
        )

        self.setWindowTitle(f"{APP_NAME} · 登录")
        self.setModal(True)
        self.setMinimumSize(440, 520)
        self.resize(460, 540)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(16)

        title_label, subtitle_label = build_auth_header(
            self,
            title=APP_NAME,
            subtitle="桌面桌宠 · 登录后继续与角色互动",
        )
        root.addWidget(title_label)
        root.addWidget(subtitle_label)

        card, card_layout = build_auth_card(self)
        self.username_label, self.username_edit = build_auth_field(
            card,
            label="用户名",
            placeholder="请输入用户名",
        )
        self.password_label, self.password_edit = build_auth_field(
            card,
            label="密码",
            placeholder="请输入密码",
            password=True,
        )
        card_layout.addWidget(self.username_label)
        card_layout.addWidget(self.username_edit)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.password_label)
        card_layout.addWidget(self.password_edit)
        card_layout.addSpacing(8)

        self.login_button = QPushButton("登录", card)
        self.login_button.setObjectName("authPrimaryButton")
        self.login_button.setDefault(True)
        self.login_button.setAutoDefault(True)
        card_layout.addWidget(self.login_button)

        self.register_button = QPushButton("还没有账号？注册", card)
        self.register_button.setObjectName("authSecondaryButton")
        card_layout.addWidget(self.register_button)
        root.addWidget(card)

        hint = QLabel("首次安装可使用管理员账号 admin 登录。", self)
        hint.setObjectName("authHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hint.setWordWrap(True)
        root.addWidget(hint)
        root.addStretch(1)

        self.login_button.clicked.connect(self.login)
        self.register_button.clicked.connect(self.open_register_dialog)
        self.password_edit.returnPressed.connect(self.login)
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)

    def login(self) -> None:
        username = self.username_edit.text().strip()
        if not username:
            QMessageBox.warning(self, "提示", "请输入用户名。")
            self.username_edit.setFocus()
            return

        result = self.user_db.verify_user(username, self.password_edit.text())
        if result is None:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误。")
            self.password_edit.clear()
            self.password_edit.setFocus()
            return

        user_id, role = result
        self.username = username
        self.role = role
        UserSession.user_id = user_id
        UserSession.username = username
        UserSession.role = role
        self.accept()

    def open_register_dialog(self) -> None:
        dialog = RegisterDialog(
            self.user_db,
            theme_id=self._theme_id,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.username = dialog.username
        self.role = dialog.role
        result = self.user_db.verify_user(self.username, dialog.password)
        if result is not None:
            user_id, role = result
            UserSession.user_id = user_id
            UserSession.username = self.username
            UserSession.role = role
        else:
            UserSession.user_id = None
            UserSession.username = self.username
            UserSession.role = self.role
        self.accept()
