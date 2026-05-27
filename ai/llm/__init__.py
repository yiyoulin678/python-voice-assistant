"""大语言模型对话（Ollama + 人设 + 兜底）。"""
from ai.llm.dialogue import (
    DialogueError,
    clear_history,
    preload_dialogue,
    process_dialogue,
)
from ai.llm.history import ChatHistory

__all__ = [
    "ChatHistory",
    "DialogueError",
    "process_dialogue",
    "preload_dialogue",
    "clear_history",
]
