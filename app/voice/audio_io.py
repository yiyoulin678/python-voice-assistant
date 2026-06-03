"""麦克风录音（适配 Whisper，wav 经 scipy 读写）。"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from app.voice.stt_settings import (
    CHANNELS,
    DTYPE,
    MIN_RECORDING_SECONDS,
    NO_SPEECH_HINT,
    SAMPLE_RATE,
    SILENCE_PEAK_THRESHOLD,
    SILENCE_RMS_THRESHOLD,
    STTSettings,
)

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_recording = False
_stream = None
_frames: list[np.ndarray] = []
_input_device: int | None = None
_paths_configured = False
_recordings_dir = Path("data/recordings")
_audio_devices_path = Path("data/config/audio_devices.json")


class AudioIOError(Exception):
    """音频模块业务异常。"""


def configure_audio_paths(settings: STTSettings, base_dir: Path) -> None:
    global _paths_configured, _recordings_dir, _audio_devices_path, _input_device
    _recordings_dir = settings.recordings_dir(base_dir)
    _audio_devices_path = settings.audio_devices_path(base_dir)
    _recordings_dir.mkdir(parents=True, exist_ok=True)
    _audio_devices_path.parent.mkdir(parents=True, exist_ok=True)
    _input_device = settings.input_device_index
    _paths_configured = True
    _save_device_settings_file()


def _ensure_configured() -> None:
    if not _paths_configured:
        raise AudioIOError("音频路径未初始化，请先调用 configure_audio_paths()。")


def _samples_to_float32(data: np.ndarray) -> np.ndarray:
    if np.issubdtype(data.dtype, np.integer):
        max_val = np.iinfo(data.dtype).max
        audio = data.astype(np.float32) / max_val
    else:
        audio = data.astype(np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio


def audio_rms(audio: np.ndarray) -> float:
    samples = _samples_to_float32(audio)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def audio_peak(audio: np.ndarray) -> float:
    samples = _samples_to_float32(audio)
    if samples.size == 0:
        return 0.0
    return float(np.max(np.abs(samples)))


def is_silent_audio(
    audio: np.ndarray,
    threshold: float = SILENCE_RMS_THRESHOLD,
    peak_threshold: float = SILENCE_PEAK_THRESHOLD,
) -> bool:
    peak = audio_peak(audio)
    if peak >= peak_threshold:
        return False
    return audio_rms(audio) < threshold


def describe_audio_levels(audio: np.ndarray, *, duration_seconds: float | None = None) -> str:
    parts = [
        f"RMS={audio_rms(audio):.5f}",
        f"峰值={audio_peak(audio):.5f}",
    ]
    if duration_seconds is not None:
        parts.insert(0, f"时长={duration_seconds:.2f}s")
    device = get_input_device()
    if device is None:
        parts.append("设备=系统默认")
    else:
        try:
            import sounddevice as sd

            name = sd.query_devices(device, "input").get("name", str(device))
            parts.append(f"设备=[{device}] {name}")
        except Exception:
            parts.append(f"设备=[{device}]")
    return "，".join(parts)


def _ensure_not_silent(audio: np.ndarray, *, duration_seconds: float | None = None) -> None:
    if is_silent_audio(audio):
        raise AudioIOError(
            f"{NO_SPEECH_HINT}（{describe_audio_levels(audio, duration_seconds=duration_seconds)}）"
        )


def _new_recording_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"rec_{stamp}_{uuid.uuid4().hex[:8]}.wav"
    return _recordings_dir / name


def _enumerate_devices(kind: str) -> list[dict]:
    import sounddevice as sd

    try:
        all_devices = sd.query_devices()
        default_in, default_out = sd.default.device
    except Exception as exc:
        raise AudioIOError(f"查询音频设备失败: {exc}") from exc

    result: list[dict] = []
    for index, dev in enumerate(all_devices):
        if kind == "input":
            channels = int(dev.get("max_input_channels", 0))
            is_default = index == default_in
        else:
            channels = int(dev.get("max_output_channels", 0))
            is_default = index == default_out
        if channels < 1:
            continue
        result.append(
            {
                "index": index,
                "name": dev.get("name", "Unknown"),
                "channels": channels,
                "default_samplerate": dev.get("default_samplerate"),
                "is_default": is_default,
            }
        )
    return result


def list_input_devices() -> list[dict]:
    devices = _enumerate_devices("input")
    for device in devices:
        device["max_input_channels"] = device["channels"]
    return devices


def device_combo_label(device: dict) -> str:
    mark = " ★" if device.get("is_default") else ""
    return f"[{device['index']}] {device['name']}{mark}"


def get_input_device() -> int | None:
    with _lock:
        return _input_device


def set_input_device(index: int | None) -> None:
    global _input_device
    if index is not None:
        _validate_device_index(index, "input")
    with _lock:
        _input_device = index
    _save_device_settings_file()


def _validate_device_index(index: int, kind: str) -> None:
    devices = list_input_devices()
    if not any(device["index"] == index for device in devices):
        raise AudioIOError(f"无效的输入设备编号: {index}")


def _load_device_settings_file() -> None:
    global _input_device
    path = _audio_devices_path
    if not path.is_file():
        return
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        logger.warning("读取音频设备配置失败: %s", exc)
        return
    raw = data.get("input_device_index")
    if raw is None:
        return
    try:
        index = int(raw)
        _validate_device_index(index, "input")
        with _lock:
            _input_device = index
    except (AudioIOError, TypeError, ValueError) as exc:
        logger.warning("输入设备配置无效，使用系统默认: %s", exc)


def _save_device_settings_file() -> None:
    data = {"input_device_index": get_input_device()}
    with _audio_devices_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def _check_input_device() -> None:
    try:
        if not list_input_devices():
            raise AudioIOError("未检测到可用麦克风，请检查系统录音设备与权限。")
    except AudioIOError:
        raise
    except Exception as exc:
        raise AudioIOError("未检测到可用麦克风，请检查系统录音设备与权限。") from exc


def is_recording() -> bool:
    with _lock:
        return _recording


def _check_input_settings(device: int | None) -> None:
    import sounddevice as sd

    try:
        sd.check_input_settings(
            device=device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
        )
    except Exception as exc:
        raise AudioIOError(
            f"当前麦克风不支持 {SAMPLE_RATE}Hz 单声道录音: {exc}"
        ) from exc


def start_recording() -> None:
    """开始录音（勿在 GUI 主线程调用）。"""
    import sounddevice as sd

    global _recording, _stream, _frames

    _ensure_configured()
    _check_input_device()
    device = get_input_device()
    _check_input_settings(device)

    with _lock:
        if _recording:
            raise AudioIOError("已在录音中，请先停止当前录音。")
        _frames = []
        _recording = True

    def callback(indata, _frames_count, _time_info, status):
        if status:
            logger.warning("录音流状态: %s", status)
        with _lock:
            if _recording:
                _frames.append(indata.copy())

    stream = None
    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            device=device,
            callback=callback,
        )
        stream.start()
    except Exception as exc:
        with _lock:
            _recording = False
            _stream = None
            _frames = []
        raise AudioIOError(f"启动录音失败: {exc}") from exc

    with _lock:
        _stream = stream

    logger.info(
        "开始录音 @ %s Hz device=%s",
        SAMPLE_RATE,
        device if device is not None else "default",
    )


def stop_recording() -> str:
    """停止录音并保存 wav，返回绝对路径。"""
    global _recording, _stream, _frames

    _ensure_configured()
    with _lock:
        if not _recording:
            raise AudioIOError("当前未在录音，请先开始录音。")
        _recording = False
        stream = _stream
        chunks = _frames
        _stream = None
        _frames = []

    if stream is not None:
        try:
            stream.stop()
            stream.close()
        except Exception as exc:
            logger.warning("关闭录音流时出错: %s", exc)

    if not chunks:
        raise AudioIOError("未采集到音频数据，请检查麦克风是否静音。")

    audio = np.concatenate(chunks, axis=0)
    if audio.ndim > 1:
        audio = audio[:, 0]

    duration_seconds = len(audio) / SAMPLE_RATE
    if duration_seconds < MIN_RECORDING_SECONDS:
        raise AudioIOError(
            f"录音太短（{duration_seconds:.2f}s），请至少录 {MIN_RECORDING_SECONDS:.1f} 秒并清楚说话。"
            f"（{describe_audio_levels(audio, duration_seconds=duration_seconds)}）"
        )

    _ensure_not_silent(audio, duration_seconds=duration_seconds)

    out_path = _new_recording_path()
    wavfile.write(str(out_path), SAMPLE_RATE, audio)
    logger.info(
        "录音已保存: %s (%.2fs, %s)",
        out_path,
        duration_seconds,
        describe_audio_levels(audio, duration_seconds=duration_seconds),
    )
    return str(out_path.resolve())
