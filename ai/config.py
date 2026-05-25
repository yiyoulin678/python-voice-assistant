"""AI 与音频模块配置。"""
from pathlib import Path

# VoiceAssistant/ 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODELS_DIR = PROJECT_ROOT / "models"
RECORDINGS_DIR = PROJECT_ROOT / "resources" / "recordings"
RESOURCES_DIR = PROJECT_ROOT / "resources"

# 音频参数（Whisper 友好）
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

# 静音检测（无麦克风 / 未说话时不应继续识别与 TTS）
# RMS 低于此阈值视为静音（float32 波形，约 -42dB 量级）
SILENCE_RMS_THRESHOLD = 0.008
# Whisper 段平均 no_speech_prob 高于此值视为无有效语音
WHISPER_NO_SPEECH_PROB_THRESHOLD = 0.55

# Whisper
WHISPER_MODEL_NAME = "base"
WHISPER_LANGUAGE = "zh"

# NLP（阶段3 使用）
NLP_QA_MODEL = "uer/roberta-base-chinese-extractive-qa"

# 确保运行时目录存在
MODELS_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
