from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.agent import AgentResult, AgentRuntime
from app.core.chat_pipeline import ChatPipeline
from app.core.debug_log import debug_log
from app.llm.chat_reply import ChatReply
from app.task.constants import STATUS_DONE, STATUS_PENDING, STATUS_RUNNING, STATUS_FAILED
from app.task.task_db import TaskDB


def build_task_messages(title: str, prompt: str) -> list[dict[str, Any]]:
    """把后台任务转成 Agent 可处理的用户消息。"""
    clean_title = title.strip() or "未命名任务"
    clean_prompt = prompt.strip()
    return [
        {
            "role": "user",
            "content": (
                f"【后台 AI 任务】{clean_title}\n"
                f"{clean_prompt}\n\n"
                "请直接完成任务，并给出简洁、可存档的中文结果。"
                "优先输出结论与要点，不要闲聊，不要切换角色扮演口吻。"
            ),
        }
    ]


def format_task_result(result: AgentResult) -> str:
    """把 Agent 回复整理为可写入任务表的文本。"""
    reply = result.reply
    body = _format_reply_text(reply)
    if not result.actions:
        return body

    action_notes: list[str] = []
    for action in result.actions:
        action_type = (action.type or "").strip()
        if not action_type:
            continue
        if action_type == "pending_tool":
            reason = str(action.payload.get("reason", "")).strip()
            tool_name = str(action.payload.get("tool_name", "")).strip()
            detail = "；".join(part for part in (tool_name, reason) if part)
            action_notes.append(f"待确认工具：{detail or action_type}")
        else:
            action_notes.append(action_type)

    if not action_notes:
        return body

    suffix = "\n\n[系统提示] " + "；".join(action_notes)
    return (body + suffix).strip()


def _format_reply_text(reply: ChatReply) -> str:
    translation = reply.translation.strip()
    if translation:
        return translation
    return reply.text.strip()


def execute_task_sync(
    agent_runtime: AgentRuntime,
    db_path: Path,
    task_id: int,
) -> str:
    """在调用线程中同步执行任务，供 Worker 与单元测试复用。"""
    task_db = TaskDB(db_path)
    task = task_db.get_task_by_id(task_id)
    if task is None:
        raise ValueError(f"任务不存在：{task_id}")

    _task_id, _user_id, title, prompt, status, _existing_result = task
    if status == STATUS_RUNNING:
        raise RuntimeError(f"任务 {task_id} 正在执行中。")

    task_db.update_task_status(task_id, STATUS_RUNNING)
    debug_log(
        "TaskRunner",
        "开始执行任务",
        {"task_id": task_id, "title": title, "previous_status": status},
    )
    try:
        pipeline = ChatPipeline(agent_runtime)
        result = pipeline.run_user_message(build_task_messages(title, prompt))
        result_text = format_task_result(result)
        task_db.update_task_result(task_id, result_text)
        task_db.update_task_status(task_id, STATUS_DONE)
        debug_log(
            "TaskRunner",
            "任务执行完成",
            {"task_id": task_id, "result_chars": len(result_text)},
        )
        return result_text
    except Exception as exc:
        error_text = str(exc).strip() or "任务执行失败"
        task_db.update_task_result(task_id, error_text)
        task_db.update_task_status(task_id, STATUS_FAILED)
        debug_log(
            "TaskRunner",
            "任务执行失败",
            {"task_id": task_id, "error": error_text},
        )
        raise


class TaskExecutionWorker(QObject):
    finished = Signal(int, str)
    failed = Signal(int, str)

    def __init__(
        self,
        agent_runtime: AgentRuntime,
        db_path: Path,
        task_id: int,
    ) -> None:
        super().__init__()
        self.agent_runtime = agent_runtime
        self.db_path = db_path
        self.task_id = task_id

    @Slot()
    def run(self) -> None:
        try:
            result_text = execute_task_sync(
                self.agent_runtime,
                self.db_path,
                self.task_id,
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(self.task_id, str(exc))
            return
        self.finished.emit(self.task_id, result_text)
