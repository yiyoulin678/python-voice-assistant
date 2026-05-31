"""检查 VoxCPM 是否可用。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import VOXCPM_MODEL_ID, VOXCPM_MODE, VOXCPM_REPO_ROOT
from ai.tts.backends import voxcpm_backend


def main() -> int:
    print("模式:", VOXCPM_MODE)
    print("模型:", VOXCPM_MODEL_ID)
    print("仓库:", VOXCPM_REPO_ROOT, "存在" if VOXCPM_REPO_ROOT.is_dir() else "缺失")
    if not voxcpm_backend.is_available():
        print("[X] 请执行: powershell -File scripts/install_voxcpm.ps1")
        return 1
    try:
        voxcpm_backend.warmup()
        print("[OK] 模型已加载")
        voxcpm_backend.speak("你好，我是小音，很高兴认识你。", block=True)
        print("[OK] 试听完成")
        return 0
    except Exception as exc:
        print("[X]", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
