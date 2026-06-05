from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
)


class RegisterDialog(QDialog):

    def __init__(self, user_db):
        super().__init__()

        self.user_db = user_db

        self.username = None
        self.role = None

        self.setWindowTitle("注册")

        self.username_edit = QLineEdit()

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.register_button = QPushButton("注册")
        self.back_button = QPushButton("返回登录")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("用户名"))
        layout.addWidget(self.username_edit)

        layout.addWidget(QLabel("密码"))
        layout.addWidget(self.password_edit)

        layout.addWidget(QLabel("确认密码"))
        layout.addWidget(self.confirm_edit)

        layout.addWidget(self.register_button)
        layout.addWidget(self.back_button)

        self.register_button.clicked.connect(
            self.register
        )

        self.back_button.clicked.connect(
            self.reject
        )

    def register(self):

        username = self.username_edit.text().strip()

        password = self.password_edit.text()

        confirm = self.confirm_edit.text()

        if not username:
            QMessageBox.warning(
                self,
                "错误",
                "用户名不能为空"
            )
            return

        if password != confirm:
            QMessageBox.warning(
                self,
                "错误",
                "两次密码不一致"
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
            "user"
        )

        self.username = username
        self.role = "user"

        QMessageBox.information(
            self,
            "成功",
            "注册成功，正在自动登录"
        )

        self.accept()