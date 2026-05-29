"""后台线程：避免 AI / 录音 / CosyVoice 阻塞界面。"""

from __future__ import annotations



from PyQt5.QtCore import QThread, pyqtSignal



from ai import audio_io, pipeline, text_process, text_to_speech

from ai.pipeline import VoiceSessionResult

from ai.text_process import ProcessMode

from ai.tts.speaker import get_tts_backend_name, get_tts_status_label

from db.database import DatabaseManager



def _speak_in_worker(worker: QThread, text: str) -> None:

    """在工作线程中播报，并向 GUI 推送 CosyVoice 合成进度。"""

    text_to_speech.speak(text, block=True, on_status=worker.status.emit)





class StatusWorker(QThread):

    """仅上报状态文本。"""



    status = pyqtSignal(str)



    def __init__(self, message: str, parent=None) -> None:

        super().__init__(parent)

        self._message = message



    def run(self) -> None:

        self.status.emit(self._message)





class PreloadWorker(QThread):

    """启动时预加载 Whisper / NLP，并检测 CosyVoice 克隆声线。"""



    status = pyqtSignal(str)

    finished_ok = pyqtSignal(str)

    failed = pyqtSignal(str)



    def run(self) -> None:

        try:

            self.status.emit("正在加载语音识别 (Whisper)…")
            llm_label, tts_label = pipeline.preload_all()
            from ai.tts import speaker as tts_speaker
            from ai.tts.backends import cosyvoice_backend, qwen_tts_backend

            backend = tts_speaker.get_tts_backend_name()
            if backend == "qwen_tts" and qwen_tts_backend.is_available():
                from ai.config import QWEN_TTS_MODE, QWEN_TTS_REFERENCE_WAV

                if (QWEN_TTS_MODE or "").lower() == "clone" and not QWEN_TTS_REFERENCE_WAV.is_file():
                    tts_label = "Qwen3-TTS 克隆（请先选择音频）"
                    self.status.emit("请点击「选择克隆音频」注册声线")
                else:
                    tts_label = "Qwen3-TTS 后台加载中…"
                    self.status.emit("语音识别已就绪；Qwen3-TTS 将在后台加载…")
            elif backend == "cosyvoice" and cosyvoice_backend.is_available():
                self.status.emit("正在预热 CosyVoice（仅首次较慢）…")
                cosyvoice_backend.warmup(on_status=self.status.emit)
                tts_label = cosyvoice_backend.status_label()
            else:
                tts_label = tts_speaker.get_tts_status_label()
            self.finished_ok.emit(f"{llm_label}|{tts_label}")

        except Exception as exc:

            self.failed.emit(str(exc))


class QwenWarmupWorker(QThread):
    """后台加载 Qwen3-TTS，不阻塞主界面。"""

    status = pyqtSignal(str)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            from ai.tts.backends import qwen_tts_backend
            from ai.tts import speaker as tts_speaker

            qwen_tts_backend.warmup(on_status=self.status.emit)
            self.finished_ok.emit(qwen_tts_backend.status_label())
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Qwen TTS 后台预热失败: %s", exc)
            from ai.tts import speaker as tts_speaker

            tts_speaker.reset_backend_cache()
            self.failed.emit(str(exc))


class RegisterCloneWorker(QThread):
    """从用户选择的 wav 注册 Qwen 克隆声线。"""

    finished = pyqtSignal(bool, str)
    status = pyqtSignal(str)

    def __init__(self, wav_path: str, prompt_text: str, parent=None) -> None:
        super().__init__(parent)
        self.wav_path = wav_path
        self.prompt_text = prompt_text

    def run(self) -> None:
        try:
            from ai.tts.backends import qwen_tts_backend

            qwen_tts_backend.set_reference(
                self.wav_path,
                self.prompt_text or None,
                on_status=self.status.emit,
            )
            self.finished.emit(True, qwen_tts_backend.status_label())
        except Exception as exc:
            self.finished.emit(False, str(exc))


class TtsPreviewWorker(QThread):

    """试听当前 TTS 后端（CosyVoice 克隆或系统音）。"""



    finished = pyqtSignal(bool, str)

    status = pyqtSignal(str)



    def __init__(self, preview_text: str = "你好，我是小音，很高兴认识你。", parent=None) -> None:

        super().__init__(parent)

        self.preview_text = preview_text



    def run(self) -> None:

        try:

            backend = get_tts_backend_name()

            self.status.emit(f"试听 · {get_tts_status_label()}")

            _speak_in_worker(self, self.preview_text)

            self.finished.emit(True, backend)

        except text_to_speech.TextToSpeechError as exc:

            self.finished.emit(False, str(exc))

        except Exception as exc:

            self.finished.emit(False, str(exc))





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

            _speak_in_worker(self, result.reply_text)

        self.finished.emit(result)





class TextChatWorker(QThread):

    """文字输入 → 回复 → 可选 CosyVoice 克隆播报。"""



    finished = pyqtSignal(object)

    status = pyqtSignal(str)



    def __init__(

        self,

        text: str,

        userid,

        speak_reply: bool = True,

        mode: str = ProcessMode.QA,

        user_nickname: str = "你",

        parent=None,

    ) -> None:

        super().__init__(parent)

        self.text = text

        self.speak_reply = speak_reply

        self.mode = mode

        self.user_nickname = user_nickname

        self.user_id = userid



    def run(self) -> None:

        result = VoiceSessionResult(

            success=False,

            recognized_text=self.text,

            reply_text="",

            error_message="",

            recording_path="",

        )

        try:

            self.status.emit(f"正在思考… · 播报: {get_tts_status_label()}")

            result.reply_text = text_process.process_text(

                self.text, mode=self.mode, user_nickname=self.user_nickname

            )
            db = DatabaseManager()
            
            db.save_history(
                user_id=self.user_id,
                speech_text=self.text,
                ai_response=result.reply_text
            )

            result.success = True

            if self.speak_reply and result.reply_text:

                _speak_in_worker(self, result.reply_text)

        except text_process.TextProcessError as exc:

            result.error_message = str(exc)

        except text_to_speech.TextToSpeechError as exc:

            result.error_message = str(exc)

            result.success = True

        except Exception as exc:

            result.error_message = f"未知错误: {exc}"

        self.finished.emit(result)





class StartRecordingWorker(QThread):
    """在后台线程打开麦克风，避免阻塞 GUI。"""

    finished = pyqtSignal(bool, str)

    def run(self) -> None:
        try:
            audio_io.start_recording()
            self.finished.emit(True, "")
        except audio_io.AudioIOError as exc:
            self.finished.emit(False, str(exc))
        except Exception as exc:
            self.finished.emit(False, f"启动录音失败: {exc}")


class StopRecordAndProcessWorker(QThread):

    """停止录音并走完整管道，回复使用 GUI 配置的 TTS。"""



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

            self.status.emit("正在识别语音…")

            inner = pipeline.run_from_wav(

                result.recording_path,

                mode=self.mode,

                speak_reply=False,

            )

            result.recognized_text = inner.recognized_text

            result.reply_text = inner.reply_text

            result.error_message = inner.error_message

            result.success = inner.success

            if inner.success:

                self.status.emit(f"正在生成回复… · 播报: {get_tts_status_label()}")

            if inner.success and self.speak_reply and result.reply_text:

                _speak_in_worker(self, result.reply_text)

        except audio_io.AudioIOError as exc:

            result.error_message = str(exc)

        except text_to_speech.TextToSpeechError as exc:

            result.error_message = str(exc)

            if result.reply_text:

                result.success = True

        except Exception as exc:

            result.error_message = f"未知错误: {exc}"

        self.finished.emit(result)


