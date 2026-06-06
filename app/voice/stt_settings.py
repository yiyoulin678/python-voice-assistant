from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Whisper 友好采样率
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
# 物理麦克风在 Windows 低增益时 RMS 常低于 0.008，需结合峰值判断。
SILENCE_RMS_THRESHOLD = 0.0015
SILENCE_PEAK_THRESHOLD = 0.006
MIN_RECORDING_SECONDS = 0.45
VOICE_CALL_SILENCE_SECONDS = 0.75
VOICE_CALL_MIN_UTTERANCE_SECONDS = 0.35
VOICE_CALL_MAX_UTTERANCE_SECONDS = 45.0
VOICE_CALL_SPEECH_RMS_THRESHOLD = 0.006
VOICE_CALL_SPEECH_PEAK_THRESHOLD = 0.01
WHISPER_NO_SPEECH_PROB_THRESHOLD = 0.72
DEFAULT_WHISPER_MODEL_NAME = "base"
DEFAULT_WHISPER_LANGUAGE = "zh"

NO_SPEECH_HINT = (
    "未检测到有效语音（录音几乎为静音）。"
    "请在 Windows「设置 → 系统 → 声音 → 输入」中调高麦克风音量并试录，"
    "或在 Mutsuki 设置 → 语音输入 中换一个麦克风（建议选带 ★ 的默认设备或你的实体麦），"
    "录音时至少说 1～2 秒。"
)


@dataclass(frozen=True)
class STTSettings:
    enabled: bool = True
    model_name: str = DEFAULT_WHISPER_MODEL_NAME
    language: str = DEFAULT_WHISPER_LANGUAGE
    input_device_index: int | None = None
    voice_call_enabled: bool = True
    voice_call_silence_seconds: float = VOICE_CALL_SILENCE_SECONDS
    voice_call_interrupt_tts: bool = True

    def recordings_dir(self, base_dir: Path) -> Path:
        return base_dir / "data" / "recordings"

    def audio_devices_path(self, base_dir: Path) -> Path:
        return base_dir / "data" / "config" / "audio_devices.json"

    def models_dir(self, base_dir: Path) -> Path:
        return base_dir / "data" / "models" / "whisper"
