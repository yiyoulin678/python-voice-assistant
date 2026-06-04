from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QMessageBox,
)


class LoginDialog(QDialog):

    def __init__(self, user_db):
        super().__init__()

        self.user_db = user_db
        self.role = None

        self.setWindowTitle("登录")

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()

        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        login_button = QPushButton("登录")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("用户名"))
        layout.addWidget(self.username_edit)

        layout.addWidget(QLabel("密码"))
        layout.addWidget(self.password_edit)

        layout.addWidget(login_button)

        login_button.clicked.connect(self.login)

    def login(self):

        role = self.user_db.verify_user(
            self.username_edit.text(),
            self.password_edit.text()
        )

        if role is None:
            QMessageBox.warning(
                self,
                "失败",
                "用户名或密码错误"
            )
            return

        self.role = role

        self.accept()