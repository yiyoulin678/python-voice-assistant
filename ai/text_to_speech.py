"""文字转语音（pyttsx3）。"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_engine = None
_engine_lock = threading.Lock()
_speak_lock = threading.Lock()


class TextToSpeechError(Exception):
    """语音合成业务异常。"""


def _get_engine():
    global _engine
    with _engine_lock:
        if _engine is not None:
            return _engine
        try:
            import pyttsx3
        except ImportError as exc:
            raise TextToSpeechError(
                "未安装 pyttsx3，请执行: pip install pyttsx3"
            ) from exc
        try:
            _engine = pyttsx3.init()
            rate = _engine.getProperty("rate")
            _engine.setProperty("rate", max(150, int(rate * 0.95)))
        except Exception as exc:
            raise TextToSpeechError(f"初始化 TTS 引擎失败: {exc}") from exc
        return _engine


def _chunk_text(text: str, max_len: int = 120) -> list[str]:
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
    """播报文本。block=True 时阻塞直到读完。"""
    chunks = _chunk_text(text)
    if not chunks:
        raise TextToSpeechError("播报文本为空。")

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


def speak_to_file(text: str, wav_path: str) -> str:
    """尝试将文本保存为 wav（依赖 pyttsx3 与系统语音；失败时仅返回路径占位说明）。"""
    path = Path(wav_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        engine = _get_engine()
        engine.save_to_file(text, str(path))
        engine.runAndWait()
        if path.is_file() and path.stat().st_size > 0:
            return str(path.resolve())
    except Exception as exc:
        logger.warning("save_to_file 不可用: %s", exc)

    raise TextToSpeechError(
        "当前环境无法将 TTS 导出为 wav，请使用 speak() 直接播报。"
    )


def speak_async(text: str, on_done=None) -> threading.Thread:
    """后台线程播报，可选完成回调。"""
    def _wrapper():
        try:
            speak(text, block=True)
        finally:
            if on_done:
                on_done()

    t = threading.Thread(target=_wrapper, daemon=True)
    t.start()
    return t
