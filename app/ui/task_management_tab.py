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
    QInputDialog
)
from torch import layout

from app.task.task_db import TaskDB
from app.auth.session import UserSession


class TaskManagementTab(QWidget):

    def __init__(self):
        super().__init__()

        self.task_db = TaskDB(
            Path("users.db")
        )

        layout = QVBoxLayout(self)

        title = QLabel("AI任务管理")

        layout.addWidget(title)

        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels(
            [
                "任务ID",
                "用户ID",
                "标题",
                "状态"
            ]
        )

        layout.addWidget(self.table)

        self.title_edit = QLineEdit()

        self.prompt_edit = QLineEdit()

        self.create_button = QPushButton(
            "创建任务"
        )

        self.refresh_button = QPushButton(
            "刷新"
        )

        self.delete_button = QPushButton(
            "删除任务"
        )
        self.status_button = QPushButton(
            "修改状态"
        )

        self.detail_button = QPushButton(
            "查看详情"
        )

        layout.addWidget(QLabel("任务标题"))
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel("Prompt"))
        layout.addWidget(self.prompt_edit)

        layout.addWidget(self.create_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.delete_button)
        layout.addWidget(self.status_button)
        layout.addWidget(self.detail_button)

        self.create_button.clicked.connect(
            self.create_task
        )

        self.refresh_button.clicked.connect(
            self.load_tasks
        )

        self.delete_button.clicked.connect(
            self.delete_selected_task
        )
        self.status_button.clicked.connect(
            self.change_status
        )

        self.detail_button.clicked.connect(
            self.show_detail
        )
        self.load_tasks()

    def load_tasks(self):

        if UserSession.role == "admin":

            tasks = self.task_db.get_all_tasks()

        else:

            tasks = self.task_db.get_tasks_by_user(
                UserSession.user_id
            )

        self.table.setRowCount(
            len(tasks)
        )

        for row, task in enumerate(tasks):

            if UserSession.role == "admin":

                task_id, user_id, title, status = task

            else:

                task_id, title, status = task

                user_id = UserSession.user_id

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(str(task_id))
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(str(user_id))
            )

            self.table.setItem(
                row,
                2,
                QTableWidgetItem(title)
            )

            self.table.setItem(
                row,
                3,
                QTableWidgetItem(status)
            )

    def create_task(self):

        title = self.title_edit.text().strip()

        prompt = self.prompt_edit.text().strip()

        if not title:

            QMessageBox.warning(
                self,
                "错误",
                "标题不能为空"
            )

            return

        if not prompt:

            QMessageBox.warning(
                self,
                "错误",
                "Prompt不能为空"
            )

            return

        self.task_db.create_task(
            UserSession.user_id,
            title,
            prompt
        )

        self.title_edit.clear()
        self.prompt_edit.clear()

        self.load_tasks()

    def delete_selected_task(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.warning(
                self,
                "提示",
                "请选择任务"
            )

            return

        task_id = int(
            self.table.item(row, 0).text()
        )

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定删除任务 {task_id} ?"
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.task_db.delete_task(
            task_id
        )

        self.load_tasks()

    def change_status(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.warning(
                self,
                "提示",
                "请选择任务"
            )

            return

        task_id = int(
            self.table.item(row, 0).text()
        )

        status, ok = QInputDialog.getItem(
            self,
            "修改状态",
            "选择状态",
            [
                "pending",
                "running",
                "finished",
                "failed"
            ],
            0,
            False
        )

        if not ok:
            return

        self.task_db.update_task_status(
            task_id,
            status
        )

        self.load_tasks()

    def show_detail(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.warning(
                self,
                "提示",
                "请选择任务"
            )

            return

        task_id = int(
            self.table.item(row, 0).text()
        )

        task = self.task_db.get_task_by_id(
            task_id
        )

        if task is None:
            return

        (
            _,
            user_id,
            title,
            prompt,
            status,
            result
        ) = task

        QMessageBox.information(
            self,
            "任务详情",
            f"""
    标题：{title}

    状态：{status}

    Prompt：
    {prompt}

    Result：
    {result or "暂无结果"}
    """
        )