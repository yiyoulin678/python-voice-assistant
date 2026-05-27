"""通过 Qwen TTS WebUI 官方 HTTP API 合成（--api --nowebui）。"""
from __future__ import annotations

import base64
import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import requests

from ai import config as ai_config
from ai.tts.backends.qwen_tts_webui_env import apply_webui_env, webui_python_exe, webui_root
from ai.tts.text_clean import clean_for_tts

logger = logging.getLogger(__name__)

_api_proc: subprocess.Popen | None = None
_ref_b64_cache: str | None = None
_model_preloaded = False


class QwenTTSApiError(Exception):
    pass


def _api_base() -> str:
    return ai_config.QWEN_TTS_API_URL.rstrip("/")


def _api_host_port() -> tuple[str, int]:
    u = urlparse(_api_base())
    return u.hostname or "127.0.0.1", u.port or 7860


def _port_open(timeout: float = 1.0) -> bool:
    host, port = _api_host_port()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _models_ok(base: str, timeout: float = 3.0) -> bool:
    try:
        r = requests.get(f"{base.rstrip('/')}/qwenapi/v1/models", timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def is_api_running(timeout: float = 3.0) -> bool:
    return _models_ok(_api_base(), timeout)


def _discover_api_base() -> str | None:
    """在常见端口上查找已运行的 Qwen TTS API。"""
    host = _api_host_port()[0]
    configured = _api_host_port()[1]
    for port in (configured, 7861, 7860, 7862):
        base = f"http://{host}:{port}"
        if _models_ok(base, timeout=2.0):
            return base
    return None


def _apply_discovered_base(base: str) -> None:
    if ai_config.QWEN_TTS_API_URL.rstrip("/") != base.rstrip("/"):
        logger.info("使用已发现的 Qwen TTS API: %s", base)
        ai_config.QWEN_TTS_API_URL = base.rstrip("/")


def _start_api_process() -> None:
    global _api_proc
    root = webui_root()
    py = webui_python_exe()
    if root is None or py is None:
        raise QwenTTSApiError("未配置 qwen_tts.webui_root 或找不到 python.exe")

    if _api_proc and _api_proc.poll() is None:
        return
    if is_api_running():
        return

    host, port = _api_host_port()
    log_dir = ai_config.PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "qwen_tts_api.log"

    env = os.environ.copy()
    apply_webui_env()
    for key in ("MODELSCOPE_CACHE", "HF_HOME"):
        if key in os.environ:
            env[key] = os.environ[key]
    core = root / "core"
    env["PYTHONPATH"] = str(core) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [
        str(py),
        "-m",
        "qwen_tts_webui",
        "--api",
        "--nowebui",
        "--no-inbrowser",
        "--skip-check",
        "--server-name",
        host,
        "--server-port",
        str(port),
    ]
    logger.info("启动 Qwen TTS API: %s", " ".join(cmd))
    with open(log_file, "a", encoding="utf-8") as logf:
        logf.write(f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        _api_proc = subprocess.Popen(
            cmd,
            cwd=str(root),
            stdout=logf,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )


def ensure_api_running(
    on_status: Callable[[str], None] | None = None,
    wait_seconds: float | None = None,
) -> None:
    if is_api_running():
        return

    found = _discover_api_base()
    if found:
        _apply_discovered_base(found)
        return

    def _emit(msg: str) -> None:
        if on_status:
            on_status(msg)

    if _port_open() and not is_api_running():
        port = _api_host_port()[1]
        raise QwenTTSApiError(
            f"端口 {port} 有程序在运行，但不是 Qwen TTS API。"
            "请在 WebUI 的 launch_args.txt 中加入 --api 并重启 WebUI，"
            "或关闭占用该端口的程序后让小音自动启动 API。"
        )

    if not ai_config.QWEN_TTS_AUTO_START_API:
        raise QwenTTSApiError(
            f"Qwen TTS API 未运行。请先启动 WebUI API（{_api_base()}），"
            "或设 qwen_tts.auto_start_api 为 true"
        )

    _emit("正在启动 Qwen TTS API 服务…")
    _start_api_process()
    deadline = time.time() + (wait_seconds or ai_config.QWEN_TTS_STARTUP_WAIT)
    while time.time() < deadline:
        if is_api_running():
            _emit("Qwen TTS API 已就绪")
            return
        if _api_proc and _api_proc.poll() is not None:
            log = ai_config.PROJECT_ROOT / "logs" / "qwen_tts_api.log"
            raise QwenTTSApiError(f"API 进程已退出，请查看 {log}")
        time.sleep(1.0)
    raise QwenTTSApiError(
        f"等待 API 超时（{int(wait_seconds or ai_config.QWEN_TTS_STARTUP_WAIT)}s）。"
        "可手动运行 scripts/start_qwen_tts_api.bat"
    )


def _encode_wav(path: Path) -> str:
    global _ref_b64_cache
    if _ref_b64_cache is not None:
        return _ref_b64_cache
    _ref_b64_cache = base64.b64encode(path.read_bytes()).decode("ascii")
    return _ref_b64_cache


def _clear_ref_cache() -> None:
    global _ref_b64_cache, _model_preloaded
    _ref_b64_cache = None
    _model_preloaded = False


def _model_name() -> str:
    mode = (ai_config.QWEN_TTS_MODE or "custom_voice").lower()
    if mode == "clone":
        return ai_config.QWEN_TTS_CLONE_MODEL_ID
    return ai_config.QWEN_TTS_MODEL_ID


def _language_param() -> str | None:
    lang = (ai_config.QWEN_TTS_LANGUAGE or "").strip()
    if not lang or lang.lower() in ("auto", "自动"):
        return None
    return lang


def speak(
    text: str,
    on_status: Callable[[str], None] | None = None,
) -> tuple[bytes, int]:
    global _model_preloaded

    cleaned = clean_for_tts(text)
    if not cleaned:
        raise QwenTTSApiError("播报文本为空")

    def _emit(msg: str) -> None:
        if on_status:
            on_status(msg)

    ensure_api_running(on_status)
    mode = (ai_config.QWEN_TTS_MODE or "custom_voice").lower()
    timeout = ai_config.QWEN_TTS_API_TIMEOUT

    if mode == "clone":
        ref = ai_config.QWEN_TTS_REFERENCE_WAV
        if not ref.is_file():
            raise QwenTTSApiError("请先「选择克隆音频」或放入 reference.wav")
        ref_text = None
        if not ai_config.QWEN_TTS_X_VECTOR_ONLY:
            ref_text = ai_config.QWEN_TTS_PROMPT_TEXT or None
        hint = "合成中" if _model_preloaded else "合成中（API 首次会加载模型，与 WebUI 同进程则更快）"
        _emit(f"Qwen3-TTS 克隆{hint}…")
        payload = {
            "model_name": _model_name(),
            "text": cleaned,
            "language": _language_param(),
            "ref_audio_base64": _encode_wav(ref),
            "ref_text": ref_text,
        }
        url = f"{_api_base()}/qwenapi/v1/voice-clone"
    else:
        _emit("Qwen3-TTS 合成中…")
        payload = {
            "model_name": _model_name(),
            "text": cleaned,
            "speaker": ai_config.QWEN_TTS_SPEAKER,
            "language": _language_param(),
            "instruct": ai_config.QWEN_TTS_INSTRUCT or "",
        }
        url = f"{_api_base()}/qwenapi/v1/custom-voice"

    logger.info(
        "POST %s text_len=%d ref_b64_kb=%s",
        url,
        len(cleaned),
        len(payload.get("ref_audio_base64", "")) // 1024 if "ref_audio_base64" in payload else 0,
    )
    t0 = time.perf_counter()
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise QwenTTSApiError(f"请求 API 失败: {exc}") from exc
    elapsed = time.perf_counter() - t0
    logger.info("API 响应 %s 耗时 %.1fs", r.status_code, elapsed)

    if r.status_code != 200:
        detail = r.text[:500]
        try:
            detail = r.json().get("detail", detail)
        except Exception:
            pass
        raise QwenTTSApiError(f"API 错误 ({r.status_code}): {detail}")

    data = r.json()
    files = data.get("audio_files_base64") or []
    if not files:
        raise QwenTTSApiError("API 未返回音频")

    _model_preloaded = True
    info = data.get("info", "")
    if info:
        logger.info("API: %s", info)

    wav_bytes = base64.b64decode(files[0])
    return wav_bytes, 24000


def set_reference(
    wav_path: str | Path,
    prompt_text: str | None = None,
    on_status: Callable[[str], None] | None = None,
) -> Path:
    def _emit(msg: str) -> None:
        if on_status:
            on_status(msg)

    src = Path(wav_path).resolve()
    if not src.is_file():
        raise QwenTTSApiError(f"音频不存在: {src}")

    dest = ai_config.QWEN_TTS_REFERENCE_WAV
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    _clear_ref_cache()
    if prompt_text is not None:
        ai_config.QWEN_TTS_PROMPT_TEXT = prompt_text.strip()
    _emit("参考音频已保存，播报时将通过 API 克隆")
    return dest


def warmup(on_status: Callable[[str], None] | None = None) -> None:
    """确保 API 可访问。api_url 端口须与 WebUI 浏览器地址栏一致。"""
    ensure_api_running(on_status)
