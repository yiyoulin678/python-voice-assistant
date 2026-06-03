from __future__ import annotations

import math
import struct
import time
import wave
from pathlib import Path

from PySide6.QtCore import QObject, QTimer


class Live2DLipSyncController(QObject):
    """根据 TTS 音频 RMS 或简易振荡驱动嘴部开合。"""

    def __init__(
        self,
        set_mouth_open: callable,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._set_mouth_open = set_mouth_open
        self._envelope: list[float] = []
        self._frame_ms = 20
        self._duration_ms = 0
        self._started_at = 0.0
        self._phase = 0.0
        self._use_procedural = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self, audio_path: Path | None) -> None:
        self._use_procedural = True
        self._envelope = []
        self._duration_ms = 0
        if audio_path is not None and audio_path.is_file():
            try:
                self._envelope, self._duration_ms = _load_rms_envelope(audio_path)
                self._use_procedural = not self._envelope
            except (OSError, wave.Error, struct.error):
                self._use_procedural = True
        self._started_at = time.perf_counter()
        self._phase = 0.0
        self._timer.start()
        self._tick()

    def stop(self) -> None:
        self._timer.stop()
        self._set_mouth_open(0.0)

    def _tick(self) -> None:
        if self._use_procedural:
            self._phase += 0.35
            value = 0.25 + 0.45 * abs(math.sin(self._phase))
            self._set_mouth_open(value)
            return

        elapsed_ms = (time.perf_counter() - self._started_at) * 1000
        if self._duration_ms > 0 and elapsed_ms >= self._duration_ms:
            self._set_mouth_open(0.0)
            return
        index = min(len(self._envelope) - 1, int(elapsed_ms / self._frame_ms))
        self._set_mouth_open(self._envelope[index])


def _load_rms_envelope(path: Path, *, frame_ms: int = 20) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise wave.Error("仅支持 16-bit PCM wav")
    sample_count = len(raw) // 2
    samples = struct.unpack(f"<{sample_count}h", raw)
    if channels > 1:
        mono = []
        for index in range(0, len(samples), channels):
            chunk = samples[index : index + channels]
            mono.append(sum(chunk) / len(chunk))
        samples = mono

    duration_ms = int(frame_count * 1000 / max(frame_rate, 1))
    samples_per_frame = max(1, int(frame_rate * frame_ms / 1000))
    envelope: list[float] = []
    for offset in range(0, len(samples), samples_per_frame):
        chunk = samples[offset : offset + samples_per_frame]
        if not chunk:
            continue
        mean_square = sum(value * value for value in chunk) / len(chunk)
        envelope.append(math.sqrt(mean_square))

    if not envelope:
        return [], duration_ms

    peak = max(envelope) or 1.0
    normalized = [
        min(1.0, max(0.0, (value / peak) ** 0.55 * 0.9 + 0.05))
        for value in envelope
    ]
    return normalized, duration_ms
