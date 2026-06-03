"""Whisper 语音识别（语音 → 文字）。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal
from scipy.io import wavfile

from app.voice.audio_io import describe_audio_levels, is_silent_audio
from app.voice.stt_settings import (
    DEFAULT_WHISPER_LANGUAGE,
    DEFAULT_WHISPER_MODEL_NAME,
    NO_SPEECH_HINT,
    SAMPLE_RATE,
    WHISPER_NO_SPEECH_PROB_THRESHOLD,
    STTSettings,
)

logger = logging.getLogger(__name__)

_model: Any = None
_model_name: str | None = None
_models_dir: Path | None = None


class SpeechToTextError(Exception):
    """语音识别业务异常。"""


def configure_whisper_cache(base_dir: Path, settings: STTSettings) -> None:
    global _models_dir
    cache_dir = settings.models_dir(base_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    _models_dir = cache_dir


def preload_whisper(model_name: str = DEFAULT_WHISPER_MODEL_NAME) -> None:
    _load_model(model_name)


def _load_model(model_name: str) -> Any:
    global _model, _model_name

    if _model is not None and _model_name == model_name:
        return _model

    try:
        import whisper
    except ImportError as exc:
        raise SpeechToTextError(
            "未安装语音识别依赖，请执行: pip install -r requirements-stt.txt"
        ) from exc

    logger.info("正在加载 Whisper 模型 '%s'（首次可能需下载）…", model_name)
    download_root = str(_models_dir) if _models_dir is not None else None
    try:
        if download_root:
            _model = whisper.load_model(model_name, download_root=download_root)
        else:
            _model = whisper.load_model(model_name)
        _model_name = model_name
    except Exception as exc:
        raise SpeechToTextError(f"加载 Whisper 模型失败: {exc}") from exc

    logger.info("Whisper 模型 '%s' 已就绪", model_name)
    return _model


def _load_wav_as_float32(path: Path) -> np.ndarray:
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


def normalize_recording_levels(audio: np.ndarray, target_peak: float = 0.85) -> np.ndarray:
    """抬高过小音量，避免实体麦在系统低增益时被误判为静音。"""
    if np.issubdtype(audio.dtype, np.integer):
        max_val = np.iinfo(audio.dtype).max
        samples = audio.astype(np.float32) / max_val
    else:
        samples = audio.astype(np.float32)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak < 1e-6:
        return samples
    if peak < 0.2:
        gain = min(target_peak / peak, 40.0)
        samples = np.clip(samples * gain, -1.0, 1.0)
    return samples.astype(np.float32)


def transcribe(
    wav_path: str,
    *,
    language: str = DEFAULT_WHISPER_LANGUAGE,
    model_name: str = DEFAULT_WHISPER_MODEL_NAME,
) -> str:
    path = Path(wav_path)
    if not path.is_file():
        raise SpeechToTextError(f"音频文件不存在: {wav_path}")

    model = _load_model(model_name)

    logger.info("开始识别: %s", path.name)
    try:
        audio = _load_wav_as_float32(path)
        duration_seconds = len(audio) / SAMPLE_RATE
        if is_silent_audio(audio):
            raise SpeechToTextError(
                f"{NO_SPEECH_HINT}（{describe_audio_levels(audio, duration_seconds=duration_seconds)}）"
            )

        audio = normalize_recording_levels(audio)
        result = model.transcribe(audio, language=language, fp16=False)
    except SpeechToTextError:
        raise
    except Exception as exc:
        raise SpeechToTextError(f"语音识别失败: {exc}") from exc

    text = (result.get("text") or "").strip()
    segments = result.get("segments") or []
    if not text and segments:
        probs = [float(segment.get("no_speech_prob", 0.0)) for segment in segments]
        avg_no_speech = sum(probs) / len(probs)
        if avg_no_speech >= WHISPER_NO_SPEECH_PROB_THRESHOLD:
            raise SpeechToTextError(
                f"{NO_SPEECH_HINT}（Whisper 判定无语音，no_speech_prob={avg_no_speech:.2f}，"
                f"{describe_audio_levels(audio, duration_seconds=duration_seconds)}）"
            )

    if not text:
        raise SpeechToTextError(
            "识别结果为空，请检查录音是否清晰。"
            f"（{describe_audio_levels(audio, duration_seconds=duration_seconds)}）"
        )

    logger.info("识别完成: %s", text[:80] + ("…" if len(text) > 80 else ""))
    return text
