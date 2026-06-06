"""语音输入后台线程，避免阻塞 Qt 主界面。"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from app.voice import audio_io, speech_to_text
from app.voice.stt_settings import STTSettings


@dataclass
class VoiceTranscribeResult:
    success: bool
    text: str = ""
    recording_path: str = ""
    error_message: str = ""


class StartRecordingWorker(QThread):
    finished = Signal(bool, str)

    def run(self) -> None:
        try:
            audio_io.start_recording()
            self.finished.emit(True, "")
        except audio_io.AudioIOError as exc:
            self.finished.emit(False, str(exc))
        except Exception as exc:
            self.finished.emit(False, f"启动录音失败: {exc}")


class TranscribePathWorker(QThread):
    finished = Signal(object)

    def __init__(self, recording_path: str, stt_settings: STTSettings, parent=None) -> None:
        super().__init__(parent)
        self.recording_path = recording_path
        self.stt_settings = stt_settings

    def run(self) -> None:
        result = VoiceTranscribeResult(success=False, recording_path=self.recording_path)
        try:
            result.text = speech_to_text.transcribe(
                self.recording_path,
                language=self.stt_settings.language,
                model_name=self.stt_settings.model_name,
            )
            result.success = True
        except speech_to_text.SpeechToTextError as exc:
            result.error_message = str(exc)
        except Exception as exc:  # noqa: BLE001
            result.error_message = f"语音识别失败: {exc}"
        self.finished.emit(result)


class StopRecordTranscribeWorker(QThread):
    finished = Signal(object)
    status = Signal(str)

    def __init__(self, stt_settings: STTSettings, parent=None) -> None:
        super().__init__(parent)
        self.stt_settings = stt_settings

    def run(self) -> None:
        result = VoiceTranscribeResult(success=False)
        try:
            self.status.emit("正在保存录音…")
            result.recording_path = audio_io.stop_recording()
            self.status.emit("正在识别语音…")
            result.text = speech_to_text.transcribe(
                result.recording_path,
                language=self.stt_settings.language,
                model_name=self.stt_settings.model_name,
            )
            result.success = True
        except (audio_io.AudioIOError, speech_to_text.SpeechToTextError) as exc:
            result.error_message = str(exc)
        except Exception as exc:
            result.error_message = f"语音识别失败: {exc}"
        self.finished.emit(result)
