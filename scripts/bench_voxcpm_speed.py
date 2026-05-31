"""测量 VoxCPM 合成耗时（不含播放）。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch

from ai.config import (
    VOXCPM_INFERENCE_TIMESTEPS,
    VOXCPM_MODEL_ID,
    VOXCPM_MODE,
    VOXCPM_RETRY_BADCASE,
)
from ai.tts.backends.voxcpm_engine import VoxCPMEngine


def main() -> int:
    print("CUDA:", torch.cuda.is_available(), end="")
    if torch.cuda.is_available():
        print(f" ({torch.cuda.get_device_name(0)})")
    else:
        print()
    print("模型:", VOXCPM_MODEL_ID)
    print("模式:", VOXCPM_MODE)
    print("timesteps:", VOXCPM_INFERENCE_TIMESTEPS, "retry_badcase:", VOXCPM_RETRY_BADCASE)

    engine = VoxCPMEngine.get()
    texts = [
        "你好。",
        "你好，我是小音。",
        "今天天气不错，我们一起聊聊天吧。",
    ]

    t0 = time.perf_counter()
    engine.warmup(lambda m: print("  warmup:", m))
    load_s = time.perf_counter() - t0
    print(f"\n[加载+预热] {load_s:.2f}s")

    print("\n--- 纯合成耗时（不含播放）---")
    ok_5s = 0
    for text in texts:
        t1 = time.perf_counter()
        audio, sr = engine.speak(text)
        synth_s = time.perf_counter() - t1
        dur = len(audio) / sr
        rtf = synth_s / dur if dur > 0 else float("inf")
        flag = "OK" if synth_s <= 5.0 else "SLOW"
        if synth_s <= 5.0:
            ok_5s += 1
        print(
            f"{flag} 「{text}」"
            f"  合成 {synth_s:.2f}s | 音频 {dur:.2f}s | RTF {rtf:.2f}"
        )

    print(f"\n结论: {ok_5s}/{len(texts)} 条在 5s 内完成合成")
    return 0 if ok_5s == len(texts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
