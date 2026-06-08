from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from app.core.debug_log import debug_log


class HistoryAudioPlayer(QObject):
    """独立播放器，用于历史记录回放，不占用 TTS 播放队列。"""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._audio_output: QAudioOutput | None = None
        self._player: QMediaPlayer | None = None

    def play(self, audio_path: Path) -> bool:
        if not audio_path.exists():
            debug_log("HistoryAudio", "音频文件不存在", {"audio_path": str(audio_path)})
            return False
        self._ensure_player()
        assert self._player is not None
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(str(audio_path.resolve())))
        self._player.play()
        debug_log("HistoryAudio", "开始回放历史音频", {"audio_path": str(audio_path)})
        return True

    def stop(self) -> None:
        if self._player is None:
            return
        self._player.stop()

    def _ensure_player(self) -> None:
        if self._player is not None:
            return
        self._audio_output = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
