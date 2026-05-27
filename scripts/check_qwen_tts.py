"""检查 Qwen3-TTS 是否可用。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import (
    QWEN_TTS_CLONE_MODEL_ID,
    QWEN_TTS_MODEL_ID,
    QWEN_TTS_MODE,
    QWEN_TTS_SPEAKER,
    QWEN_TTS_WEBUI_ROOT,
)
from ai.tts.backends import qwen_tts_backend


def main() -> int:
    print("模式:", QWEN_TTS_MODE)
    print("模型:", QWEN_TTS_MODEL_ID if QWEN_TTS_MODE != "clone" else QWEN_TTS_CLONE_MODEL_ID)
    print("WebUI:", QWEN_TTS_WEBUI_ROOT or "(未配置)")
    print("说话人:", QWEN_TTS_SPEAKER)
    if not qwen_tts_backend.is_available():
        print("[X] 请执行: pip install qwen-tts")
        return 1
    try:
        qwen_tts_backend.warmup()
        print("[OK] 模型已加载")
        qwen_tts_backend.speak("你好，我是小音，很高兴认识你。", block=True)
        print("[OK] 试听完成")
        return 0
    except Exception as exc:
        print("[X]", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
