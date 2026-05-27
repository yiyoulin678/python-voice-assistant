"""TTS 前清洗 LLM 回复，减少 CosyVoice 乱读。"""
from __future__ import annotations

import re


def clean_for_tts(text: str, max_len: int = 180) -> str:
    if not text:
        return ""
    t = text.strip()
    # 去掉 emoji、markdown、多余空白
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)
    t = re.sub(r"[*#`_~]", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    t = t.strip()
    if not t:
        return ""
    # 无标点时补句号，利于中文分句
    if t[-1] not in "。！？；.!?…":
        t += "。"
    if len(t) > max_len:
        cut = t[:max_len]
        for sep in ("。", "！", "？", "；", ".", "!", "?"):
            idx = cut.rfind(sep)
            if idx > max_len // 2:
                cut = cut[: idx + 1]
                break
        t = cut
    return t
