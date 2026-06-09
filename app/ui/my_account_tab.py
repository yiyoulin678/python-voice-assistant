from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFormLayout,
    QGroupBox,
)

from app.auth.user_db import UserDB
from app.auth.session import UserSession, role_display_name, user_database_path


class MyAccountTab(QWidget):
    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.user_db = UserDB(user_database_path(base_dir))

        main_layout = QVBoxLayout(self)

        profile_group = QGroupBox("账户信息")
        profile_form = QFormLayout()
        username = UserSession.username.strip() or "—"
        user_id = "—" if UserSession.user_id is None else str(UserSession.user_id)
        profile_form.addRow("用户名", QLabel(username))
        profile_form.addRow("用户 ID", QLabel(user_id))
        profile_form.addRow("当前角色", QLabel(role_display_name(UserSession.role)))
        profile_group.setLayout(profile_form)
        main_layout.addWidget(profile_group)

        if UserSession.role.lower() != "admin":
            hint = QLabel(
                "管理员后台需使用管理员账号登录。"
                "首次安装默认账号：admin / admin123；"
                "登录后在设置页会出现「用户管理」「任务管理」「管理后台」。"
            )
            hint.setWordWrap(True)
            main_layout.addWidget(hint)

        password_group = QGroupBox("修改密码")
        password_layout = QVBoxLayout()
        self.old_password = QLineEdit()
        self.old_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        password_form = QFormLayout()
        password_form.addRow("旧密码", self.old_password)
        password_form.addRow("新密码", self.new_password)
        password_form.addRow("确认新密码", self.confirm_password)
        password_layout.addLayout(password_form)
        self.change_button = QPushButton("修改密码")
        self.change_button.clicked.connect(self.change_password)
        password_layout.addWidget(self.change_button)
        password_group.setLayout(password_layout)
        main_layout.addWidget(password_group)
        main_layout.addStretch(1)

    def change_password(self) -> None:
        old_password = self.old_password.text()
        new_password = self.new_password.text()
        confirm_password = self.confirm_password.text()

        if not UserSession.username.strip():
            QMessageBox.warning(self, "错误", "当前未登录，无法修改密码。")
            return

        if not old_password:
            QMessageBox.warning(self, "错误", "请输入旧密码")
            return

        if not new_password:
            QMessageBox.warning(self, "错误", "请输入新密码")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "错误", "两次密码不一致")
            return

        success = self.user_db.change_password(
            UserSession.username,
            old_password,
            new_password,
        )

        if not success:
            QMessageBox.warning(self, "失败", "旧密码错误")
            return

        QMessageBox.information(self, "成功", "密码修改成功")
        self.old_password.clear()
        self.new_password.clear()
        self.confirm_password.clear()
