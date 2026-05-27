"""通过 WebUI 自带 Python 启动 Qwen3-TTS 常驻子进程。"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

from ai import config as ai_config
from ai.tts.backends.qwen_tts_engine import QwenTTSEngineError
from ai.tts.backends.qwen_tts_webui_env import webui_python_exe

_daemon_proc: subprocess.Popen | None = None
_io_lock = threading.Lock()


def _daemon_script() -> Path:
    return ai_config.PROJECT_ROOT / "scripts" / "qwen_tts_daemon.py"


def _creationflags() -> int:
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW
    return 0


def _ensure_daemon() -> subprocess.Popen:
    global _daemon_proc
    py = webui_python_exe()
    if py is None:
        raise QwenTTSEngineError("未配置有效的 Qwen TTS WebUI 路径或 python.exe")

    if _daemon_proc is not None and _daemon_proc.poll() is None:
        return _daemon_proc

    script = _daemon_script()
    if not script.is_file():
        raise QwenTTSEngineError(f"缺少守护脚本: {script}")

    _daemon_proc = subprocess.Popen(
        [str(py), str(script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=str(ai_config.PROJECT_ROOT),
        creationflags=_creationflags(),
    )
    resp = _request_unlocked({"cmd": "ping"}, proc=_daemon_proc)
    if not resp.get("ok"):
        err = resp.get("error", "守护进程启动失败")
        _stop_daemon()
        raise QwenTTSEngineError(err)
    return _daemon_proc


def _stop_daemon() -> None:
    global _daemon_proc
    if _daemon_proc is None:
        return
    try:
        if _daemon_proc.poll() is None:
            _daemon_proc.terminate()
            _daemon_proc.wait(timeout=5)
    except Exception:
        pass
    _daemon_proc = None


def _request_unlocked(payload: dict, *, proc: subprocess.Popen) -> dict:
    if proc.stdin is None or proc.stdout is None:
        raise QwenTTSEngineError("守护进程管道不可用")
    proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        stderr = (proc.stderr.read() if proc.stderr else "") or ""
        raise QwenTTSEngineError(f"守护进程无响应{(': ' + stderr.strip()) if stderr else ''}")
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise QwenTTSEngineError(f"守护进程返回无效 JSON: {line!r}") from exc


def request(payload: dict) -> dict:
    with _io_lock:
        proc = _ensure_daemon()
        resp = _request_unlocked(payload, proc=proc)
        if proc.poll() is not None:
            _stop_daemon()
            raise QwenTTSEngineError("Qwen TTS 守护进程已退出，请重试")
        if not resp.get("ok"):
            raise QwenTTSEngineError(resp.get("error", "未知错误"))
        return resp
