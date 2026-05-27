"""统一 TTS 入口：auto → Qwen3-TTS → CosyVoice → pyttsx3。"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from ai.config import TTS_BACKEND
from ai.tts.backends import cosyvoice_backend, pyttsx3_backend, qwen_tts_backend

logger = logging.getLogger(__name__)

_active_backend: str | None = None


def reset_backend_cache() -> None:
    global _active_backend
    _active_backend = None


class TextToSpeechError(Exception):
    """语音合成业务异常。"""


def _pick_auto_backend() -> str:
    if qwen_tts_backend.is_available():
        return "qwen_tts"
    if cosyvoice_backend.is_available():
        return "cosyvoice"
    return "pyttsx3"


def get_tts_backend_name() -> str:
    global _active_backend
    if _active_backend:
        return _active_backend
    mode = (TTS_BACKEND or "auto").lower()
    if mode == "pyttsx3":
        _active_backend = "pyttsx3"
    elif mode == "qwen_tts":
        _active_backend = "qwen_tts" if qwen_tts_backend.is_available() else "pyttsx3"
    elif mode == "cosyvoice":
        _active_backend = "cosyvoice" if cosyvoice_backend.is_available() else "pyttsx3"
    elif mode == "gpt_sovits":
        try:
            from ai.tts.backends import gpt_sovits_backend

            _active_backend = "gpt_sovits" if gpt_sovits_backend.is_available() else _pick_auto_backend()
        except ImportError:
            _active_backend = _pick_auto_backend()
    else:
        _active_backend = _pick_auto_backend()
    return _active_backend


def get_tts_status_label() -> str:
    name = get_tts_backend_name()
    if name == "qwen_tts":
        return qwen_tts_backend.status_label()
    if name == "cosyvoice":
        return cosyvoice_backend.status_label()
    if name == "gpt_sovits":
        from ai.tts.backends import gpt_sovits_backend

        return gpt_sovits_backend.status_label()
    return "系统语音 (pyttsx3)"


def speak(
    text: str,
    block: bool = True,
    on_status: Callable[[str], None] | None = None,
) -> None:
    backend = get_tts_backend_name()
    try:
        if backend == "qwen_tts":
            qwen_tts_backend.speak(text, block=block, on_status=on_status)
        elif backend == "gpt_sovits":
            from ai.tts.backends import gpt_sovits_backend

            gpt_sovits_backend.speak(text, block=block, on_status=on_status)
        elif backend == "cosyvoice":
            cosyvoice_backend.speak(text, block=block, on_status=on_status)
        else:
            if on_status:
                on_status("正在系统语音播报…")
            pyttsx3_backend.speak(text, block=block)
    except Exception as exc:
        logger.warning("%s 失败，尝试回退: %s", backend, exc)
        global _active_backend
        if backend == "qwen_tts" and cosyvoice_backend.is_available():
            _active_backend = "cosyvoice"
            if on_status:
                on_status("Qwen TTS 失败，改用 CosyVoice…")
            cosyvoice_backend.speak(text, block=block, on_status=on_status)
        else:
            _active_backend = "pyttsx3"
            if on_status:
                on_status("改用系统语音…")
            pyttsx3_backend.speak(text, block=block)


def speak_async(text: str, on_done=None) -> threading.Thread:
    def _wrapper():
        try:
            speak(text, block=True)
        finally:
            if on_done:
                on_done()

    t = threading.Thread(target=_wrapper, daemon=True)
    t.start()
    return t
