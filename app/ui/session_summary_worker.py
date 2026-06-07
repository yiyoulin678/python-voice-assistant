from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.ai.session_summary import SessionTurn, append_session_summary, generate_session_summary
from app.llm.api_client import OpenAICompatibleClient


class SessionSummaryWorker(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        api_client: OpenAICompatibleClient,
        turn: SessionTurn,
        note_path: Path,
    ) -> None:
        super().__init__()
        self.api_client = api_client
        self.turn = turn
        self.note_path = note_path

    @Slot()
    def run(self) -> None:
        try:
            summary = generate_session_summary(self.api_client, self.turn)
            append_session_summary(self.note_path, summary)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(summary)
        finally:
            self.finished.emit()
