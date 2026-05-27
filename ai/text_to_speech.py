"""TTS 对外接口（兼容旧代码；内部走 ai.tts）。"""
from __future__ import annotations

from ai.tts.speaker import (
    TextToSpeechError,
    get_tts_backend_name,
    get_tts_status_label,
    speak,
    speak_async,
)

# 兼容：预热 CosyVoice
from ai.tts.backends.cosyvoice_backend import warmup as warmup_cosyvoice

__all__ = [
    "TextToSpeechError",
    "speak",
    "speak_async",
    "get_tts_backend_name",
    "get_tts_status_label",
]
