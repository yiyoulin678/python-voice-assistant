"""GPT-SoVITS TTS（通过 api_v2.py HTTP 服务）。"""
from __future__ import annotations

import logging
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import requests

from ai.config import (
    GPT_SOVITS_API_TIMEOUT,
    GPT_SOVITS_API_URL,
    GPT_SOVITS_AUTO_START,
    GPT_SOVITS_ENABLED,
    GPT_SOVITS_PROMPT_LANG,
    GPT_SOVITS_PROMPT_TEXT,
    GPT_SOVITS_REFERENCE_WAV,
    GPT_SOVITS_ROOT,
    GPT_SOVITS_STARTUP_WAIT,
    GPT_SOVITS_TEXT_LANG,
)
from ai.tts.text_clean import clean_for_tts

logger = logging.getLogger(__name__)

_api_proc: subprocess.Popen | None = None


def _api_host_port() -> tuple[str, int]:
    u = urlparse(GPT_SOVITS_API_URL)
    host = u.hostname or "127.0.0.1"
    port = u.port or 9880
    return host, port


def _api_base() -> str:
    return GPT_SOVITS_API_URL.rstrip("/")


def _port_open(timeout: float = 1.0) -> bool:
    host, port = _api_host_port()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_api_running(timeout: float = 2.0) -> bool:
    if not _port_open(timeout=min(timeout, 1.0)):
        return False
    try:
        r = requests.get(f"{_api_base()}/set_refer_audio", timeout=timeout)
        return r.status_code in (200, 400)
    except requests.RequestException:
        return _port_open(timeout=timeout)


def is_available() -> bool:
    if not GPT_SOVITS_ENABLED:
        return False
    if not GPT_SOVITS_REFERENCE_WAV.is_file():
        logger.debug("GPT-SoVITS 参考音频不存在: %s", GPT_SOVITS_REFERENCE_WAV)
        return False
    if is_api_running():
        return True
    if GPT_SOVITS_AUTO_START and GPT_SOVITS_ROOT and (GPT_SOVITS_ROOT / "api_v2.py").is_file():
        return True
    return False


def status_label() -> str:
    if is_api_running():
        return "GPT-SoVITS 克隆声线"
    if GPT_SOVITS_ROOT and (GPT_SOVITS_ROOT / "api_v2.py").is_file():
        return "GPT-SoVITS（待启动 API）"
    return "GPT-SoVITS 未配置"


def _python_exe() -> str:
    if GPT_SOVITS_ROOT:
        bundled = GPT_SOVITS_ROOT / "runtime" / "python.exe"
        if bundled.is_file():
            return str(bundled)
    return sys.executable


def _start_api_process() -> None:
    global _api_proc
    if not GPT_SOVITS_ROOT or not (GPT_SOVITS_ROOT / "api_v2.py").is_file():
        raise RuntimeError(
            "未找到 GPT-SoVITS。请在 config/ai_settings.json 的 gpt_sovits.install_dir 填写安装路径"
        )
    if _api_proc and _api_proc.poll() is None:
        return
    if _port_open():
        return

    py = _python_exe()
    host, port = _api_host_port()
    log_dir = Path(__file__).resolve().parents[3] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gpt_sovits_api.log"

    logger.info("启动 GPT-SoVITS API: %s (%s)", GPT_SOVITS_ROOT, py)
    with open(log_file, "a", encoding="utf-8") as logf:
        logf.write(f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        _api_proc = subprocess.Popen(
            [py, "api_v2.py", "-a", host, "-p", str(port)],
            cwd=str(GPT_SOVITS_ROOT),
            stdout=logf,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )


def ensure_api_running(
    on_status: Callable[[str], None] | None = None,
    wait_seconds: float | None = None,
) -> None:
    if is_api_running():
        return

    def _emit(msg: str) -> None:
        if on_status:
            on_status(msg)

    if not GPT_SOVITS_AUTO_START:
        raise RuntimeError(
            "GPT-SoVITS API 未运行。请先运行 scripts\\start_gpt_sovits_api.bat"
        )

    wait = wait_seconds if wait_seconds is not None else GPT_SOVITS_STARTUP_WAIT
    _emit("正在启动 GPT-SoVITS（首次加载模型约 1～3 分钟）…")
    _start_api_process()

    t0 = time.time()
    while time.time() - t0 < wait:
        if is_api_running():
            _emit("GPT-SoVITS API 已就绪")
            return
        elapsed = int(time.time() - t0)
        if elapsed > 0 and elapsed % 15 == 0:
            _emit(f"仍在加载 GPT-SoVITS…（已 {elapsed} 秒）")
        time.sleep(2)

    raise RuntimeError(
        "GPT-SoVITS API 启动超时。请先双击 scripts\\start_gpt_sovits_api.bat，"
        "看到 Uvicorn running 后再开 GUI；日志见 logs/gpt_sovits_api.log"
    )


def warmup(on_status: Callable[[str], None] | None = None) -> None:
    ensure_api_running(on_status=on_status)
    ref = str(GPT_SOVITS_REFERENCE_WAV.resolve())
    try:
        r = requests.get(
            f"{_api_base()}/set_refer_audio",
            params={"refer_audio_path": ref},
            timeout=60,
        )
        if r.status_code != 200:
            logger.warning("set_refer_audio: %s", r.text[:200])
    except Exception as exc:
        logger.warning("set_refer_audio 失败（可继续）: %s", exc)


def speak(
    text: str,
    block: bool = True,
    on_status: Callable[[str], None] | None = None,
) -> None:
    cleaned = clean_for_tts(text)
    if not cleaned:
        raise RuntimeError("播报文本为空")
    if not GPT_SOVITS_REFERENCE_WAV.is_file():
        raise RuntimeError(f"参考音频不存在: {GPT_SOVITS_REFERENCE_WAV}")

    def _emit(msg: str) -> None:
        if on_status:
            on_status(msg)

    ensure_api_running(on_status=on_status)
    _emit("GPT-SoVITS 合成中…")

    payload = {
        "text": cleaned,
        "text_lang": GPT_SOVITS_TEXT_LANG,
        "ref_audio_path": str(GPT_SOVITS_REFERENCE_WAV.resolve()),
        "prompt_text": GPT_SOVITS_PROMPT_TEXT,
        "prompt_lang": GPT_SOVITS_PROMPT_LANG,
        "text_split_method": "cut5",
        "media_type": "wav",
        "streaming_mode": False,
    }
    r = requests.post(f"{_api_base()}/tts", json=payload, timeout=GPT_SOVITS_API_TIMEOUT)
    if r.status_code != 200:
        try:
            err = r.json()
        except Exception:
            err = r.text[:300]
        raise RuntimeError(f"GPT-SoVITS 合成失败: {err}")

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out = Path(tmp.name)
        out.write_bytes(r.content)

    try:
        _emit("正在播放…")
        from ai.audio_io import play_wav

        play_wav(str(out))
    finally:
        out.unlink(missing_ok=True)
