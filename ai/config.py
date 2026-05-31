"""AI 与音频模块配置。"""
from __future__ import annotations

import json
from pathlib import Path

# VoiceAssistant/ 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
AI_SETTINGS_PATH = CONFIG_DIR / "ai_settings.json"
AUDIO_DEVICES_PATH = CONFIG_DIR / "audio_devices.json"
PERSONA_PATH = CONFIG_DIR / "persona_default.json"

MODELS_DIR = PROJECT_ROOT / "models"
RECORDINGS_DIR = PROJECT_ROOT / "resources" / "recordings"
RESOURCES_DIR = PROJECT_ROOT / "resources"
VOICE_REF_DIR = RESOURCES_DIR / "voice_ref"
THIRD_PARTY_DIR = PROJECT_ROOT / "third_party"

# 音频参数（Whisper 友好）
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

SILENCE_RMS_THRESHOLD = 0.008
WHISPER_NO_SPEECH_PROB_THRESHOLD = 0.55

WHISPER_MODEL_NAME = "base"
WHISPER_LANGUAGE = "zh"

NLP_QA_MODEL = "uer/roberta-base-chinese-extractive-qa"

# 默认值（可被 config/ai_settings.json 覆盖）
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_TIMEOUT = 120.0
TTS_BACKEND = "auto"
COSYVOICE_ROOT = THIRD_PARTY_DIR / "CosyVoice"
COSYVOICE_MODEL_DIR = "pretrained_models/CosyVoice2-0.5B"
COSYVOICE_PROMPT_TEXT = "希望你以后能够做的比我还好呦。"
COSYVOICE_REFERENCE_WAV = VOICE_REF_DIR / "reference.wav"
GPT_SOVITS_ENABLED = True
GPT_SOVITS_API_URL = "http://127.0.0.1:9880"
GPT_SOVITS_ROOT: Path | None = None
GPT_SOVITS_REFERENCE_WAV = VOICE_REF_DIR / "reference.wav"
GPT_SOVITS_PROMPT_TEXT = "希望你以后能够做的比我还好呦。"
GPT_SOVITS_TEXT_LANG = "zh"
GPT_SOVITS_PROMPT_LANG = "zh"
GPT_SOVITS_AUTO_START = True
GPT_SOVITS_API_TIMEOUT = 180.0
GPT_SOVITS_STARTUP_WAIT = 300.0
QWEN_TTS_ENABLED = False
QWEN_TTS_MODE = "custom_voice"
QWEN_TTS_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
QWEN_TTS_CLONE_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
QWEN_TTS_SPEAKER = "Serena"
QWEN_TTS_LANGUAGE = "Chinese"
QWEN_TTS_INSTRUCT = "温柔甜美的年轻女声，亲切自然，像虚拟女友小音一样说话。"
QWEN_TTS_REFERENCE_WAV = VOICE_REF_DIR / "reference.wav"
QWEN_TTS_PROMPT_TEXT = "希望你以后能够做的比我还好呦。"
QWEN_TTS_X_VECTOR_ONLY = False
QWEN_TTS_WEBUI_ROOT: Path | None = None
QWEN_TTS_USE_WEBUI_API = True
QWEN_TTS_API_URL = "http://127.0.0.1:7861"
QWEN_TTS_AUTO_START_API = True
QWEN_TTS_API_TIMEOUT = 300.0
QWEN_TTS_STARTUP_WAIT = 120.0
QWEN_TTS_USE_WEBUI_PYTHON = False
QWEN_TTS_PYTHON_EXE: Path | None = None
QWEN_TTS_PRELOAD_ON_STARTUP = True
VOXCPM_REPO_ROOT = THIRD_PARTY_DIR / "VoxCPM"
VOXCPM_ENABLED = True
VOXCPM_MODEL_ID = "openbmb/VoxCPM1.5"
VOXCPM_LOCAL_MODEL_DIR: Path | None = None
VOXCPM_MODE = "clone"
VOXCPM_LOAD_DENOISER = False
VOXCPM_CFG_VALUE = 2.0
VOXCPM_INFERENCE_TIMESTEPS = 4
VOXCPM_RETRY_BADCASE = False
VOXCPM_RETRY_BADCASE_MAX_TIMES = 1
VOXCPM_RETRY_BADCASE_RATIO_THRESHOLD = 8.0
VOXCPM_MAX_LEN = 1024
VOXCPM_TTS_MAX_CHARS = 120
VOXCPM_VOICE_DESIGN_PREFIX = "温柔甜美的年轻女声，亲切自然，像虚拟女友小音"
VOXCPM_STYLE_CONTROL = ""
VOXCPM_REFERENCE_WAV = VOICE_REF_DIR / "reference.wav"
VOXCPM_PROMPT_TEXT = ""
VOXCPM_X_VECTOR_ONLY = True
VOXCPM_PRELOAD_ON_STARTUP = True
DIALOGUE_MAX_HISTORY_TURNS = 8


def _load_ai_settings() -> None:
    global OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, TTS_BACKEND
    global COSYVOICE_ROOT, COSYVOICE_MODEL_DIR, COSYVOICE_PROMPT_TEXT
    global COSYVOICE_REFERENCE_WAV, DIALOGUE_MAX_HISTORY_TURNS
    global GPT_SOVITS_ENABLED, GPT_SOVITS_API_URL, GPT_SOVITS_ROOT
    global GPT_SOVITS_REFERENCE_WAV, GPT_SOVITS_PROMPT_TEXT
    global GPT_SOVITS_TEXT_LANG, GPT_SOVITS_PROMPT_LANG
    global GPT_SOVITS_AUTO_START, GPT_SOVITS_API_TIMEOUT, GPT_SOVITS_STARTUP_WAIT
    global QWEN_TTS_ENABLED, QWEN_TTS_MODE, QWEN_TTS_MODEL_ID, QWEN_TTS_CLONE_MODEL_ID
    global QWEN_TTS_SPEAKER, QWEN_TTS_LANGUAGE, QWEN_TTS_INSTRUCT
    global QWEN_TTS_REFERENCE_WAV, QWEN_TTS_PROMPT_TEXT, QWEN_TTS_X_VECTOR_ONLY
    global QWEN_TTS_WEBUI_ROOT, QWEN_TTS_USE_WEBUI_API, QWEN_TTS_API_URL
    global QWEN_TTS_AUTO_START_API, QWEN_TTS_API_TIMEOUT, QWEN_TTS_STARTUP_WAIT
    global QWEN_TTS_USE_WEBUI_PYTHON, QWEN_TTS_PYTHON_EXE, QWEN_TTS_PRELOAD_ON_STARTUP
    global VOXCPM_REPO_ROOT, VOXCPM_ENABLED, VOXCPM_MODEL_ID, VOXCPM_LOCAL_MODEL_DIR, VOXCPM_MODE
    global VOXCPM_LOAD_DENOISER, VOXCPM_CFG_VALUE, VOXCPM_INFERENCE_TIMESTEPS
    global VOXCPM_RETRY_BADCASE, VOXCPM_MAX_LEN, VOXCPM_TTS_MAX_CHARS
    global VOXCPM_RETRY_BADCASE_MAX_TIMES, VOXCPM_RETRY_BADCASE_RATIO_THRESHOLD
    global VOXCPM_VOICE_DESIGN_PREFIX, VOXCPM_STYLE_CONTROL
    global VOXCPM_REFERENCE_WAV, VOXCPM_PROMPT_TEXT, VOXCPM_X_VECTOR_ONLY
    global VOXCPM_PRELOAD_ON_STARTUP

    if not AI_SETTINGS_PATH.is_file():
        return
    try:
        with AI_SETTINGS_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    ollama = data.get("ollama", {})
    OLLAMA_BASE_URL = ollama.get("base_url", OLLAMA_BASE_URL)
    OLLAMA_MODEL = ollama.get("model", OLLAMA_MODEL)
    OLLAMA_TIMEOUT = float(ollama.get("timeout_seconds", OLLAMA_TIMEOUT))

    tts = data.get("tts", {})
    TTS_BACKEND = tts.get("backend", TTS_BACKEND)

    cv = data.get("cosyvoice", {})
    rel_root = cv.get("third_party_dir", "third_party/CosyVoice")
    COSYVOICE_ROOT = PROJECT_ROOT / rel_root
    COSYVOICE_MODEL_DIR = cv.get("model_dir", COSYVOICE_MODEL_DIR)
    COSYVOICE_PROMPT_TEXT = cv.get("prompt_text", COSYVOICE_PROMPT_TEXT)
    ref = cv.get("reference_wav", "resources/voice_ref/reference.wav")
    COSYVOICE_REFERENCE_WAV = PROJECT_ROOT / ref

    gs = data.get("gpt_sovits", {})
    GPT_SOVITS_ENABLED = bool(gs.get("enabled", GPT_SOVITS_ENABLED))
    GPT_SOVITS_API_URL = gs.get("api_url", GPT_SOVITS_API_URL).rstrip("/")
    install_dir = gs.get("install_dir") or gs.get("root")
    GPT_SOVITS_ROOT = (PROJECT_ROOT / install_dir).resolve() if install_dir else None
    gref = gs.get("reference_wav", ref)
    GPT_SOVITS_REFERENCE_WAV = PROJECT_ROOT / gref
    GPT_SOVITS_PROMPT_TEXT = gs.get("prompt_text", COSYVOICE_PROMPT_TEXT)
    GPT_SOVITS_TEXT_LANG = gs.get("text_lang", "zh")
    GPT_SOVITS_PROMPT_LANG = gs.get("prompt_lang", "zh")
    GPT_SOVITS_AUTO_START = bool(gs.get("auto_start_api", True))
    GPT_SOVITS_API_TIMEOUT = float(gs.get("timeout_seconds", GPT_SOVITS_API_TIMEOUT))
    GPT_SOVITS_STARTUP_WAIT = float(gs.get("api_startup_wait_seconds", GPT_SOVITS_STARTUP_WAIT))

    qt = data.get("qwen_tts", {})
    QWEN_TTS_ENABLED = bool(qt.get("enabled", QWEN_TTS_ENABLED))
    QWEN_TTS_MODE = qt.get("mode", QWEN_TTS_MODE)
    QWEN_TTS_MODEL_ID = qt.get("model_id", QWEN_TTS_MODEL_ID)
    QWEN_TTS_CLONE_MODEL_ID = qt.get("clone_model_id", QWEN_TTS_CLONE_MODEL_ID)
    QWEN_TTS_SPEAKER = qt.get("speaker", QWEN_TTS_SPEAKER)
    QWEN_TTS_LANGUAGE = qt.get("language", QWEN_TTS_LANGUAGE)
    QWEN_TTS_INSTRUCT = qt.get("instruct", QWEN_TTS_INSTRUCT)
    qref = qt.get("reference_wav", ref)
    QWEN_TTS_REFERENCE_WAV = PROJECT_ROOT / qref
    QWEN_TTS_PROMPT_TEXT = qt.get("prompt_text", COSYVOICE_PROMPT_TEXT)
    QWEN_TTS_X_VECTOR_ONLY = bool(qt.get("x_vector_only_mode", QWEN_TTS_X_VECTOR_ONLY))
    webui_root = qt.get("webui_root")
    if webui_root:
        QWEN_TTS_WEBUI_ROOT = Path(webui_root).expanduser().resolve()
    else:
        QWEN_TTS_WEBUI_ROOT = None
    QWEN_TTS_USE_WEBUI_API = bool(qt.get("use_webui_api", QWEN_TTS_USE_WEBUI_API))
    QWEN_TTS_API_URL = qt.get("api_url", QWEN_TTS_API_URL).rstrip("/")
    QWEN_TTS_AUTO_START_API = bool(qt.get("auto_start_api", QWEN_TTS_AUTO_START_API))
    QWEN_TTS_API_TIMEOUT = float(qt.get("api_timeout_seconds", QWEN_TTS_API_TIMEOUT))
    QWEN_TTS_STARTUP_WAIT = float(qt.get("api_startup_wait_seconds", QWEN_TTS_STARTUP_WAIT))
    QWEN_TTS_USE_WEBUI_PYTHON = bool(qt.get("use_webui_python", QWEN_TTS_USE_WEBUI_PYTHON))
    py_exe = qt.get("python_exe")
    QWEN_TTS_PYTHON_EXE = Path(py_exe).expanduser().resolve() if py_exe else None
    QWEN_TTS_PRELOAD_ON_STARTUP = bool(qt.get("preload_on_startup", QWEN_TTS_PRELOAD_ON_STARTUP))
    if QWEN_TTS_WEBUI_ROOT and "use_webui_api" not in qt:
        QWEN_TTS_USE_WEBUI_API = True

    vx = data.get("voxcpm", {})
    repo_rel = vx.get("third_party_dir", "third_party/VoxCPM")
    VOXCPM_REPO_ROOT = PROJECT_ROOT / repo_rel
    VOXCPM_ENABLED = bool(vx.get("enabled", VOXCPM_ENABLED))
    VOXCPM_MODEL_ID = vx.get("model_id", VOXCPM_MODEL_ID)
    local_dir = vx.get("local_model_dir")
    VOXCPM_LOCAL_MODEL_DIR = (
        Path(local_dir).expanduser().resolve() if local_dir and str(local_dir).strip() else None
    )
    VOXCPM_MODE = vx.get("mode", VOXCPM_MODE)
    VOXCPM_LOAD_DENOISER = bool(vx.get("load_denoiser", VOXCPM_LOAD_DENOISER))
    VOXCPM_CFG_VALUE = float(vx.get("cfg_value", VOXCPM_CFG_VALUE))
    VOXCPM_INFERENCE_TIMESTEPS = int(vx.get("inference_timesteps", VOXCPM_INFERENCE_TIMESTEPS))
    VOXCPM_RETRY_BADCASE = bool(vx.get("retry_badcase", VOXCPM_RETRY_BADCASE))
    VOXCPM_RETRY_BADCASE_MAX_TIMES = int(
        vx.get("retry_badcase_max_times", VOXCPM_RETRY_BADCASE_MAX_TIMES)
    )
    VOXCPM_RETRY_BADCASE_RATIO_THRESHOLD = float(
        vx.get("retry_badcase_ratio_threshold", VOXCPM_RETRY_BADCASE_RATIO_THRESHOLD)
    )
    VOXCPM_MAX_LEN = int(vx.get("max_len", VOXCPM_MAX_LEN))
    VOXCPM_TTS_MAX_CHARS = int(vx.get("tts_max_chars", VOXCPM_TTS_MAX_CHARS))
    VOXCPM_VOICE_DESIGN_PREFIX = vx.get("voice_design_prefix", VOXCPM_VOICE_DESIGN_PREFIX)
    VOXCPM_STYLE_CONTROL = vx.get("style_control", VOXCPM_STYLE_CONTROL)
    vref = vx.get("reference_wav", ref)
    VOXCPM_REFERENCE_WAV = PROJECT_ROOT / vref
    VOXCPM_PROMPT_TEXT = vx.get("prompt_text", VOXCPM_PROMPT_TEXT)
    VOXCPM_X_VECTOR_ONLY = bool(vx.get("x_vector_only_mode", VOXCPM_X_VECTOR_ONLY))
    VOXCPM_PRELOAD_ON_STARTUP = bool(vx.get("preload_on_startup", VOXCPM_PRELOAD_ON_STARTUP))

    dlg = data.get("dialogue", {})
    DIALOGUE_MAX_HISTORY_TURNS = int(dlg.get("max_history_turns", DIALOGUE_MAX_HISTORY_TURNS))


_load_ai_settings()

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
VOICE_REF_DIR.mkdir(parents=True, exist_ok=True)
THIRD_PARTY_DIR.mkdir(parents=True, exist_ok=True)
