"""Whisper 语音识别（语音 → 文字）。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile
from scipy import signal

from ai.audio_io import NO_SPEECH_HINT, is_silent_audio
from ai.config import (
    MODELS_DIR,
    SAMPLE_RATE,
    WHISPER_LANGUAGE,
    WHISPER_MODEL_NAME,
    WHISPER_NO_SPEECH_PROB_THRESHOLD,
)

logger = logging.getLogger(__name__)

_model: Any = None
_model_name: str | None = None


class SpeechToTextError(Exception):
    """语音识别业务异常。"""


def preload_whisper(model_name: str = WHISPER_MODEL_NAME) -> None:
    """预加载 Whisper 模型（建议在应用启动或后台线程调用）。"""
    _load_model(model_name)


def _load_model(model_name: str) -> Any:
    global _model, _model_name

    if _model is not None and _model_name == model_name:
        return _model

    try:
        import whisper
    except ImportError as exc:
        raise SpeechToTextError(
            "未安装 openai-whisper，请执行: pip install openai-whisper torch"
        ) from exc

    logger.info("正在加载 Whisper 模型 '%s'（首次可能需下载）…", model_name)
    try:
        _model = whisper.load_model(model_name)#, download_root=str(MODELS_DIR)
        _model_name = model_name
    except Exception as exc:
        raise SpeechToTextError(f"加载 Whisper 模型失败: {exc}") from exc

    logger.info("Whisper 模型 '%s' 已就绪", model_name)
    return _model


def _load_wav_as_float32(path: Path) -> np.ndarray:
    """读取 wav 为 16kHz 单声道 float32（不依赖 ffmpeg）。"""
    rate, data = wavfile.read(str(path))
    if data.size == 0:
        raise SpeechToTextError("音频文件为空。")

    if np.issubdtype(data.dtype, np.integer):
        max_val = np.iinfo(data.dtype).max
        audio = data.astype(np.float32) / max_val
    else:
        audio = data.astype(np.float32)

    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if rate != SAMPLE_RATE:
        num_samples = int(round(len(audio) * SAMPLE_RATE / rate))
        audio = signal.resample(audio, num_samples).astype(np.float32)

    return audio


def transcribe(
    wav_path: str,
    language: str = WHISPER_LANGUAGE,
    model_name: str = WHISPER_MODEL_NAME,
) -> str:
    """将 wav 转为文本。"""
    path = Path(wav_path)
    if not path.is_file():
        raise SpeechToTextError(f"音频文件不存在: {wav_path}")

    model = _load_model(model_name)

    logger.info("开始识别: %s", path.name)
    try:
        audio = _load_wav_as_float32(path)
        if is_silent_audio(audio):
            raise SpeechToTextError(NO_SPEECH_HINT)

        result = model.transcribe(
            audio,
            language=language,
            fp16=False,
        )
    except SpeechToTextError:
        raise
    except Exception as exc:
        raise SpeechToTextError(f"语音识别失败: {exc}") from exc

    segments = result.get("segments") or []
    if segments:
        probs = [float(s.get("no_speech_prob", 0.0)) for s in segments]
        avg_no_speech = sum(probs) / len(probs)
        if avg_no_speech >= WHISPER_NO_SPEECH_PROB_THRESHOLD:
            raise SpeechToTextError(
                f"{NO_SPEECH_HINT}（Whisper 判定无语音，no_speech_prob={avg_no_speech:.2f}）"
            )

    text = (result.get("text") or "").strip()
    if not text:
        raise SpeechToTextError("识别结果为空，请检查录音是否清晰。")

    logger.info("识别完成: %s", text[:80] + ("…" if len(text) > 80 else ""))
    return text
