"""音频录制与播放。"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from ai.config import (
    AUDIO_DEVICES_PATH,
    CHANNELS,
    CONFIG_DIR,
    DTYPE,
    RECORDINGS_DIR,
    SAMPLE_RATE,
    SILENCE_RMS_THRESHOLD,
)

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_recording = False
_stream: sd.InputStream | None = None
_frames: list[np.ndarray] = []
_input_device: int | None = None
_output_device: int | None = None


class AudioIOError(Exception):
    """音频模块业务异常。"""


NO_SPEECH_HINT = (
    "未检测到有效语音（录音几乎为静音）。"
    "若无麦克风，请用: python -m ai.demo_cli session --text \"你的问题\""
)


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
    """计算波形 RMS（float32 单声道）。"""
    samples = _samples_to_float32(audio)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def is_silent_audio(
    audio: np.ndarray,
    threshold: float = SILENCE_RMS_THRESHOLD,
) -> bool:
    return audio_rms(audio) < threshold


def is_silent_wav(
    wav_path: str,
    threshold: float = SILENCE_RMS_THRESHOLD,
) -> bool:
    path = Path(wav_path)
    if not path.is_file():
        return True
    rate, data = wavfile.read(str(path))
    if data.size == 0:
        return True
    return is_silent_audio(data, threshold=threshold)


def _ensure_not_silent(audio: np.ndarray) -> None:
    rms = audio_rms(audio)
    if is_silent_audio(audio):
        raise AudioIOError(f"{NO_SPEECH_HINT}（RMS={rms:.5f}）")


def _new_recording_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"rec_{stamp}_{uuid.uuid4().hex[:8]}.wav"
    return RECORDINGS_DIR / name


def _enumerate_devices(kind: str) -> list[dict]:
    """kind: 'input' | 'output'"""
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
    """列出可用于录音的输入设备（供 CLI / GUI 展示）。"""
    devices = _enumerate_devices("input")
    for d in devices:
        d["max_input_channels"] = d["channels"]
    return devices


def list_output_devices() -> list[dict]:
    """列出可用于播放的输出设备。"""
    devices = _enumerate_devices("output")
    for d in devices:
        d["max_output_channels"] = d["channels"]
    return devices


def get_input_device() -> int | None:
    with _lock:
        return _input_device


def get_output_device() -> int | None:
    with _lock:
        return _output_device


def set_input_device(index: int | None) -> None:
    """None 表示系统默认输入。"""
    global _input_device
    if index is not None:
        _validate_device_index(index, "input")
    with _lock:
        _input_device = index
    save_device_settings()


def set_output_device(index: int | None) -> None:
    global _output_device
    if index is not None:
        _validate_device_index(index, "output")
    with _lock:
        _output_device = index
    save_device_settings()


def _validate_device_index(index: int, kind: str) -> None:
    devices = list_input_devices() if kind == "input" else list_output_devices()
    if not any(d["index"] == index for d in devices):
        raise AudioIOError(f"无效的{'输入' if kind == 'input' else '输出'}设备编号: {index}")


def load_device_settings() -> None:
    global _input_device, _output_device
    path = AUDIO_DEVICES_PATH
    if not path.is_file():
        return
    try:
        import json

        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.warning("读取音频设备配置失败: %s", exc)
        return
    inp = data.get("input_device_index")
    out = data.get("output_device_index")
    with _lock:
        _input_device = None
        _output_device = None
        if inp is not None:
            try:
                idx = int(inp)
                _validate_device_index(idx, "input")
                _input_device = idx
            except (AudioIOError, TypeError, ValueError) as exc:
                logger.warning("输入设备配置无效，使用系统默认: %s", exc)
        if out is not None:
            try:
                idx = int(out)
                _validate_device_index(idx, "output")
                _output_device = idx
            except (AudioIOError, TypeError, ValueError) as exc:
                logger.warning("输出设备配置无效，使用系统默认: %s", exc)


def save_device_settings() -> None:
    import json

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "input_device_index": get_input_device(),
        "output_device_index": get_output_device(),
    }
    with AUDIO_DEVICES_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def device_combo_label(dev: dict) -> str:
    mark = " ★" if dev.get("is_default") else ""
    return f"[{dev['index']}] {dev['name']}{mark}"


def format_devices_text(devices: list[dict] | None = None) -> str:
    """将输入设备格式化为可读文本。"""
    devices = devices if devices is not None else list_input_devices()
    if not devices:
        return "未找到可用的录音输入设备。请在系统「声音 → 输入」中检查麦克风。"

    lines = ["可用录音设备（录音模块使用系统默认输入）：", ""]
    for d in devices:
        mark = " [默认]" if d.get("is_default") else ""
        rate = d.get("default_samplerate")
        rate_s = f", {int(rate)} Hz" if rate else ""
        lines.append(
            f"  [{d['index']}] {d['name']} "
            f"(输入声道: {d['max_input_channels']}{rate_s}){mark}"
        )
    lines.append("")
    lines.append("也可在小音 GUI 顶栏下方选择「麦克风 / 播放设备」。")
    return "\n".join(lines)


def _check_input_device() -> None:
    try:
        devices = list_input_devices()
        if not devices:
            raise AudioIOError(
                "未检测到可用麦克风，请检查系统录音设备与权限。"
            )
    except AudioIOError:
        raise
    except Exception as exc:
        raise AudioIOError(
            "未检测到可用麦克风，请检查系统录音设备与权限。"
        ) from exc


def is_recording() -> bool:
    with _lock:
        return _recording


def _check_input_settings(device: int | None) -> None:
    try:
        sd.check_input_settings(
            device=device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
        )
    except Exception as exc:
        raise AudioIOError(
            f"当前麦克风不支持 {SAMPLE_RATE}Hz 单声道录音，请换一个设备或选「系统默认」: {exc}"
        ) from exc


def start_recording() -> None:
    """开始录音（需调用 stop_recording 结束）。勿在 GUI 主线程直接调用。"""
    global _recording, _stream, _frames

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

    stream: sd.InputStream | None = None
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

    with _lock:
        if not _recording:
            raise AudioIOError("当前未在录音，请先调用 start_recording()。")

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

    _ensure_not_silent(audio)

    out_path = _new_recording_path()
    wavfile.write(str(out_path), SAMPLE_RATE, audio)
    logger.info("录音已保存: %s (%.2fs)", out_path, len(audio) / SAMPLE_RATE)
    return str(out_path.resolve())


def record_for_seconds(seconds: float) -> str:
    """录制固定时长并保存，返回 wav 绝对路径。"""
    if seconds <= 0:
        raise AudioIOError("录音时长必须大于 0。")

    _check_input_device()
    logger.info("固定时长录音 %.1f 秒…", seconds)
    try:
        audio = sd.rec(
            int(seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            device=get_input_device(),
        )
        sd.wait()
    except Exception as exc:
        raise AudioIOError(f"录音失败: {exc}") from exc

    if audio is None or len(audio) == 0:
        raise AudioIOError("未采集到音频数据。")

    if audio.ndim > 1:
        audio = audio[:, 0]

    _ensure_not_silent(audio)

    out_path = _new_recording_path()
    wavfile.write(str(out_path), SAMPLE_RATE, audio)
    return str(out_path.resolve())


def play_wav(wav_path: str) -> None:
    """播放 wav 文件（阻塞直到播放结束）。"""
    path = Path(wav_path)
    if not path.is_file():
        raise AudioIOError(f"音频文件不存在: {wav_path}")

    rate, data = wavfile.read(str(path))
    if data.size == 0:
        raise AudioIOError("音频文件为空。")

    if data.dtype != np.float32:
        if np.issubdtype(data.dtype, np.integer):
            max_val = np.iinfo(data.dtype).max
            samples = data.astype(np.float32) / max_val
        else:
            samples = data.astype(np.float32)
    else:
        samples = data

    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    try:
        sd.play(samples, rate, device=get_output_device())
        sd.wait()
    except Exception as exc:
        raise AudioIOError(f"播放失败: {exc}") from exc

    logger.info(
        "播放完成: %s (device=%s)",
        path,
        get_output_device() if get_output_device() is not None else "default",
    )


load_device_settings()
