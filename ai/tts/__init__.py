"""语音合成（CosyVoice 克隆音 + pyttsx3 兜底）。"""
from ai.tts.speaker import TextToSpeechError, get_tts_backend_name, speak, speak_async

__all__ = ["speak", "speak_async", "TextToSpeechError", "get_tts_backend_name"]
