from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agent.actions import AgentResult
from app.llm.chat_reply import ChatReply, ChatSegment
from app.task.constants import STATUS_DONE, STATUS_FAILED, STATUS_PENDING, STATUS_RUNNING
from app.task.task_db import TaskDB
from app.task.task_runner import (
    build_task_messages,
    execute_task_sync,
    format_task_result,
)


def test_build_task_messages_includes_title_and_prompt() -> None:
    messages = build_task_messages("课设摘要", "列出基础必做五项")
    assert len(messages) == 1
    content = messages[0]["content"]
    assert "课设摘要" in content
    assert "列出基础必做五项" in content
    assert "后台 AI 任务" in content


def test_format_task_result_prefers_translation() -> None:
    result = AgentResult(
        reply=ChatReply(
            segments=[
                ChatSegment(text="こんにちは", translation="你好", tone="中性"),
            ]
        )
    )
    assert format_task_result(result) == "你好"


def test_execute_task_sync_updates_database(tmp_path: Path) -> None:
    db_path = tmp_path / "users.db"
    task_db = TaskDB(db_path)
    task_id = task_db.create_task(1, "测试任务", "用一句话介绍 Python")

    agent_runtime = MagicMock()
    pipeline = MagicMock()
    pipeline.run_user_message.return_value = AgentResult(
        reply=ChatReply(
            segments=[
                ChatSegment(text="Python", translation="Python 是一门编程语言。", tone="中性"),
            ]
        )
    )

    import app.task.task_runner as task_runner_module

    original_pipeline = task_runner_module.ChatPipeline
    task_runner_module.ChatPipeline = MagicMock(return_value=pipeline)
    try:
        result_text = execute_task_sync(agent_runtime, db_path, task_id)
    finally:
        task_runner_module.ChatPipeline = original_pipeline

    assert "Python" in result_text
    refreshed = TaskDB(db_path).get_task_by_id(task_id)
    assert refreshed is not None
    _id, _user_id, _title, _prompt, status, stored_result = refreshed
    assert status == STATUS_DONE
    assert stored_result == result_text


def test_execute_task_sync_marks_failed_on_error(tmp_path: Path) -> None:
    db_path = tmp_path / "users.db"
    task_db = TaskDB(db_path)
    task_id = task_db.create_task(1, "失败任务", "触发异常")

    agent_runtime = MagicMock()
    pipeline = MagicMock()
    pipeline.run_user_message.side_effect = RuntimeError("LLM 不可用")

    import app.task.task_runner as task_runner_module

    original_pipeline = task_runner_module.ChatPipeline
    task_runner_module.ChatPipeline = MagicMock(return_value=pipeline)
    try:
        with pytest.raises(RuntimeError, match="LLM 不可用"):
            execute_task_sync(agent_runtime, db_path, task_id)
    finally:
        task_runner_module.ChatPipeline = original_pipeline

    refreshed = TaskDB(db_path).get_task_by_id(task_id)
    assert refreshed is not None
    _id, _user_id, _title, _prompt, status, stored_result = refreshed
    assert status == STATUS_FAILED
    assert "LLM 不可用" in (stored_result or "")


def test_task_db_create_task_sets_pending_and_created_at(tmp_path: Path) -> None:
    db_path = tmp_path / "users.db"
    task_db = TaskDB(db_path)
    task_id = task_db.create_task(2, "标题", "prompt")
    task = task_db.get_task_by_id(task_id)
    assert task is not None
    assert task[4] == STATUS_PENDING
