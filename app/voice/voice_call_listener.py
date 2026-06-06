"""VAD 连续听音：检测一句话结束并提交识别（语音通话模式）。"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Signal
from scipy.io import wavfile

from app.voice.audio_io import audio_peak, audio_rms, get_input_device
from app.voice.stt_settings import (
    CHANNELS,
    DTYPE,
    SAMPLE_RATE,
    STTSettings,
    VOICE_CALL_MAX_UTTERANCE_SECONDS,
    VOICE_CALL_MIN_UTTERANCE_SECONDS,
    VOICE_CALL_SILENCE_SECONDS,
    VOICE_CALL_SPEECH_PEAK_THRESHOLD,
    VOICE_CALL_SPEECH_RMS_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceCallConfig:
    silence_seconds: float
    min_utterance_seconds: float
    max_utterance_seconds: float
    speech_rms_threshold: float
    speech_peak_threshold: float
    interrupt_tts: bool

    @classmethod
    def from_stt_settings(cls, settings: STTSettings) -> "VoiceCallConfig":
        try:
            silence = float(settings.voice_call_silence_seconds)
        except (TypeError, ValueError):
            silence = VOICE_CALL_SILENCE_SECONDS
        silence = max(0.35, min(2.0, silence))
        return cls(
            silence_seconds=silence,
            min_utterance_seconds=VOICE_CALL_MIN_UTTERANCE_SECONDS,
            max_utterance_seconds=VOICE_CALL_MAX_UTTERANCE_SECONDS,
            speech_rms_threshold=VOICE_CALL_SPEECH_RMS_THRESHOLD,
            speech_peak_threshold=VOICE_CALL_SPEECH_PEAK_THRESHOLD,
            interrupt_tts=bool(settings.voice_call_interrupt_tts),
        )


def is_speech_block(
    block: np.ndarray,
    *,
    rms_threshold: float,
    peak_threshold: float,
) -> bool:
    if block.size == 0:
        return False
    peak = audio_peak(block)
    if peak >= peak_threshold:
        return True
    return audio_rms(block) >= rms_threshold


def should_finalize_utterance(
    *,
    speech_seconds: float,
    silence_seconds: float,
    config: VoiceCallConfig,
) -> bool:
    if speech_seconds < config.min_utterance_seconds:
        return False
    return silence_seconds >= config.silence_seconds


class VoiceCallListener(QThread):
    """后台线程持续读麦克风，按静音切分语句。"""

    status_changed = Signal(str)
    user_started_speaking = Signal()
    utterance_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        stt_settings: STTSettings,
        recordings_dir: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.stt_settings = stt_settings
        self.config = VoiceCallConfig.from_stt_settings(stt_settings)
        self.recordings_dir = recordings_dir
        self._running = False
        self._user_speaking_emitted = False

    def stop_listening(self) -> None:
        self._running = False

    def run(self) -> None:
        import sounddevice as sd

        self._running = True
        block_duration = 0.03
        block_size = max(1, int(SAMPLE_RATE * block_duration))
        silence_blocks_needed = max(1, int(self.config.silence_seconds / block_duration))
        min_speech_blocks = max(1, int(self.config.min_utterance_seconds / block_duration))
        max_blocks = max(min_speech_blocks, int(self.config.max_utterance_seconds / block_duration))

        speech_frames: list[np.ndarray] = []
        speech_blocks = 0
        trailing_silence_blocks = 0
        in_speech = False
        device = get_input_device()

        self.status_changed.emit("通话中，请说话…")
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                device=device,
                blocksize=block_size,
            ) as stream:
                while self._running:
                    data, _overflowed = stream.read(block_size)
                    if not self._running:
                        break
                    block = np.asarray(data)
                    if block.ndim > 1:
                        block = block[:, 0]

                    speaking = is_speech_block(
                        block,
                        rms_threshold=self.config.speech_rms_threshold,
                        peak_threshold=self.config.speech_peak_threshold,
                    )

                    if speaking:
                        if not in_speech:
                            in_speech = True
                            speech_frames = []
                            speech_blocks = 0
                            trailing_silence_blocks = 0
                            if not self._user_speaking_emitted:
                                self._user_speaking_emitted = True
                                self.user_started_speaking.emit()
                        speech_frames.append(block.copy())
                        speech_blocks += 1
                        trailing_silence_blocks = 0
                        if speech_blocks >= max_blocks:
                            self._finalize_frames(speech_frames)
                            in_speech = False
                            speech_frames = []
                            speech_blocks = 0
                            trailing_silence_blocks = 0
                            self._user_speaking_emitted = False
                            self.status_changed.emit("通话中，请说话…")
                        continue

                    if not in_speech:
                        continue

                    speech_frames.append(block.copy())
                    trailing_silence_blocks += 1
                    if trailing_silence_blocks < silence_blocks_needed:
                        continue

                    if speech_blocks >= min_speech_blocks:
                        self._finalize_frames(speech_frames)
                    in_speech = False
                    speech_frames = []
                    speech_blocks = 0
                    trailing_silence_blocks = 0
                    self._user_speaking_emitted = False
                    self.status_changed.emit("通话中，请说话…")
        except Exception as exc:  # noqa: BLE001
            logger.exception("语音通话监听失败")
            self.error_occurred.emit(f"语音通话监听失败：{exc}")
        finally:
            self._running = False

    def _finalize_frames(self, frames: list[np.ndarray]) -> None:
        if not frames:
            return
        audio = np.concatenate(frames, axis=0)
        if audio.ndim > 1:
            audio = audio[:, 0]
        duration = len(audio) / SAMPLE_RATE
        if duration < self.config.min_utterance_seconds:
            return

        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = self.recordings_dir / f"call_{stamp}_{uuid.uuid4().hex[:8]}.wav"
        wavfile.write(str(out_path), SAMPLE_RATE, audio)
        logger.info("语音通话语句已切分: %s (%.2fs)", out_path, duration)
        self.status_changed.emit("正在识别…")
        self.utterance_ready.emit(str(out_path.resolve()))
