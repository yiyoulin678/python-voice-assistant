"""Qwen3-TTS 播报后端（优先 WebUI 官方 HTTP API）。"""

from __future__ import annotations



import logging

import tempfile

from collections.abc import Callable

from pathlib import Path



from ai.config import (

    QWEN_TTS_ENABLED,

    QWEN_TTS_MODE,

    QWEN_TTS_SPEAKER,

    QWEN_TTS_USE_WEBUI_API,

)

from ai.tts.backends.qwen_tts_webui_env import webui_root



logger = logging.getLogger(__name__)





def _use_webui_api() -> bool:

    return bool(QWEN_TTS_USE_WEBUI_API and webui_root())





def is_available() -> bool:

    if not QWEN_TTS_ENABLED:

        return False

    if _use_webui_api():

        from ai.tts.backends.qwen_tts_webui_env import webui_python_exe



        return webui_python_exe() is not None

    from ai.config import QWEN_TTS_USE_WEBUI_PYTHON

    from ai.tts.backends.qwen_tts_webui_env import webui_python_exe as _py



    if QWEN_TTS_USE_WEBUI_PYTHON and _py() is not None:

        return True

    try:

        import qwen_tts  # noqa: F401



        return True

    except ImportError:

        return False





def status_label() -> str:

    mode = (QWEN_TTS_MODE or "custom_voice").lower()

    suffix = " · WebUI API" if _use_webui_api() else ""

    if mode == "clone":

        return f"Qwen3-TTS 声音克隆{suffix}"

    return f"Qwen3-TTS · {QWEN_TTS_SPEAKER}{suffix}"





def warmup(on_status: Callable[[str], None] | None = None) -> None:

    if _use_webui_api():

        from ai.tts.backends import qwen_tts_webui_api



        qwen_tts_webui_api.ensure_api_running(on_status)

        return

    from ai.tts.backends.qwen_tts_engine import warmup as _engine_warmup



    _engine_warmup(on_status)





def set_reference(

    wav_path: str,

    prompt_text: str | None = None,

    on_status: Callable[[str], None] | None = None,

) -> None:

    if _use_webui_api():

        from ai.tts.backends import qwen_tts_webui_api



        qwen_tts_webui_api.set_reference(wav_path, prompt_text, on_status=on_status)

    else:

        from ai.tts.backends.qwen_tts_engine import set_reference as _engine_set



        _engine_set(wav_path, prompt_text, on_status=on_status)

    from ai.tts import speaker



    speaker.reset_backend_cache()





def speak(

    text: str,

    block: bool = True,

    on_status: Callable[[str], None] | None = None,

) -> None:

    def _emit(msg: str) -> None:

        if on_status:

            on_status(msg)



    from ai.tts.backends.qwen_tts_webui_api import QwenTTSApiError

    from ai.tts.backends.qwen_tts_engine import QwenTTSEngine, QwenTTSEngineError



    try:

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:

            out = Path(tmp.name)



        if _use_webui_api():

            from ai.tts.backends import qwen_tts_webui_api



            wav_bytes, _sr = qwen_tts_webui_api.speak(text, on_status=on_status)

            out.write_bytes(wav_bytes)

        else:

            import soundfile as sf



            _emit("Qwen3-TTS 合成中…")

            audio, sr = QwenTTSEngine.get().speak(text, on_status=on_status)

            sf.write(str(out), audio, sr)



        try:

            _emit("正在播放…")

            from ai.audio_io import play_wav



            play_wav(str(out))

        finally:

            out.unlink(missing_ok=True)

    except (QwenTTSApiError, QwenTTSEngineError) as exc:

        raise RuntimeError(str(exc)) from exc


