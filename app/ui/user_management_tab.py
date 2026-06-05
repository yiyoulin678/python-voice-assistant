from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QInputDialog
)

from app.auth.user_db import UserDB


class UserManagementTab(QWidget):

    def __init__(self):
        super().__init__()

        self.user_db = UserDB(
            Path("users.db")
        )

        layout = QVBoxLayout(self)

        title = QLabel("用户管理（管理员专用）")

        layout.addWidget(title)

        self.table = QTableWidget()

        self.table.setColumnCount(3)

        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "用户名",
                "角色"
            ]
        )

        layout.addWidget(self.table)

        self.refresh_button = QPushButton("刷新")
        self.delete_button = QPushButton("删除用户")
        self.reset_button = QPushButton("重置密码")
        
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.delete_button)
        layout.addWidget(self.reset_button)
        self.username_edit = QLineEdit()

        self.password_edit = QLineEdit()

        self.role_combo = QComboBox()

        self.role_combo.addItems(
            [
                "user",
                "admin"
            ]
        )

        self.create_button = QPushButton(
            "创建用户"
        )

        layout.addWidget(QLabel("用户名"))
        layout.addWidget(self.username_edit)

        layout.addWidget(QLabel("密码"))
        layout.addWidget(self.password_edit)

        layout.addWidget(QLabel("角色"))
        layout.addWidget(self.role_combo)

        layout.addWidget(self.create_button)
        self.refresh_button.clicked.connect(
            self.load_users
        )
        self.delete_button.clicked.connect(
            self.delete_selected_user
        )
        self.create_button.clicked.connect(
            self.create_user
        )
        self.reset_button.clicked.connect(
            self.reset_password
        )

        self.load_users()

    def create_user(self):

        username = self.username_edit.text().strip()

        password = self.password_edit.text()

        role = self.role_combo.currentText()

        if not username:

            QMessageBox.warning(
                self,
                "错误",
                "用户名不能为空"
            )

            return
        
        if not password:

            QMessageBox.warning(
                self,
                "错误",
                "密码不能为空"
            )

            return

        if self.user_db.user_exists(username):

            QMessageBox.warning(
                self,
                "错误",
                "用户名已存在"
            )

            return

        self.user_db.create_user(
            username,
            password,
            role
        )

        self.load_users()

        self.username_edit.clear()
        self.password_edit.clear()
        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

    def reset_password(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.warning(
                self,
                "提示",
                "请选择用户"
            )

            return

        user_id = int(
            self.table.item(row, 0).text()
        )

        new_password, ok = QInputDialog.getText(
            self,
            "重置密码",
            "请输入新密码"
        )

        if not ok:
            return

        if not new_password:
            return

        self.user_db.reset_password(
            user_id,
            new_password
        )

        QMessageBox.information(
            self,
            "成功",
            "密码已重置"
        )

    def delete_selected_user(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.warning(
                self,
                "提示",
                "请先选择一个用户"
            )

            return

        user_id = int(
            self.table.item(row, 0).text()
        )

        user = self.user_db.get_user_by_id(
            user_id
        )

        if user is None:
            return

        _, username, role = user

        if role == "admin":

            QMessageBox.warning(
                self,
                "禁止",
                "不能删除管理员账号"
            )

            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定删除用户 {username} ?"
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.user_db.delete_user(user_id)

        self.load_users()
        self.table.clearSelection()

    def load_users(self):

        users = self.user_db.get_all_users()

        self.table.setRowCount(
            len(users)
        )

        for row, user in enumerate(users):

            user_id, username, role = user

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(str(user_id))
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(username)
            )

            self.table.setItem(
                row,
                2,
                QTableWidgetItem(role)
            )