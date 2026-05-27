"""CosyVoice 声音克隆 TTS（常驻引擎 + 声线缓存）。"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from ai.config import (
    COSYVOICE_MODEL_DIR,
    COSYVOICE_REFERENCE_WAV,
    COSYVOICE_ROOT,
    PROJECT_ROOT,
)
from ai.tts.backends.cosyvoice_engine import CosyVoiceEngine, CosyVoiceEngineError, warmup

logger = logging.getLogger(__name__)


def _model_dir() -> Path:
    return COSYVOICE_ROOT / COSYVOICE_MODEL_DIR


def is_available() -> bool:
    if not COSYVOICE_REFERENCE_WAV.is_file():
        logger.debug("CosyVoice 参考音频不存在: %s", COSYVOICE_REFERENCE_WAV)
        return False
    if not COSYVOICE_ROOT.is_dir():
        return False
    if not _model_dir().is_dir():
        return False
    return True


def status_label() -> str:
    if not is_available():
        return "CosyVoice 未就绪"
    if CosyVoiceEngine.get().ready:
        return "CosyVoice 克隆声线（已缓存）"
    return "CosyVoice 克隆声线"


def speak(
    text: str,
    block: bool = True,
    on_status: Callable[[str], None] | None = None,
) -> None:
    if not text.strip():
        raise RuntimeError("播报文本为空")
    if not is_available():
        raise RuntimeError("CosyVoice 未就绪，请参考 docs/SETUP_LLM_TTS.md")

    try:
        out_wav = CosyVoiceEngine.get().speak(text, on_status=on_status)
    except CosyVoiceEngineError as exc:
        raise RuntimeError(str(exc)) from exc

    try:
        if on_status:
            on_status("正在播放…")
        from ai.audio_io import play_wav

        play_wav(str(out_wav))
    finally:
        out_wav.unlink(missing_ok=True)
