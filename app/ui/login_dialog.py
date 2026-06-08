from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QMessageBox,
)
from app.ui.register_dialog import RegisterDialog
from app.auth.session import UserSession

class LoginDialog(QDialog):

    def __init__(self, user_db):
        super().__init__()

        self.user_db = user_db
        self.role = None
        self.username = None

        self.setWindowTitle("登录")

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()

        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        login_button = QPushButton("登录")
        register_button = QPushButton("注册")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("用户名"))
        layout.addWidget(self.username_edit)

        layout.addWidget(QLabel("密码"))
        layout.addWidget(self.password_edit)

        layout.addWidget(login_button)
        layout.addWidget(register_button)

        login_button.clicked.connect(self.login)
        register_button.clicked.connect(self.open_register_dialog)

    def login(self):
        username = self.username_edit.text().strip()

        result = self.user_db.verify_user(
            username,
            self.password_edit.text()
        )
        print("LOGIN RESULT =", result)

        if result is None:
            QMessageBox.warning(
                self,
                "失败",
                "用户名或密码错误"
            )
            return
        user_id, role = result

        self.username = username
        self.role = role
        UserSession.user_id = user_id
        UserSession.username = username
        UserSession.role = role
        self.accept()

    def open_register_dialog(self):

        dialog = RegisterDialog(self.user_db)

        if dialog.exec() == QDialog.DialogCode.Accepted:

            self.username = dialog.username
            self.role = dialog.role
            UserSession.username = self.username
            UserSession.role = self.role
            self.accept()