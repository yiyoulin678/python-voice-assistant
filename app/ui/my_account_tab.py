from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox
)

from app.auth.user_db import UserDB
from app.auth.session import UserSession


class MyAccountTab(QWidget):

    def __init__(self):
        super().__init__()

        self.user_db = UserDB(
            Path("users.db")
        )

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel("当前账号：")
        )

        self.username_label = QLabel(
            UserSession.username
        )

        layout.addWidget(
            self.username_label
        )

        layout.addWidget(
            QLabel("当前角色：")
        )

        self.role_label = QLabel(
            UserSession.role
        )

        layout.addWidget(
            self.role_label
        )

        layout.addWidget(
            QLabel("旧密码：")
        )

        self.old_password = QLineEdit()

        self.old_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        layout.addWidget(
            self.old_password
        )

        layout.addWidget(
            QLabel("新密码：")
        )

        self.new_password = QLineEdit()

        self.new_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        layout.addWidget(
            self.new_password
        )

        layout.addWidget(
            QLabel("确认新密码：")
        )

        self.confirm_password = QLineEdit()

        self.confirm_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        layout.addWidget(
            self.confirm_password
        )

        self.change_button = QPushButton(
            "修改密码"
        )

        layout.addWidget(
            self.change_button
        )

        self.change_button.clicked.connect(
            self.change_password
        )

    def change_password(self):

        old_password = (
            self.old_password.text()
        )

        new_password = (
            self.new_password.text()
        )

        confirm_password = (
            self.confirm_password.text()
        )

        if not old_password:

            QMessageBox.warning(
                self,
                "错误",
                "请输入旧密码"
            )

            return

        if not new_password:

            QMessageBox.warning(
                self,
                "错误",
                "请输入新密码"
            )

            return

        if new_password != confirm_password:

            QMessageBox.warning(
                self,
                "错误",
                "两次密码不一致"
            )

            return

        success = self.user_db.change_password(
            UserSession.username,
            old_password,
            new_password
        )

        if not success:

            QMessageBox.warning(
                self,
                "失败",
                "旧密码错误"
            )

            return

        QMessageBox.information(
            self,
            "成功",
            "密码修改成功"
        )

        self.old_password.clear()
        self.new_password.clear()
        self.confirm_password.clear()