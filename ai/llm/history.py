"""多轮对话内存历史（GUI 会话内；后续可接 SQLite）。"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


def _default_max_turns() -> int:
    try:
        from ai.config import DIALOGUE_MAX_HISTORY_TURNS

        return DIALOGUE_MAX_HISTORY_TURNS
    except Exception:
        return 8


@dataclass
class ChatHistory:
    max_turns: int = field(default_factory=_default_max_turns)
    _pairs: deque[tuple[str, str]] = field(default_factory=deque)

    def add(self, user: str, assistant: str) -> None:
        self._pairs.append((user.strip(), assistant.strip()))
        while len(self._pairs) > self.max_turns:
            self._pairs.popleft()

    def clear(self) -> None:
        self._pairs.clear()

    def to_ollama_messages(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for user, assistant in self._pairs:
            out.append({"role": "user", "content": user})
            out.append({"role": "assistant", "content": assistant})
        return out


_global_history = ChatHistory()


def get_history() -> ChatHistory:
    return _global_history
