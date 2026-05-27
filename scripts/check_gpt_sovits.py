"""检查 GPT-SoVITS API 是否可用。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import GPT_SOVITS_API_URL, GPT_SOVITS_REFERENCE_WAV, GPT_SOVITS_ROOT
from ai.tts.backends import gpt_sovits_backend


def main() -> int:
    print("API:", GPT_SOVITS_API_URL)
    print("安装目录:", GPT_SOVITS_ROOT or "(未配置 install_dir)")
    print("参考音频:", GPT_SOVITS_REFERENCE_WAV, "存在=", GPT_SOVITS_REFERENCE_WAV.is_file())

    if not gpt_sovits_backend.is_available():
        print("[X] 不可用。请配置 gpt_sovits.install_dir 并放置 reference.wav")
        return 1

    try:
        gpt_sovits_backend.ensure_api_running()
        print("[OK] API 已运行")
        gpt_sovits_backend.warmup()
        print("[OK] 参考音频已注册")
        gpt_sovits_backend.speak("你好，我是小音。", block=True)
        print("[OK] 试听完成")
        return 0
    except Exception as exc:
        print("[X]", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
