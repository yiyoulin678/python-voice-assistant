"""智能语音学习助手 — AI 与音频子包（成员3）。"""
from ai.audio_io import (
    AudioIOError,
    is_recording,
    play_wav,
    record_for_seconds,
    start_recording,
    stop_recording,
)
from ai.config import PROJECT_ROOT, RECORDINGS_DIR, SAMPLE_RATE
from ai.pipeline import VoiceSessionResult, preload_all, run_from_wav, run_full_voice_session
from ai.speech_to_text import SpeechToTextError, preload_whisper, transcribe
from ai.text_process import ProcessMode, TextProcessError, preload_nlp, process_text
from ai.text_to_speech import TextToSpeechError, speak, speak_async, speak_to_file

__all__ = [
    "PROJECT_ROOT",
    "RECORDINGS_DIR",
    "SAMPLE_RATE",
    "AudioIOError",
    "SpeechToTextError",
    "TextProcessError",
    "TextToSpeechError",
    "ProcessMode",
    "VoiceSessionResult",
    "start_recording",
    "stop_recording",
    "record_for_seconds",
    "play_wav",
    "is_recording",
    "preload_whisper",
    "transcribe",
    "preload_nlp",
    "process_text",
    "speak",
    "speak_async",
    "speak_to_file",
    "preload_all",
    "run_from_wav",
    "run_full_voice_session",
]
