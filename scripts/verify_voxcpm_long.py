"""可复现的长句测速（写入结果文件，避免终端编码干扰）。"""
from __future__ import annotations

import json
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

OUT = ROOT / "logs" / "voxcpm_long_verify.json"


def main() -> int:
    texts: list[tuple[str, str]] = [
        ("short_8", "你好，我是小音。"),
        ("mid_33", "今天心情特别好呢，刚才还在想你，你要是有空的话我们可以多聊一会儿。"),
        ("long_57", "其实我一直都在这里陪着你哦，不管你开心还是难过都可以跟我说，我会认真听你说的每一句话，然后尽量用温柔的声音回应你。"),
    ]

    engine = VoxCPMEngine.get()
    t0 = time.perf_counter()
    engine.warmup()
    warmup_s = time.perf_counter() - t0

    rows: list[dict] = []
    for label, text in texts:
        cleaned = clean_for_tts(text, max_len=VOXCPM_TTS_MAX_CHARS)
        row: dict = {"label": label, "input_chars": len(cleaned), "error": None}
        try:
            t1 = time.perf_counter()
            audio, sr = engine.speak(text)
            synth_s = time.perf_counter() - t1
            dur = float(len(audio) / sr)
            row.update(
                {
                    "synth_s": round(synth_s, 2),
                    "audio_s": round(dur, 2),
                    "rtf": round(synth_s / dur, 3) if dur > 0 else None,
                    "under_5s": synth_s <= 5.0,
                }
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    payload = {
        "cuda": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "model": VOXCPM_MODEL_ID,
        "timesteps": VOXCPM_INFERENCE_TIMESTEPS,
        "retry_badcase": VOXCPM_RETRY_BADCASE,
        "tts_max_chars": VOXCPM_TTS_MAX_CHARS,
        "warmup_s": round(warmup_s, 2),
        "results": rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
