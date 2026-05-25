"""端到端语音学习管道。"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ai import audio_io, speech_to_text, text_process, text_to_speech
from ai.text_process import ProcessMode

logger = logging.getLogger(__name__)


@dataclass
class VoiceSessionResult:
    success: bool
    recognized_text: str
    reply_text: str
    error_message: str
    recording_path: str
    reply_audio_path: str | None = None


def preload_all(whisper_model: str | None = None) -> None:
    """预加载 Whisper 与 NLP（TTS 按需初始化）。"""
    from ai.config import WHISPER_MODEL_NAME

    name = whisper_model or WHISPER_MODEL_NAME
    speech_to_text.preload_whisper(name)
    text_process.preload_nlp()


def run_from_wav(
    wav_path: str,
    mode: str = ProcessMode.QA,
    speak_reply: bool = True,
) -> VoiceSessionResult:
    """从已有 wav 执行：识别 → 处理 → 可选播报。"""
    result = VoiceSessionResult(
        success=False,
        recognized_text="",
        reply_text="",
        error_message="",
        recording_path=wav_path,
    )
    try:
        result.recognized_text = speech_to_text.transcribe(wav_path)
        result.reply_text = text_process.process_text(result.recognized_text, mode=mode)
        if speak_reply:
            text_to_speech.speak(result.reply_text, block=True)
        result.success = True
    except speech_to_text.SpeechToTextError as exc:
        result.error_message = str(exc)
    except text_process.TextProcessError as exc:
        result.error_message = str(exc)
    except text_to_speech.TextToSpeechError as exc:
        result.error_message = str(exc)
        result.success = True
        logger.warning("播报失败但文本已生成: %s", exc)
    except Exception as exc:
        result.error_message = f"未知错误: {exc}"
        logger.exception("pipeline 失败")
    return result


def run_full_voice_session(
    mode: str = ProcessMode.QA,
    record_seconds: float | None = 5.0,
    speak_reply: bool = True,
) -> VoiceSessionResult:
    """录音 → 识别 → 处理 → 播报。"""
    result = VoiceSessionResult(
        success=False,
        recognized_text="",
        reply_text="",
        error_message="",
        recording_path="",
    )
    try:
        if record_seconds is not None:
            result.recording_path = audio_io.record_for_seconds(record_seconds)
        else:
            audio_io.start_recording()
            raise RuntimeError("请使用 GUI 调用 stop_recording 后再 run_from_wav")

        return run_from_wav(
            result.recording_path,
            mode=mode,
            speak_reply=speak_reply,
        )
    except audio_io.AudioIOError as exc:
        result.error_message = str(exc)
    except RuntimeError as exc:
        result.error_message = str(exc)
    except Exception as exc:
        result.error_message = f"未知错误: {exc}"
    return result
