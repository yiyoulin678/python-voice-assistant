from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer

from app.media.music import normalize_music_source
from app.media.now_playing import is_music_app, read_now_playing
from app.ui.live2d_portrait_controller import Live2DPortraitController

_TICK_MS = 360


class MusicSingAlongController(QObject):
    """音乐播放时驱动 Live2D 口型与说话表情（不播放 TTS，避免盖住原曲）。"""

    def __init__(
        self,
        *,
        get_portrait: Callable[[], object],
        is_blocked: Callable[[], bool],
        music_source: str = "netease",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_portrait = get_portrait
        self._is_blocked = is_blocked
        self._music_source = normalize_music_source(music_source)
        self._enabled = False
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if self._enabled:
            self._timer.start()
            self._tick()
            return
        self._timer.stop()
        self._stop_singing()

    def set_music_source(self, source: str) -> None:
        self._music_source = normalize_music_source(source)

    def _tick(self) -> None:
        if not self._enabled:
            return
        if self._is_blocked():
            self._stop_singing()
            return

        info = read_now_playing()
        should_sing = (
            info is not None
            and info.is_playing
            and is_music_app(info.app_id, source=self._music_source)
        )
        if not should_sing:
            self._stop_singing()
            return
        if self._active:
            return
        portrait = self._get_portrait()
        if not isinstance(portrait, Live2DPortraitController):
            return
        portrait.begin_speech(None)
        self._active = True

    def _stop_singing(self) -> None:
        if not self._active:
            return
        portrait = self._get_portrait()
        if isinstance(portrait, Live2DPortraitController):
            portrait.end_speech()
        self._active = False
