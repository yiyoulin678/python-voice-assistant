from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.media.now_playing import NowPlayingInfo


_POLL_INTERVAL_SECONDS = 0.32


class PlaybackPoller:
    """后台轮询 SMTC，避免在 UI 线程反复 asyncio.run。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: NowPlayingInfo | None = None
        self._snapshot_at = 0.0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

    def ensure_started(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="smtc-playback-poller", daemon=True)
        self._thread.start()

    def get_snapshot(self, *, max_age_seconds: float = 6.0) -> NowPlayingInfo | None:
        with self._lock:
            if self._snapshot is None:
                return None
            if time.monotonic() - self._snapshot_at > max_age_seconds:
                return None
            return self._snapshot

    def stop(self) -> None:
        self._stop.set()
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(lambda: None)
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        from app.media.now_playing import read_now_playing_async

        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            while not self._stop.is_set():
                try:
                    info = loop.run_until_complete(read_now_playing_async())
                except Exception:
                    info = None
                with self._lock:
                    self._snapshot = info
                    self._snapshot_at = time.monotonic()
                self._stop.wait(_POLL_INTERVAL_SECONDS)
        finally:
            loop.close()
            self._loop = None


playback_poller = PlaybackPoller()
