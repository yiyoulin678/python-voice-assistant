"""VoxCPM 播报后端。"""
from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

from ai.config import VOXCPM_ENABLED, VOXCPM_MODE, VOXCPM_MODEL_ID, VOXCPM_REFERENCE_WAV
from ai.tts.backends.voxcpm_engine import (
    VoxCPMEngine,
    VoxCPMEngineError,
    set_reference as _set_reference,
    warmup,
)

logger = logging.getLogger(__name__)


def is_available() -> bool:
    if not VOXCPM_ENABLED:
        return False
    try:
        import voxcpm  # noqa: F401

        return True
    except ImportError:
        return False


def status_label() -> str:
    mode = (VOXCPM_MODE or "clone").lower()
    name = Path(VOXCPM_MODEL_ID).name if "/" in VOXCPM_MODEL_ID else VOXCPM_MODEL_ID
    if mode == "design":
        return f"VoxCPM 声音设计 · {name}"
    if VOXCPM_REFERENCE_WAV.is_file():
        return f"VoxCPM 声音克隆 · {name}"
    return f"VoxCPM（请先选择克隆音频）· {name}"


def speak(
    text: str,
    block: bool = True,
    on_status: Callable[[str], None] | None = None,
) -> None:
    def _emit(msg: str) -> None:
        if on_status:
            on_status(msg)

    try:
        _emit("VoxCPM 合成中…")
        audio, sr = VoxCPMEngine.get().speak(text, on_status=on_status)
    except VoxCPMEngineError as exc:
        raise RuntimeError(str(exc)) from exc

    import soundfile as sf

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out = Path(tmp.name)
        sf.write(str(out), audio, sr)

    try:
        _emit("正在播放…")
        from ai.audio_io import play_wav

        play_wav(str(out))
    finally:
        out.unlink(missing_ok=True)


def set_reference(
    wav_path: str,
    prompt_text: str | None = None,
    on_status: Callable[[str], None] | None = None,
) -> None:
    _set_reference(wav_path, prompt_text, on_status=on_status)
    from ai.tts import speaker

    speaker.reset_backend_cache()
