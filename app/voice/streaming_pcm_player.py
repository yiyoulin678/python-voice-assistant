from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices


class StreamingPCMPlayer(QObject):
    """边收边播 PCM int16 单声道，对齐 AIFE 的 PyAudio 流式播放。"""

    playback_started = Signal()
    playback_finished = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sink: QAudioSink | None = None
        self._device = None
        self._sample_rate = 32000
        self._started_emitted = False
        self._pending_pcm = bytearray()
        self._synthesis_done = False
        self._drain_timer = QTimer(self)
        self._drain_timer.setInterval(30)
        self._drain_timer.timeout.connect(self._drain_pending_pcm)

    def is_active(self) -> bool:
        return self._sink is not None or bool(self._pending_pcm)

    def start(self, sample_rate: int = 32000) -> None:
        self.stop(finished=False)
        self._sample_rate = sample_rate
        self._started_emitted = False
        self._pending_pcm.clear()
        self._synthesis_done = False

        audio_format = QAudioFormat()
        audio_format.setSampleRate(sample_rate)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        self._sink = QAudioSink(QMediaDevices.defaultAudioOutput(), audio_format, self)
        self._device = self._sink.start()
        self._drain_timer.start()

    def append_pcm(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes:
            return
        self._pending_pcm.extend(pcm_bytes)
        if not self._started_emitted:
            self._started_emitted = True
            self.playback_started.emit()

    def mark_synthesis_done(self) -> None:
        self._synthesis_done = True

    def stop(self, *, finished: bool = True) -> None:
        self._drain_timer.stop()
        self._pending_pcm.clear()
        self._synthesis_done = False
        if self._sink is not None:
            self._sink.stop()
        self._sink = None
        self._device = None
        if finished and self._started_emitted:
            self.playback_finished.emit()
        self._started_emitted = False

    def _drain_pending_pcm(self) -> None:
        if self._device is None or self._sink is None:
            if self._synthesis_done and not self._pending_pcm:
                self.stop(finished=True)
            return

        while self._pending_pcm:
            chunk = bytes(self._pending_pcm)
            written = self._device.write(chunk)
            if written < 0:
                self.stop(finished=True)
                return
            if written == 0:
                return
            del self._pending_pcm[:written]

        if not self._synthesis_done:
            return

        if self._sink.bytesFree() < self._sink.bufferSize():
            return

        self.stop(finished=True)
