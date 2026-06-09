from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.agent import AgentRuntime
from app.auth.permissions import is_admin
from app.auth.session import UserSession, user_database_path
from app.task.constants import ALL_STATUSES, STATUS_RUNNING
from app.task.task_db import TaskDB
from app.task.task_runner import TaskExecutionWorker


class TaskManagementTab(QWidget):
    def __init__(
        self,
        base_dir: Path,
        agent_runtime: AgentRuntime | None = None,
    ) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.agent_runtime = agent_runtime
        self.db_path = user_database_path(base_dir)
        self.task_db = TaskDB(self.db_path)
        self._execution_thread: QThread | None = None
        self._execution_worker: TaskExecutionWorker | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("AI 任务管理"))
        if agent_runtime is None:
            hint = QLabel("当前 Agent 未就绪，可管理任务记录，但无法执行。")
            hint.setWordWrap(True)
            layout.addWidget(hint)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["任务ID", "用户ID", "标题", "状态"]
        )
        layout.addWidget(self.table)

        self.title_edit = QLineEdit()
        self.prompt_edit = QLineEdit()
        layout.addWidget(QLabel("任务标题"))
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("Prompt"))
        layout.addWidget(self.prompt_edit)

        self.create_button = QPushButton("创建任务")
        self.execute_button = QPushButton("执行任务")
        self.refresh_button = QPushButton("刷新")
        self.delete_button = QPushButton("删除任务")
        self.status_button = QPushButton("修改状态")
        self.detail_button = QPushButton("查看详情")
        layout.addWidget(self.create_button)
        layout.addWidget(self.execute_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.delete_button)
        layout.addWidget(self.status_button)
        layout.addWidget(self.detail_button)

        self.create_button.clicked.connect(self.create_task)
        self.execute_button.clicked.connect(self.execute_selected_task)
        self.refresh_button.clicked.connect(self.load_tasks)
        self.delete_button.clicked.connect(self.delete_selected_task)
        self.status_button.clicked.connect(self.change_status)
        self.detail_button.clicked.connect(self.show_detail)

        self._sync_execute_button()
        self.load_tasks()

    def _sync_execute_button(self) -> None:
        running = self._execution_thread is not None and self._execution_thread.isRunning()
        self.execute_button.setEnabled(
            self.agent_runtime is not None and not running
        )

    def load_tasks(self) -> None:
        if is_admin(UserSession.role):
            tasks = self.task_db.get_all_tasks()
        else:
            tasks = self.task_db.get_tasks_by_user(UserSession.user_id)

        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            if is_admin(UserSession.role):
                task_id, user_id, title, status = task
            else:
                task_id, title, status = task
                user_id = UserSession.user_id

            self.table.setItem(row, 0, QTableWidgetItem(str(task_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(user_id)))
            self.table.setItem(row, 2, QTableWidgetItem(title))
            self.table.setItem(row, 3, QTableWidgetItem(status))

    def create_task(self) -> None:
        title = self.title_edit.text().strip()
        prompt = self.prompt_edit.text().strip()

        if not title:
            QMessageBox.warning(self, "错误", "标题不能为空")
            return
        if not prompt:
            QMessageBox.warning(self, "错误", "Prompt 不能为空")
            return
        if UserSession.user_id is None:
            QMessageBox.warning(self, "错误", "当前未登录，无法创建任务。")
            return

        self.task_db.create_task(UserSession.user_id, title, prompt)
        self.title_edit.clear()
        self.prompt_edit.clear()
        self.load_tasks()

    def execute_selected_task(self) -> None:
        if self.agent_runtime is None:
            QMessageBox.warning(self, "无法执行", "Agent 尚未初始化，请稍后再试。")
            return
        if self._execution_thread is not None and self._execution_thread.isRunning():
            QMessageBox.warning(self, "请稍候", "已有任务正在执行。")
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择任务")
            return

        task_id = int(self.table.item(row, 0).text())
        status = self.table.item(row, 3).text().strip()
        if status == STATUS_RUNNING:
            QMessageBox.warning(self, "提示", "该任务正在执行中。")
            return

        reply = QMessageBox.question(
            self,
            "确认执行",
            f"确定让 Agent 执行任务 {task_id} 吗？\n执行期间会调用 LLM API。",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._start_execution(task_id)

    def _start_execution(self, task_id: int) -> None:
        thread = QThread(self)
        worker = TaskExecutionWorker(self.agent_runtime, self.db_path, task_id)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_execution_finished)
        worker.failed.connect(self._handle_execution_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_execution_thread)
        self._execution_thread = thread
        self._execution_worker = worker
        self._sync_execute_button()
        thread.start()

    def _clear_execution_thread(self) -> None:
        self._execution_thread = None
        self._execution_worker = None
        self._sync_execute_button()

    def _handle_execution_finished(self, task_id: int, result_text: str) -> None:
        self.load_tasks()
        preview = result_text.strip()
        if len(preview) > 400:
            preview = preview[:400] + "..."
        QMessageBox.information(
            self,
            "执行完成",
            f"任务 {task_id} 已完成。\n\n{preview or '（无文本结果）'}",
        )

    def _handle_execution_failed(self, task_id: int, error: str) -> None:
        self.load_tasks()
        QMessageBox.warning(self, "执行失败", f"任务 {task_id} 失败：{error}")

    def delete_selected_task(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择任务")
            return

        task_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定删除任务 {task_id} ?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.task_db.delete_task(task_id)
        self.load_tasks()

    def change_status(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择任务")
            return

        task_id = int(self.table.item(row, 0).text())
        status, ok = QInputDialog.getItem(
            self,
            "修改状态",
            "选择状态",
            list(ALL_STATUSES),
            0,
            False,
        )
        if not ok:
            return

        self.task_db.update_task_status(task_id, status)
        self.load_tasks()

    def show_detail(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择任务")
            return

        task_id = int(self.table.item(row, 0).text())
        task = self.task_db.get_task_by_id(task_id)
        if task is None:
            return

        _, user_id, title, prompt, status, result = task
        QMessageBox.information(
            self,
            "任务详情",
            f"""
标题：{title}
用户 ID：{user_id}
状态：{status}

Prompt：
{prompt}

Result：
{result or "暂无结果"}
""",
        )
