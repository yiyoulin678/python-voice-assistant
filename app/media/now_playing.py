from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.debug_log import debug_log


_SCRIPT_PATH = Path(__file__).with_name("smtc_read.ps1")

_READ_CACHE_TTL_SECONDS = 0.4
_read_cache_at: float = 0.0
_read_cache_value: NowPlayingInfo | None = None
_PREFERRED_MUSIC_SOURCE = "netease"
_MUSIC_APP_HINTS: dict[str, tuple[str, ...]] = {
    "netease": ("cloudmusic", "netease"),
    "qq": ("qqmusic", "qqmusiclite"),
}


def set_preferred_music_source(source: str) -> None:
    global _PREFERRED_MUSIC_SOURCE
    normalized = str(source).strip().lower()
    if normalized in _MUSIC_APP_HINTS:
        _PREFERRED_MUSIC_SOURCE = normalized


def is_music_app(app_id: str, *, source: str | None = None) -> bool:
    app = str(app_id or "").lower()
    key = source or _PREFERRED_MUSIC_SOURCE
    hints = _MUSIC_APP_HINTS.get(key, _MUSIC_APP_HINTS["netease"])
    return any(hint in app for hint in hints)


def _normalize_track_part(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


@dataclass(frozen=True)
class NowPlayingInfo:
    title: str = ""
    artist: str = ""
    album: str = ""
    is_playing: bool = False
    app_id: str = ""
    position_seconds: float = 0.0
    duration_seconds: float = 0.0

    @property
    def track_key(self) -> str:
        return f"{_normalize_track_part(self.title)}|{_normalize_track_part(self.artist)}"

    @property
    def lyric_line(self) -> str:
        title, artist = self._split_title_artist()
        if title and artist:
            return f"{title} — {artist}"
        return title or artist

    def resolved_title_and_artist(self) -> tuple[str, str]:
        return self._split_title_artist()

    def _split_title_artist(self) -> tuple[str, str]:
        title = self.title.strip()
        artist = self.artist.strip()
        if title and not artist:
            for sep in (" - ", " – ", "—", " / "):
                if sep in title:
                    left, right = title.split(sep, 1)
                    if left.strip() and right.strip():
                        return left.strip(), right.strip()
        if artist and not title:
            for sep in (" - ", " – ", "—", " / "):
                if sep in artist:
                    left, right = artist.split(sep, 1)
                    if left.strip() and right.strip():
                        return left.strip(), right.strip()
        return title, artist

    @property
    def display_line(self) -> str:
        return self.lyric_line


def read_now_playing(*, force: bool = False) -> NowPlayingInfo | None:
    global _read_cache_at, _read_cache_value
    if sys.platform != "win32":
        return None

    from app.media.playback_poller import playback_poller

    playback_poller.ensure_started()
    snapshot = playback_poller.get_snapshot()
    if snapshot is not None and not force:
        return snapshot

    now = time.monotonic()
    if (
        not force
        and _read_cache_value is not None
        and now - _read_cache_at < _READ_CACHE_TTL_SECONDS
    ):
        return _read_cache_value

    try:
        info = asyncio.run(read_now_playing_async())
    except Exception as exc:
        debug_log("Media", "同步读取播放信息失败", {"error": str(exc)})
        info = None
    if info is None:
        info = _read_now_playing_powershell()
    _read_cache_at = now
    _read_cache_value = info
    return info


async def read_now_playing_async() -> NowPlayingInfo | None:
    if sys.platform != "win32":
        return None
    return await _read_now_playing_winsdk_async()


async def _read_now_playing_winsdk_async() -> NowPlayingInfo | None:
    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus,
        )
    except ImportError:
        return None

    async def _read_async() -> NowPlayingInfo | None:
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        candidates: list[tuple[int, NowPlayingInfo]] = []
        for session in manager.get_sessions():
            try:
                props = await session.try_get_media_properties_async()
                playback = session.get_playback_info()
                status = playback.playback_status
                title = str(props.title or "").strip()
                artist = str(props.artist or "").strip()
                album = str(props.album_title or "").strip()
                if not title and not artist:
                    continue
                is_playing = (
                    status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
                )
                timeline = session.get_timeline_properties()
                position_seconds = _time_span_seconds(timeline.position)
                duration_seconds = _time_span_seconds(timeline.end_time)
                app_id = str(session.source_app_user_model_id or "")
                score = (100 if is_playing else 0) + (10 if title else 0)
                if is_music_app(app_id):
                    score += 80
                if position_seconds > 0.5:
                    score += 25
                candidates.append(
                    (
                        score,
                        NowPlayingInfo(
                            title=title,
                            artist=artist,
                            album=album,
                            is_playing=is_playing,
                            app_id=app_id,
                            position_seconds=position_seconds,
                            duration_seconds=duration_seconds,
                        ),
                    )
                )
            except Exception:
                continue
        if not candidates:
            return None
        music_candidates = [
            item for item in candidates if is_music_app(item[1].app_id)
        ]
        pool = music_candidates if music_candidates else candidates
        return max(pool, key=lambda item: item[0])[1]

    return await _read_async()


def _time_span_seconds(value: object) -> float:
    if value is None:
        return 0.0
    total_seconds = getattr(value, "total_seconds", None)
    if callable(total_seconds):
        try:
            return max(0.0, float(total_seconds()))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _read_now_playing_powershell() -> NowPlayingInfo | None:
    if not _SCRIPT_PATH.is_file():
        return None
    kwargs: dict[str, object] = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 8,
        "check": False,
    }
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    for executable in ("pwsh", "powershell"):
        completed = subprocess.run(
            [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(_SCRIPT_PATH)],
            **kwargs,
        )
        if completed.returncode != 0:
            continue
        text = (completed.stdout or "").strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        info = NowPlayingInfo(
            title=str(data.get("title") or ""),
            artist=str(data.get("artist") or ""),
            album=str(data.get("album") or ""),
            is_playing=bool(data.get("is_playing")),
            app_id=str(data.get("app") or ""),
        )
        if info.lyric_line:
            return info
    return None
