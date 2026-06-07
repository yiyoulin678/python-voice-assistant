from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.core.debug_log import format_debug_data

_MAX_ENTRIES = 500


@dataclass(frozen=True)
class NapCatLogEntry:
    timestamp: str
    message: str
    detail: str

    def format_line(self) -> str:
        if self.detail:
            return f"[{self.timestamp}] {self.message} {self.detail}"
        return f"[{self.timestamp}] {self.message}"


class NapCatEventLog(QObject):
    """NapCat 运行日志缓冲，供内置控制台实时展示。"""

    entry_added = Signal(object)
    cleared = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._entries: deque[NapCatLogEntry] = deque(maxlen=_MAX_ENTRIES)

    def append(self, message: str, data: Any | None = None) -> NapCatLogEntry:
        detail = format_debug_data(data) if data is not None else ""
        entry = NapCatLogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            message=message.strip(),
            detail=detail.strip(),
        )
        self._entries.append(entry)
        self.entry_added.emit(entry)
        return entry

    def entries(self) -> list[NapCatLogEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self.cleared.emit()


_EVENT_LOG: NapCatEventLog | None = None


def napcat_event_log() -> NapCatEventLog:
    global _EVENT_LOG
    if _EVENT_LOG is None:
        _EVENT_LOG = NapCatEventLog()
    return _EVENT_LOG
