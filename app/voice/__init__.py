"""语音播放与语音识别。"""

from app.voice.playback_controller import VoicePlaybackController
from app.voice.stt_settings import STTSettings
# TTS 类延迟导入，避免缺少音频库时阻塞整个 voice 包
# from app.voice.tts import GPTSoVITSTTSProvider, GPTSoVITSTTSSettings, NullTTSProvider, TTSConfigError, TTSProvider

__all__ = [
    "STTSettings",
    "GPTSoVITSTTSProvider",
    "GPTSoVITSTTSSettings",
    "NullTTSProvider",
    "TTSConfigError",
    "TTSProvider",
    "VoicePlaybackController",
]
