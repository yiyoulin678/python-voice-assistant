"""文本处理对外接口（兼容旧代码；内部走 ai.llm）。"""
from __future__ import annotations

from ai.llm.dialogue import DialogueError, ProcessMode, process_dialogue
from ai.llm.dialogue import clear_history
from ai.llm.dialogue import preload_dialogue as preload_nlp

# 兼容旧异常名
TextProcessError = DialogueError

__all__ = [
    "ProcessMode",
    "TextProcessError",
    "process_text",
    "preload_nlp",
    "clear_history",
]

clear_dialogue_history = clear_history


def process_text(text: str, mode: str = ProcessMode.QA, user_nickname: str = "你") -> str:
    return process_dialogue(text, mode=mode, user_nickname=user_nickname)
