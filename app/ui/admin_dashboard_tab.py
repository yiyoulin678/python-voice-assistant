from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QGroupBox
)

from app.auth.user_db import UserDB
from app.auth.session import UserSession, role_display_name, user_database_path
from app.task.task_db import TaskDB


class AdminDashboardTab(QWidget):

    def __init__(self, base_dir: Path) -> None:
        super().__init__()

        db_path = user_database_path(base_dir)
        self.user_db = UserDB(db_path)
        self.task_db = TaskDB(db_path)

        main_layout = QVBoxLayout(self)

        #
        # 系统统计
        #
        stats_group = QGroupBox("系统统计")

        stats_form = QFormLayout()

        self.user_count_edit = QLineEdit()
        self.user_count_edit.setReadOnly(True)

        self.admin_count_edit = QLineEdit()
        self.admin_count_edit.setReadOnly(True)

        stats_form.addRow(
            "用户总数",
            self.user_count_edit
        )

        stats_form.addRow(
            "管理员数量",
            self.admin_count_edit
        )

        stats_group.setLayout(
            stats_form
        )

        #
        # 任务统计
        #
        task_group = QGroupBox("任务统计")

        task_form = QFormLayout()

        self.task_count_edit = QLineEdit()
        self.task_count_edit.setReadOnly(True)

        self.pending_count_edit = QLineEdit()
        self.pending_count_edit.setReadOnly(True)

        self.done_count_edit = QLineEdit()
        self.done_count_edit.setReadOnly(True)

        task_form.addRow(
            "任务总数",
            self.task_count_edit
        )

        task_form.addRow(
            "待处理任务",
            self.pending_count_edit
        )

        task_form.addRow(
            "已完成任务",
            self.done_count_edit
        )

        task_group.setLayout(
            task_form
        )

        #
        # 当前登录信息
        #
        account_group = QGroupBox(
            "当前登录信息"
        )

        account_form = QFormLayout()

        self.username_edit = QLineEdit()
        self.username_edit.setReadOnly(True)

        self.role_edit = QLineEdit()
        self.role_edit.setReadOnly(True)

        account_form.addRow(
            "当前用户",
            self.username_edit
        )

        account_form.addRow(
            "当前角色",
            self.role_edit
        )

        account_group.setLayout(
            account_form
        )

        #
        # 刷新按钮
        #
        self.refresh_button = QPushButton(
            "刷新统计"
        )

        self.refresh_button.clicked.connect(
            self.load_statistics
        )

        #
        # 添加到页面
        #
        main_layout.addWidget(
            stats_group
        )

        main_layout.addWidget(
            task_group
        )

        main_layout.addWidget(
            account_group
        )

        main_layout.addWidget(
            self.refresh_button
        )

        self.load_statistics()

    def load_statistics(self):

        users = self.user_db.get_user_count()

        admins = self.user_db.get_admin_count()

        tasks = self.task_db.get_task_count()

        pending = self.task_db.get_pending_count()

        done = self.task_db.get_done_count()

        self.user_count_edit.setText(
            str(users)
        )

        self.admin_count_edit.setText(
            str(admins)
        )

        self.task_count_edit.setText(
            str(tasks)
        )

        self.pending_count_edit.setText(
            str(pending)
        )

        self.done_count_edit.setText(
            str(done)
        )

        self.username_edit.setText(
            UserSession.username
        )

        self.role_edit.setText(
            role_display_name(UserSession.role)
        )
