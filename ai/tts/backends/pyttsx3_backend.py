"""pyttsx3 系统语音后端。"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_engine = None
_engine_lock = threading.Lock()
_speak_lock = threading.Lock()


def _get_engine():
    global _engine
    with _engine_lock:
        if _engine is not None:
            return _engine
        import pyttsx3

        _engine = pyttsx3.init()
        rate = _engine.getProperty("rate")
        _engine.setProperty("rate", max(150, int(rate * 0.95)))
        return _engine


def chunk_text(text: str, max_len: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in "。！？；\n" and len(buf) >= 20:
            parts.append(buf.strip())
            buf = ""
        elif len(buf) >= max_len:
            parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    return parts


def speak(text: str, block: bool = True) -> None:
    chunks = chunk_text(text)
    if not chunks:
        raise RuntimeError("播报文本为空")

    def _run():
        with _speak_lock:
            engine = _get_engine()
            for part in chunks:
                engine.say(part)
            engine.runAndWait()

    if block:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


def is_available() -> bool:
    try:
        import pyttsx3  # noqa: F401

        return True
    except ImportError:
        return False
