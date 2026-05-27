"""Qwen3-TTS 常驻子进程（使用 WebUI 自带 Python + 本地模型缓存）。"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QWEN_TTS_IN_DAEMON"] = "1"

from ai.tts.backends.qwen_tts_webui_env import apply_webui_env

apply_webui_env()

from ai.tts.backends.qwen_tts_engine import QwenTTSEngine, QwenTTSEngineError  # noqa: E402


def _ok(**payload) -> dict:
    return {"ok": True, **payload}


def _err(msg: str) -> dict:
    return {"ok": False, "error": msg}


def _handle(req: dict) -> dict:
    cmd = req.get("cmd")
    engine = QwenTTSEngine.get()
    try:
        if cmd == "ping":
            return _ok()
        if cmd == "warmup":
            engine.warmup()
            return _ok()
        if cmd == "set_reference":
            path = engine.set_reference(
                req["wav_path"],
                req.get("prompt_text"),
                copy_to_project=bool(req.get("copy_to_project", True)),
            )
            return _ok(ref_path=str(path))
        if cmd == "speak":
            import soundfile as sf

            audio, sr = engine.speak(req["text"])
            out = Path(req["output_wav"])
            out.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(out), audio, sr)
            return _ok(output_wav=str(out), sample_rate=sr)
        return _err(f"未知命令: {cmd}")
    except QwenTTSEngineError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"{exc}\n{traceback.format_exc()}")


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            resp = _err(f"JSON 解析失败: {exc}")
        else:
            resp = _handle(req)
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
