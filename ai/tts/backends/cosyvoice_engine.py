"""CosyVoice 常驻引擎：模型只加载一次，声线特征缓存复用。"""
from __future__ import annotations

import json
import logging
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from ai.config import (
    COSYVOICE_MODEL_DIR,
    COSYVOICE_PROMPT_TEXT,
    COSYVOICE_REFERENCE_WAV,
    COSYVOICE_ROOT,
    VOICE_REF_DIR,
)
from ai.tts.text_clean import clean_for_tts

logger = logging.getLogger(__name__)

SPEAKER_ID = "xiaoyin"
_SPK_CACHE = VOICE_REF_DIR / f"spk_{SPEAKER_ID}.pt"
_SPK_META = VOICE_REF_DIR / f"spk_{SPEAKER_ID}.meta.json"


class CosyVoiceEngineError(Exception):
    pass


class CosyVoiceEngine:
    _instance: CosyVoiceEngine | None = None
    _boot_lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._sample_rate = 24000
        self._ready = False
        self._infer_lock = threading.Lock()

    @classmethod
    def get(cls) -> CosyVoiceEngine:
        if cls._instance is None:
            with cls._boot_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def ready(self) -> bool:
        return self._ready

    def _meta_current(self) -> dict:
        ref = COSYVOICE_REFERENCE_WAV
        return {
            "prompt_text": COSYVOICE_PROMPT_TEXT,
            "ref_mtime": ref.stat().st_mtime if ref.is_file() else 0,
            "ref_size": ref.stat().st_size if ref.is_file() else 0,
        }

    def _meta_matches(self) -> bool:
        if not _SPK_META.is_file() or not _SPK_CACHE.is_file():
            return False
        try:
            saved = json.loads(_SPK_META.read_text(encoding="utf-8"))
            return saved == self._meta_current()
        except Exception:
            return False

    def _save_spk_cache(self) -> None:
        import torch

        VOICE_REF_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.frontend.spk2info[SPEAKER_ID], _SPK_CACHE)
        _SPK_META.write_text(json.dumps(self._meta_current(), ensure_ascii=False), encoding="utf-8")
        logger.info("声线缓存已保存: %s", _SPK_CACHE)

    def _load_spk_cache(self) -> bool:
        import torch

        if not self._meta_matches():
            return False
        try:
            self._model.frontend.spk2info[SPEAKER_ID] = torch.load(
                _SPK_CACHE, map_location=self._model.frontend.device, weights_only=False
            )
            logger.info("已加载声线缓存: %s", _SPK_CACHE)
            return True
        except Exception as exc:
            logger.warning("加载声线缓存失败: %s", exc)
            return False

    def _register_speaker(self) -> None:
        if not COSYVOICE_REFERENCE_WAV.is_file():
            raise CosyVoiceEngineError(f"参考音频不存在: {COSYVOICE_REFERENCE_WAV}")
        self._model.add_zero_shot_spk(
            COSYVOICE_PROMPT_TEXT,
            str(COSYVOICE_REFERENCE_WAV),
            SPEAKER_ID,
        )
        self._save_spk_cache()

    def warmup(self, on_status: Callable[[str], None] | None = None) -> None:
        if self._ready:
            return

        def _emit(msg: str) -> None:
            if on_status:
                on_status(msg)

        with self._boot_lock:
            if self._ready:
                return

            model_path = COSYVOICE_ROOT / COSYVOICE_MODEL_DIR
            if not model_path.is_dir():
                raise CosyVoiceEngineError(f"模型目录不存在: {model_path}")

            _emit("正在加载 CosyVoice 模型（仅首次较慢）…")
            root = COSYVOICE_ROOT.resolve()
            sys.path.insert(0, str(root))
            sys.path.insert(0, str(root / "third_party" / "Matcha-TTS"))

            import torch
            import torchaudio  # noqa: F401
            from cosyvoice.cli.cosyvoice import AutoModel

            self._model = AutoModel(model_dir=str(model_path), fp16=False)
            if not torch.cuda.is_available():
                self._model.model.llm.float()
                self._model.model.flow.float()
                self._model.model.hift.float()
            self._sample_rate = self._model.sample_rate

            _emit("正在加载/注册女友声线（参考音频只处理一次）…")
            if not self._load_spk_cache():
                self._register_speaker()

            self._ready = True
            _emit("CosyVoice 就绪（声线已缓存）")

    def speak(self, text: str, on_status: Callable[[str], None] | None = None) -> Path:
        import tempfile
        import torchaudio

        cleaned = clean_for_tts(text)
        if not cleaned:
            raise CosyVoiceEngineError("播报文本为空")

        def _emit(msg: str) -> None:
            if on_status:
                on_status(msg)

        self.warmup(on_status)
        _emit("正在合成语音…")

        with self._infer_lock:
            out_path = Path(tempfile.mkstemp(suffix=".wav")[1])
            for _, output in enumerate(
                self._model.inference_zero_shot(
                    cleaned,
                    COSYVOICE_PROMPT_TEXT,
                    str(COSYVOICE_REFERENCE_WAV),
                    zero_shot_spk_id=SPEAKER_ID,
                    text_frontend=True,
                )
            ):
                torchaudio.save(str(out_path), output["tts_speech"], self._sample_rate)
                break

        if not out_path.is_file() or out_path.stat().st_size == 0:
            raise CosyVoiceEngineError("未生成有效音频")
        return out_path

    def shutdown(self) -> None:
        self._model = None
        self._ready = False


def warmup(on_status: Callable[[str], None] | None = None) -> None:
    CosyVoiceEngine.get().warmup(on_status)
