"""VoxCPM 常驻引擎（声音设计 / 可控克隆）。"""
from __future__ import annotations

import logging
import shutil
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np

from ai import config as ai_config
from ai.tts.text_clean import clean_for_tts

logger = logging.getLogger(__name__)


class VoxCPMEngineError(Exception):
    pass


class VoxCPMEngine:
    _instance: VoxCPMEngine | None = None
    _boot_lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._ready = False
        self._infer_lock = threading.Lock()

    @classmethod
    def get(cls) -> VoxCPMEngine:
        if cls._instance is None:
            with cls._boot_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def ready(self) -> bool:
        return self._ready

    def _model_path(self) -> str:
        local = ai_config.VOXCPM_LOCAL_MODEL_DIR
        if local and Path(local).is_dir():
            return str(Path(local).resolve())
        return ai_config.VOXCPM_MODEL_ID

    def _is_voxcpm2(self) -> bool:
        mid = self._model_path().lower().replace("-", "").replace("_", "")
        return "voxcpm2" in mid

    def _ensure_model(self, on_status: Callable[[str], None] | None = None) -> None:
        def _emit(msg: str) -> None:
            if on_status:
                on_status(msg)

        if self._model is not None:
            return
        try:
            from voxcpm import VoxCPM
        except ImportError as exc:
            repo = ai_config.VOXCPM_REPO_ROOT
            hint = f"请执行: powershell -File scripts/install_voxcpm.ps1（或 pip install -e {repo}）"
            raise VoxCPMEngineError(hint) from exc

        path = self._model_path()
        _emit(f"正在加载 VoxCPM（{Path(path).name if Path(path).is_dir() else path}，首次需下载）…")
        logger.info("Loading VoxCPM from %s", path)
        load_kw: dict = {
            "load_denoiser": ai_config.VOXCPM_LOAD_DENOISER,
        }
        try:
            import torch

            if torch.cuda.is_available():
                load_kw["device"] = "cuda"
        except ImportError:
            pass
        self._model = VoxCPM.from_pretrained(path, **load_kw)
        _emit("VoxCPM 模型已载入")

    def _build_text(self, cleaned: str) -> str:
        mode = (ai_config.VOXCPM_MODE or "clone").lower()
        prefix = (ai_config.VOXCPM_VOICE_DESIGN_PREFIX or "").strip()
        style = (ai_config.VOXCPM_STYLE_CONTROL or "").strip()

        text = cleaned
        if mode == "design" and prefix and not text.lstrip().startswith("("):
            text = f"({prefix}){text.lstrip()}"
        elif style and mode == "clone":
            text = f"({style}){text.lstrip()}"
        return text

    def _default_prompt_text(self) -> str:
        return (ai_config.VOXCPM_PROMPT_TEXT or ai_config.COSYVOICE_PROMPT_TEXT or "").strip()

    def _generate_kwargs(self, cleaned: str) -> dict:
        kwargs: dict = {
            "text": self._build_text(cleaned),
            "cfg_value": ai_config.VOXCPM_CFG_VALUE,
            "inference_timesteps": ai_config.VOXCPM_INFERENCE_TIMESTEPS,
            "retry_badcase": ai_config.VOXCPM_RETRY_BADCASE,
            "max_len": ai_config.VOXCPM_MAX_LEN,
        }
        if ai_config.VOXCPM_RETRY_BADCASE:
            kwargs["retry_badcase_max_times"] = ai_config.VOXCPM_RETRY_BADCASE_MAX_TIMES
            kwargs["retry_badcase_ratio_threshold"] = ai_config.VOXCPM_RETRY_BADCASE_RATIO_THRESHOLD
        mode = (ai_config.VOXCPM_MODE or "clone").lower()
        ref = ai_config.VOXCPM_REFERENCE_WAV

        if mode != "clone" or not ref.is_file():
            return kwargs

        ref_s = str(ref.resolve())
        if self._is_voxcpm2():
            if ai_config.VOXCPM_X_VECTOR_ONLY:
                kwargs["reference_wav_path"] = ref_s
                return kwargs
            prompt = self._default_prompt_text()
            kwargs["prompt_wav_path"] = ref_s
            kwargs["reference_wav_path"] = ref_s
            if prompt:
                kwargs["prompt_text"] = prompt
            return kwargs

        # VoxCPM 1.x 仅支持 prompt 续写克隆，不支持 reference_wav_path
        prompt = self._default_prompt_text()
        if not prompt:
            logger.warning("VoxCPM1.5 克隆需 prompt_text，当前无参考台词，退化为纯文本合成")
            return kwargs
        kwargs["prompt_wav_path"] = ref_s
        kwargs["prompt_text"] = prompt
        return kwargs

    def set_reference(
        self,
        wav_path: str | Path,
        prompt_text: str | None = None,
        *,
        on_status: Callable[[str], None] | None = None,
    ) -> Path:
        src = Path(wav_path).resolve()
        if not src.is_file():
            raise VoxCPMEngineError(f"音频不存在: {src}")

        dest = ai_config.VOXCPM_REFERENCE_WAV
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if prompt_text is not None:
            ai_config.VOXCPM_PROMPT_TEXT = prompt_text.strip()

        def _emit(msg: str) -> None:
            if on_status:
                on_status(msg)

        _emit("参考音频已保存，后续播报将用 VoxCPM 克隆")
        return dest

    def warmup(self, on_status: Callable[[str], None] | None = None) -> None:
        if self._ready:
            return
        with self._boot_lock:
            if self._ready:
                return
            self._ensure_model(on_status)
            mode = (ai_config.VOXCPM_MODE or "clone").lower()
            ref = ai_config.VOXCPM_REFERENCE_WAV
            if mode == "clone" and not ref.is_file():
                raise VoxCPMEngineError(
                    f"克隆模式需要参考音频。请点「选择克隆音频」或放入 {ref}"
                )
            self._ready = True

    def speak(self, text: str, on_status: Callable[[str], None] | None = None) -> tuple[np.ndarray, int]:
        cleaned = clean_for_tts(text, max_len=ai_config.VOXCPM_TTS_MAX_CHARS)
        if not cleaned:
            raise VoxCPMEngineError("播报文本为空")

        self.warmup(on_status)

        with self._infer_lock:
            kwargs = self._generate_kwargs(cleaned)
            logger.debug("VoxCPM generate: %s", {k: v for k, v in kwargs.items() if k != "text"})
            wav = self._model.generate(**kwargs)

        if wav is None or (hasattr(wav, "size") and wav.size == 0):
            raise VoxCPMEngineError("VoxCPM 未返回音频")

        audio = np.asarray(wav, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        sr = int(getattr(self._model.tts_model, "sample_rate", 44100))
        return audio, sr


def warmup(on_status: Callable[[str], None] | None = None) -> None:
    VoxCPMEngine.get().warmup(on_status)


def set_reference(
    wav_path: str | Path,
    prompt_text: str | None = None,
    on_status: Callable[[str], None] | None = None,
) -> Path:
    return VoxCPMEngine.get().set_reference(wav_path, prompt_text, on_status=on_status)
