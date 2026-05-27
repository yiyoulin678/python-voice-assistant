"""规则 / 知识库兜底（Ollama 不可用时）。"""
from __future__ import annotations

import re

_KNOWLEDGE: dict[str, str] = {
    "死锁": (
        "死锁是指多个进程互相等待资源导致都无法推进的状态。"
        "一般需要互斥、占有且等待、不可抢占和循环等待四个条件同时成立。"
    ),
    "进程": "进程是操作系统调度与分配资源的基本单位。",
    "线程": "线程是进程里的执行单元，同一进程内线程共享地址空间。",
    "python": "Python 是简洁易学的编程语言，常用于 AI、Web 和自动化。",
}

_EMOTION_REPLIES: list[tuple[tuple[str, ...], str]] = [
    (("难过", "伤心", "不开心", "郁闷", "累", "疲惫", "压力大"), "抱抱你～今天辛苦了，慢慢来，我在呢。想说的话都可以跟我讲。"),
    (("开心", "高兴", "哈哈", "太好了"), "哇，听你这么说我也开心！要不要多跟我讲讲呀？"),
    (
        ("你好", "嗨", "在吗", "hello", "hi", "hey", "ciallo", "ciao", "早上好", "晚上好", "午安"),
        "在呀在呀～我是小音，今天想聊点什么？",
    ),
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def rule_answer(text: str) -> str | None:
    q = text.lower()
    for key, answer in _KNOWLEDGE.items():
        if key.lower() in q or key in text:
            return answer
    for keys, reply in _EMOTION_REPLIES:
        if any(k in text for k in keys):
            return reply
    return None


def rule_keywords(text: str) -> str:
    stop = {"什么", "是", "的", "吗", "呢", "请", "如何", "怎么"}
    words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", text)
    picked = [w for w in words if w.lower() not in stop and len(w) > 1]
    return "关键词：" + "、".join(picked[:8]) if picked else "暂时没抓到明显关键词呢～"


def rule_summary(text: str) -> str:
    text = normalize(text)
    if len(text) <= 80:
        return f"我帮你概括一下：{text}"
    return f"我帮你概括一下：{text[:80]}…（原文比较长哦）"


def rule_study_tip(text: str) -> str:
    return (
        f"关于「{text[:24]}{'…' if len(text) > 24 else ''}」，我建议你先翻教材对应章节，"
        "再做几道练习题，最后用自己的话讲一遍，会记得更牢～需要我陪你梳理也可以说。"
    )


def generic_fallback(text: str) -> str:
    return (
        f"嗯嗯，我听到你说「{text[:40]}{'…' if len(text) > 40 else ''}」啦。"
        "我这边暂时连不上大模型，但我会陪着你；你可以换种说法，或者问学习相关的问题试试～"
    )
