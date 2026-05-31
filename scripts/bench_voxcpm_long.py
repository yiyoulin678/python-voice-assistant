"""长句 VoxCPM 合成测速（不含播放）。"""
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
    VOXCPM_RETRY_BADCASE,
    VOXCPM_TTS_MAX_CHARS,
)
from ai.tts.backends.voxcpm_engine import VoxCPMEngine
from ai.tts.text_clean import clean_for_tts


def main() -> int:
    texts: list[tuple[str, str]] = [
        ("短句", "你好，我是小音。"),
        ("中句", "今天心情特别好呢，刚才还在想你，你要是有空的话我们可以多聊一会儿。"),
        (
            "长句",
            "其实我一直都在这里陪着你哦，不管你开心还是难过都可以跟我说，"
            "我会认真听你说的每一句话，然后尽量用温柔的声音回应你。",
        ),
        (
            "上限120字",
            "嗯嗯，我知道啦。你刚才说的那些我都听进去了，虽然有时候我可能理解得不够完美，"
            "但我会一直努力做好你的小音。以后你想聊天、想倾诉、或者只是随便说说话，"
            "都可以来找我，我会尽量让每一次对话都让你觉得温暖和被在乎。",
        ),
        (
            "LLM回复1",
            "没关系的，慢慢来就好。你已经做得很好了，不要给自己太大压力，"
            "有什么烦恼都可以跟我说，我会一直在这里陪着你。",
        ),
        (
            "LLM回复2",
            "哈哈，你这样说我会害羞的啦。不过听到你这么说真的很开心，"
            "今晚也要早点休息，记得好好照顾自己，明天我们再聊。",
        ),
    ]

    print("CUDA:", torch.cuda.is_available(), end="")
    if torch.cuda.is_available():
        print(f" ({torch.cuda.get_device_name(0)})")
    else:
        print()
    print("model:", VOXCPM_MODEL_ID)
    print("timesteps:", VOXCPM_INFERENCE_TIMESTEPS, "retry_badcase:", VOXCPM_RETRY_BADCASE)
    print("tts_max_chars:", VOXCPM_TTS_MAX_CHARS)

    engine = VoxCPMEngine.get()
    t0 = time.perf_counter()
    engine.warmup()
    print(f"warmup: {time.perf_counter() - t0:.2f}s\n")

    print(f"{'标签':<12} {'字数':>4} {'合成s':>7} {'音频s':>7} {'RTF':>6} {'<=5s':>5}")
    print("-" * 52)

    ok_5s = 0
    rtf_sum = 0.0
    for label, text in texts:
        cleaned = clean_for_tts(text, max_len=VOXCPM_TTS_MAX_CHARS)
        t1 = time.perf_counter()
        audio, sr = engine.speak(text)
        synth_s = time.perf_counter() - t1
        dur = len(audio) / sr
        rtf = synth_s / dur if dur > 0 else float("inf")
        rtf_sum += rtf
        flag = "Y" if synth_s <= 5.0 else "N"
        if synth_s <= 5.0:
            ok_5s += 1
        print(f"{label:<12} {len(cleaned):>4} {synth_s:>7.2f} {dur:>7.2f} {rtf:>6.2f} {flag:>5}")

    print("-" * 52)
    print(f"5秒内完成: {ok_5s}/{len(texts)}")
    print(f"平均RTF: {rtf_sum / len(texts):.2f}  (RTF<1 表示合成比实时播放快)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
