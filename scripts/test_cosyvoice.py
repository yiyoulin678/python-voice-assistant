"""快速检测 CosyVoice 是否可用。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.config import COSYVOICE_REFERENCE_WAV, COSYVOICE_ROOT
from ai.tts.backends import cosyvoice_backend
from ai.tts.speaker import get_tts_backend_name


def main() -> int:
    print("参考音频:", COSYVOICE_REFERENCE_WAV, "存在=", COSYVOICE_REFERENCE_WAV.is_file())
    print("CosyVoice 根目录:", COSYVOICE_ROOT, "存在=", COSYVOICE_ROOT.is_dir())
    print("当前 TTS 后端:", get_tts_backend_name())
    if not cosyvoice_backend.is_available():
        print("未就绪，见 docs/SETUP_LLM_TTS.md")
        return 1
    print("尝试合成短句（CPU 可能需 1～3 分钟）…")
    cosyvoice_backend.speak("你好，我是小音。", block=True)
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
