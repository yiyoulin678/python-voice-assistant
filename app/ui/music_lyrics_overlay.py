from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from app.media.lrc_parser import plain_line_at, synced_line_at
from app.media.lyrics_fetcher import TrackLyrics, fetch_track_lyrics
from app.media.now_playing import NowPlayingInfo, read_now_playing


LYRICS_OVERLAY_HEIGHT = 88
TRACK_POLL_INTERVAL_MS = 450
LYRIC_TICK_INTERVAL_MS = 50
SMTC_POSITION_TRUST_SECONDS = 0.35
_IDLE_POLLS_BEFORE_HIDE = 4


class LyricsFetchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, info: NowPlayingInfo, *, music_source: str = "netease") -> None:
        super().__init__()
        self._info = info
        self._music_source = music_source

    @Slot()
    def run(self) -> None:
        try:
            title, artist = self._info.resolved_title_and_artist()
            lyrics = fetch_track_lyrics(
                title,
                artist,
                album=self._info.album,
                duration_hint=self._info.duration_seconds,
                music_source=self._music_source,
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        self.finished.emit(lyrics)


@dataclass
class _PlaybackClock:
    track_key: str = ""
    started_at: float | None = None
    paused_at: float = 0.0
    is_playing: bool = False
    last_smtc_position: float = 0.0
    last_smtc_sync_at: float = 0.0


class MusicLyricsOverlay(QWidget):
    """立绘前方的透明歌词层。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        lyric_sync_offset_seconds: float = 1.2,
        music_source: str = "netease",
    ) -> None:
        super().__init__(parent)
        self._lyric_sync_offset_seconds = float(lyric_sync_offset_seconds)
        self._music_source = str(music_source).strip().lower() or "netease"
        self._idle_poll_streak = 0
        self._lyrics_fetch_done = False
        self.setObjectName("musicLyricsOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.lyrics_label = QLabel("", self)
        self.lyrics_label.setObjectName("musicLyricsText")
        self.lyrics_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.lyrics_label.setWordWrap(True)

        shadow = QGraphicsDropShadowEffect(self.lyrics_label)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.lyrics_label.setGraphicsEffect(shadow)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 0, 10, 12)
        layout.addStretch(1)
        layout.addWidget(self.lyrics_label)
        self.setLayout(layout)

        self._cached_info: NowPlayingInfo | None = None
        self._track_lyrics: TrackLyrics | None = None
        self._lyrics_track_key = ""
        self._last_displayed_line = ""
        self._fetch_thread: QThread | None = None
        self._fetch_worker: LyricsFetchWorker | None = None
        self._clock = _PlaybackClock()

        self._track_timer = QTimer(self)
        self._track_timer.setInterval(TRACK_POLL_INTERVAL_MS)
        self._track_timer.timeout.connect(self._poll_track)

        self._lyric_timer = QTimer(self)
        self._lyric_timer.setInterval(LYRIC_TICK_INTERVAL_MS)
        self._lyric_timer.timeout.connect(self._update_lyric_line)

        self._track_timer.start()
        self._lyric_timer.start()
        self._poll_track()

    def set_lyric_sync_offset(self, offset_seconds: float) -> None:
        try:
            value = float(offset_seconds)
        except (TypeError, ValueError):
            value = 1.2
        self._lyric_sync_offset_seconds = max(-5.0, min(5.0, value))

    def _poll_track(self) -> None:
        info = read_now_playing()
        if info is None or not info.lyric_line:
            self._idle_poll_streak += 1
            if self._idle_poll_streak >= _IDLE_POLLS_BEFORE_HIDE:
                self._reset_display()
            return

        self._idle_poll_streak = 0

        if info.track_key != self._clock.track_key:
            self._clock = _PlaybackClock(track_key=info.track_key)
            self._track_lyrics = None
            self._lyrics_track_key = ""
            self._last_displayed_line = ""
            self._lyrics_fetch_done = False
            self._seed_clock_from_info(info)
            self._start_lyrics_fetch(info)

        self._cached_info = info
        self._sync_playback_clock(info)
        self.show()
        self._update_lyric_line()

    def _seed_clock_from_info(self, info: NowPlayingInfo) -> None:
        self._clock.is_playing = info.is_playing
        if info.position_seconds <= SMTC_POSITION_TRUST_SECONDS:
            if info.is_playing:
                self._clock.started_at = time.monotonic()
            return
        self._apply_smtc_position(info.position_seconds, playing=info.is_playing)

    def _start_lyrics_fetch(self, info: NowPlayingInfo) -> None:
        self._cleanup_fetch_thread()
        self._lyrics_track_key = info.track_key
        self.lyrics_label.setText("歌词加载中…")
        thread = QThread(self)
        worker = LyricsFetchWorker(info, music_source=self._music_source)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_lyrics_loaded)
        worker.failed.connect(self._handle_lyrics_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_fetch_thread)
        self._fetch_thread = thread
        self._fetch_worker = worker
        thread.start()

    @Slot(object)
    def _handle_lyrics_loaded(self, lyrics: object) -> None:
        if not isinstance(lyrics, TrackLyrics):
            return
        if self._lyrics_track_key and self._lyrics_track_key != self._clock.track_key:
            return
        self._track_lyrics = lyrics
        self._lyrics_fetch_done = True
        self._update_lyric_line()

    @Slot(str)
    def _handle_lyrics_failed(self, message: str) -> None:
        _ = message
        self._lyrics_fetch_done = True
        self._update_lyric_line()

    def _apply_smtc_position(self, position_seconds: float, *, playing: bool) -> None:
        position_seconds = max(0.0, position_seconds)
        now = time.monotonic()
        self._clock.last_smtc_position = position_seconds
        self._clock.last_smtc_sync_at = now
        self._clock.is_playing = playing
        if playing:
            self._clock.started_at = now - position_seconds
            return
        self._clock.paused_at = position_seconds
        self._clock.started_at = None

    def _sync_playback_clock(self, info: NowPlayingInfo) -> None:
        if info.position_seconds > SMTC_POSITION_TRUST_SECONDS:
            drift = abs(info.position_seconds - self._playback_position_seconds())
            if (
                info.is_playing != self._clock.is_playing
                or drift > 1.0
                or self._clock.last_smtc_sync_at <= 0
            ):
                self._apply_smtc_position(info.position_seconds, playing=info.is_playing)
            else:
                self._clock.last_smtc_position = info.position_seconds
                self._clock.last_smtc_sync_at = time.monotonic()
                self._clock.is_playing = info.is_playing
            return

        if info.is_playing:
            if not self._clock.is_playing:
                if self._clock.started_at is None:
                    self._clock.started_at = time.monotonic() - self._clock.paused_at
                self._clock.is_playing = True
            return

        if self._clock.is_playing and self._clock.started_at is not None:
            self._clock.paused_at = max(0.0, time.monotonic() - self._clock.started_at)
        self._clock.is_playing = False
        self._clock.started_at = None

    def _playback_position_seconds(self) -> float:
        if self._clock.last_smtc_sync_at > 0:
            if self._clock.is_playing:
                return self._clock.last_smtc_position + (
                    time.monotonic() - self._clock.last_smtc_sync_at
                )
            return self._clock.last_smtc_position
        if self._clock.started_at is not None and self._clock.is_playing:
            return max(0.0, time.monotonic() - self._clock.started_at)
        return self._clock.paused_at

    def _effective_position(self) -> float:
        position = self._playback_position_seconds()
        if self._clock.is_playing:
            position += self._lyric_sync_offset_seconds
        return max(0.0, position)

    def _update_lyric_line(self) -> None:
        info = self._cached_info
        if info is None or not info.lyric_line:
            return
        if info.track_key != self._clock.track_key:
            return

        position = self._effective_position()
        lyrics = self._track_lyrics
        if lyrics is not None and lyrics.has_synced():
            line = synced_line_at(list(lyrics.synced_lines), position)
        elif lyrics is not None and lyrics.has_plain():
            duration = lyrics.duration_seconds or info.duration_seconds
            line = plain_line_at(list(lyrics.plain_lines), position, duration_seconds=duration)
        elif self._lyrics_fetch_done:
            line = "暂无歌词"
        else:
            line = info.lyric_line

        if not line.strip():
            self.hide()
            return
        if line != self._last_displayed_line:
            self._last_displayed_line = line
            self.lyrics_label.setText(line)
        self.show()

    def _reset_display(self) -> None:
        self.lyrics_label.setText("")
        self._last_displayed_line = ""
        self.hide()
        self._cached_info = None
        self._track_lyrics = None
        self._clock = _PlaybackClock()
        self._idle_poll_streak = 0

    def _cleanup_fetch_thread(self) -> None:
        if self._fetch_thread is not None and self._fetch_thread.isRunning():
            self._fetch_thread.quit()
            self._fetch_thread.wait(2000)
        self._clear_fetch_thread()

    def _clear_fetch_thread(self) -> None:
        self._fetch_thread = None
        self._fetch_worker = None

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._cleanup_fetch_thread()
        super().closeEvent(event)
