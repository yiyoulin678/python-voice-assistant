"""后台线程：避免 AI / 录音阻塞界面。"""
from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from ai import audio_io, pipeline, text_process, text_to_speech
from ai.pipeline import VoiceSessionResult
from ai.text_process import ProcessMode


class StatusWorker(QThread):
    """仅上报状态文本。"""

    status = pyqtSignal(str)

    def __init__(self, message: str, parent=None) -> None:
        super().__init__(parent)
        self._message = message

    def run(self) -> None:
        self.status.emit(self._message)


class PreloadWorker(QThread):
    """启动时预加载 Whisper / NLP。"""

    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            pipeline.preload_all()
            self.finished_ok.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class VoiceFromWavWorker(QThread):
    """wav → 识别 → 回复 → 可选播报。"""

    finished = pyqtSignal(object)
    status = pyqtSignal(str)

    def __init__(
        self,
        wav_path: str,
        speak_reply: bool = True,
        mode: str = ProcessMode.QA,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.wav_path = wav_path
        self.speak_reply = speak_reply
        self.mode = mode

    def run(self) -> None:
        self.status.emit("正在识别语音…")
        result = pipeline.run_from_wav(
            self.wav_path,
            mode=self.mode,
            speak_reply=False,
        )
        if result.success and self.speak_reply and result.reply_text:
            self.status.emit("正在语音回复…")
            try:
                text_to_speech.speak(result.reply_text, block=True)
            except text_to_speech.TextToSpeechError as exc:
                result.error_message = str(exc)
        self.finished.emit(result)


class TextChatWorker(QThread):
    """文字输入 → 回复 → 可选播报（无麦克风）。"""

    finished = pyqtSignal(object)
    status = pyqtSignal(str)

    def __init__(
        self,
        text: str,
        speak_reply: bool = True,
        mode: str = ProcessMode.QA,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.speak_reply = speak_reply
        self.mode = mode

    def run(self) -> None:
        result = VoiceSessionResult(
            success=False,
            recognized_text=self.text,
            reply_text="",
            error_message="",
            recording_path="",
        )
        try:
            self.status.emit("正在思考…")
            result.reply_text = text_process.process_text(self.text, mode=self.mode)
            result.success = True
            if self.speak_reply and result.reply_text:
                self.status.emit("正在语音回复…")
                text_to_speech.speak(result.reply_text, block=True)
        except text_process.TextProcessError as exc:
            result.error_message = str(exc)
        except text_to_speech.TextToSpeechError as exc:
            result.error_message = str(exc)
            result.success = True
        except Exception as exc:
            result.error_message = f"未知错误: {exc}"
        self.finished.emit(result)


class StopRecordAndProcessWorker(QThread):
    """停止录音并走完整管道。"""

    finished = pyqtSignal(object)
    status = pyqtSignal(str)

    def __init__(
        self,
        speak_reply: bool = True,
        mode: str = ProcessMode.QA,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.speak_reply = speak_reply
        self.mode = mode

    def run(self) -> None:
        result = VoiceSessionResult(
            success=False,
            recognized_text="",
            reply_text="",
            error_message="",
            recording_path="",
        )
        try:
            self.status.emit("正在保存录音…")
            result.recording_path = audio_io.stop_recording()
            inner = pipeline.run_from_wav(
                result.recording_path,
                mode=self.mode,
                speak_reply=False,
            )
            result.recognized_text = inner.recognized_text
            result.reply_text = inner.reply_text
            result.error_message = inner.error_message
            result.success = inner.success
            if inner.success and self.speak_reply and result.reply_text:
                self.status.emit("正在语音回复…")
                text_to_speech.speak(result.reply_text, block=True)
        except audio_io.AudioIOError as exc:
            result.error_message = str(exc)
        except Exception as exc:
            result.error_message = f"未知错误: {exc}"
        self.finished.emit(result)
