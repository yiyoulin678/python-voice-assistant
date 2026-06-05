from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
)


class UserManagementTab(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel("用户管理（管理员专用）")
        )