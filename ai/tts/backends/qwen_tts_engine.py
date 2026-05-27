"""Qwen3-TTS 常驻引擎（CustomVoice 预设声线 / Base 声音克隆）。"""
from __future__ import annotations

import logging
import os
import shutil
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np

from ai import config as ai_config
from ai.tts.backends.qwen_tts_webui_env import (
    apply_webui_env,
    resolve_model_path,
    webui_python_exe,
)
from ai.tts.text_clean import clean_for_tts

apply_webui_env()

logger = logging.getLogger(__name__)


class QwenTTSEngineError(Exception):
    pass


def _use_webui_daemon() -> bool:
    if os.environ.get("QWEN_TTS_IN_DAEMON") == "1":
        return False
    if not ai_config.QWEN_TTS_USE_WEBUI_PYTHON:
        return False
    return webui_python_exe() is not None


class QwenTTSEngine:
    _instance: QwenTTSEngine | None = None
    _boot_lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._clone_prompt = None
        self._ready = False
        self._infer_lock = threading.Lock()
        self._ref_path: Path | None = None
        self._ref_text: str = ""

    @classmethod
    def get(cls) -> QwenTTSEngine:
        if cls._instance is None:
            with cls._boot_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def ready(self) -> bool:
        return self._ready

    def _mode(self) -> str:
        return (ai_config.QWEN_TTS_MODE or "custom_voice").lower()

    def _load_kwargs(self, model_path: str) -> dict:
        import torch

        if torch.cuda.is_available():
            kwargs: dict = {
                "device_map": "cuda:0",
                "dtype": torch.bfloat16,
                "attn_implementation": "sdpa",
            }
        else:
            kwargs = {"device_map": "cpu", "dtype": torch.float32}
        if Path(model_path).is_dir():
            kwargs["local_files_only"] = True
        return kwargs

    def _ensure_model(self, on_status: Callable[[str], None] | None = None) -> None:
        def _emit(msg: str) -> None:
            if on_status:
                on_status(msg)

        if self._model is not None:
            return
        apply_webui_env()
        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise QwenTTSEngineError(
                "请安装 pip install qwen-tts，或在 config 中配置 qwen_tts.webui_root 使用 WebUI 整合包"
            ) from exc

        import torch

        mode = self._mode()
        model_id = (
            ai_config.QWEN_TTS_CLONE_MODEL_ID if mode == "clone" else ai_config.QWEN_TTS_MODEL_ID
        )
        model_path = resolve_model_path(model_id)
        device_hint = "显卡" if torch.cuda.is_available() else "CPU（会非常慢，建议用独显）"
        local = Path(model_path).is_dir()
        size_hint = "1.7B" if "1.7" in model_id or "1___7" in model_path else "模型"
        _emit(
            f"正在把 Qwen3-TTS {size_hint} 载入{device_hint}"
            f"{'（本地缓存）' if local else ''}，约 1～3 分钟请稍候…"
        )
        logger.info("Loading Qwen3-TTS from %s", model_path)
        self._model = Qwen3TTSModel.from_pretrained(
            model_path, **self._load_kwargs(model_path)
        )
        _emit("Qwen3-TTS 权重已载入，正在准备声线…")

    def _build_clone_prompt(self, ref_path: Path, ref_text: str) -> None:
        x_only = ai_config.QWEN_TTS_X_VECTOR_ONLY
        if not x_only and not ref_text.strip():
            raise QwenTTSEngineError("请填写参考音频里说的文字（prompt_text），或开启 x_vector_only_mode")
        self._clone_prompt = self._model.create_voice_clone_prompt(
            ref_audio=str(ref_path.resolve()),
            ref_text=ref_text if not x_only else None,
            x_vector_only_mode=x_only,
        )
        self._ref_path = ref_path
        self._ref_text = ref_text

    def set_reference(
        self,
        wav_path: str | Path,
        prompt_text: str | None = None,
        *,
        copy_to_project: bool = True,
        on_status: Callable[[str], None] | None = None,
    ) -> Path:
        """用一段新音频现场注册克隆声线（会缓存，后续播报复用）。"""
        if _use_webui_daemon():
            if on_status:
                on_status("正在启动 Qwen TTS（WebUI 环境）…")
            from ai.tts.backends import qwen_tts_daemon_client as daemon

            resp = daemon.request(
                {
                    "cmd": "set_reference",
                    "wav_path": str(Path(wav_path).resolve()),
                    "prompt_text": prompt_text,
                    "copy_to_project": copy_to_project,
                }
            )
            if on_status:
                on_status("声线已注册，后续回复将用这段声音")
            return Path(resp["ref_path"])

        src = Path(wav_path).resolve()
        if not src.is_file():
            raise QwenTTSEngineError(f"音频不存在: {src}")

        dest = ai_config.QWEN_TTS_REFERENCE_WAV
        dest.parent.mkdir(parents=True, exist_ok=True)
        if copy_to_project:
            shutil.copy2(src, dest)
            ref_path = dest
        else:
            ref_path = src

        text = (prompt_text if prompt_text is not None else ai_config.QWEN_TTS_PROMPT_TEXT).strip()
        ai_config.QWEN_TTS_PROMPT_TEXT = text

        def _emit(msg: str) -> None:
            if on_status:
                on_status(msg)

        with self._boot_lock:
            self._ensure_model(on_status)
            if self._mode() != "clone":
                raise QwenTTSEngineError('请先在 config/ai_settings.json 设置 qwen_tts.mode 为 "clone"')
            _emit("正在从你的音频提取声线（约 10～30 秒）…")
            self._build_clone_prompt(ref_path, text)
            self._ready = True
            _emit("声线已注册，后续回复将用这段声音")
        return ref_path

    def warmup(self, on_status: Callable[[str], None] | None = None) -> None:
        if self._ready:
            return

        def _emit(msg: str) -> None:
            if on_status:
                on_status(msg)

        if _use_webui_daemon():
            _emit("正在加载 Qwen3-TTS（WebUI 本地模型）…")
            from ai.tts.backends import qwen_tts_daemon_client as daemon

            daemon.request({"cmd": "warmup"})
            self._ready = True
            _emit("Qwen3-TTS 就绪")
            return

        with self._boot_lock:
            if self._ready:
                return
            self._ensure_model(on_status)
            if self._mode() == "clone":
                ref = ai_config.QWEN_TTS_REFERENCE_WAV
                if not ref.is_file():
                    raise QwenTTSEngineError(
                        f"克隆模式需要参考音频。请点「选择克隆音频」或放入 {ref}"
                    )
                _emit("正在注册克隆声线…")
                self._build_clone_prompt(ref, ai_config.QWEN_TTS_PROMPT_TEXT)
            self._ready = True
            _emit("Qwen3-TTS 就绪")

    def speak(self, text: str, on_status: Callable[[str], None] | None = None) -> tuple[np.ndarray, int]:
        cleaned = clean_for_tts(text)
        if not cleaned:
            raise QwenTTSEngineError("播报文本为空")

        self.warmup(on_status)

        if _use_webui_daemon():
            import tempfile

            import soundfile as sf
            from ai.tts.backends import qwen_tts_daemon_client as daemon

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                out = Path(tmp.name)
            try:
                daemon.request(
                    {"cmd": "speak", "text": cleaned, "output_wav": str(out)}
                )
                audio, sr = sf.read(str(out), dtype="float32")
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
                return audio, int(sr)
            finally:
                out.unlink(missing_ok=True)

        with self._infer_lock:
            if self._mode() == "clone":
                ref = self._ref_path or ai_config.QWEN_TTS_REFERENCE_WAV
                ref_text = ""
                if not ai_config.QWEN_TTS_X_VECTOR_ONLY:
                    ref_text = self._ref_text or ai_config.QWEN_TTS_PROMPT_TEXT
                wavs, sr = self._model.generate_voice_clone(
                    text=cleaned,
                    language=ai_config.QWEN_TTS_LANGUAGE,
                    ref_audio=str(ref.resolve()),
                    ref_text=ref_text,
                    voice_clone_prompt=self._clone_prompt,
                    non_streaming_mode=True,
                )
            else:
                wavs, sr = self._model.generate_custom_voice(
                    text=cleaned,
                    language=ai_config.QWEN_TTS_LANGUAGE,
                    speaker=ai_config.QWEN_TTS_SPEAKER,
                    instruct=ai_config.QWEN_TTS_INSTRUCT or None,
                    non_streaming_mode=True,
                )
        if not wavs:
            raise QwenTTSEngineError("Qwen3-TTS 未返回音频")
        return wavs[0], int(sr)


def warmup(on_status: Callable[[str], None] | None = None) -> None:
    QwenTTSEngine.get().warmup(on_status)


def set_reference(
    wav_path: str | Path,
    prompt_text: str | None = None,
    on_status: Callable[[str], None] | None = None,
) -> Path:
    return QwenTTSEngine.get().set_reference(wav_path, prompt_text, on_status=on_status)
