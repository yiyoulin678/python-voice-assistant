"""文本智能处理（transformers + 规则兜底）。"""
from __future__ import annotations

import logging
import re
from typing import Any

from ai.config import NLP_QA_MODEL

logger = logging.getLogger(__name__)

_qa_pipeline: Any = None


class ProcessMode:
    QA = "qa"
    SUMMARY = "summary"
    KEYWORDS = "keywords"
    STUDY_TIP = "study_tip"


class TextProcessError(Exception):
    """文本处理业务异常。"""


# 课设演示用本地知识片段（transformers 失败或无时使用）
_KNOWLEDGE: dict[str, str] = {
    "死锁": (
        "死锁是指两个或多个进程在执行过程中，因争夺资源而造成的一种互相等待的现象。"
        "若无外力干涉，它们都将无法推进。产生死锁通常需要互斥、占有且等待、不可抢占、循环等待四个条件。"
    ),
    "进程": "进程是操作系统进行资源分配和调度的基本单位，是程序在计算机上的一次执行过程。",
    "线程": "线程是进程内的执行单元，同一进程的线程共享地址空间，切换开销通常小于进程。",
    "python": (
        "Python 是一种解释型、面向对象的高级编程语言，语法简洁，常用于 Web、数据分析、人工智能等领域。"
    ),
}


def preload_nlp() -> None:
    """预加载 NLP 模型（可选，失败不抛错，将使用规则兜底）。"""
    try:
        _load_qa_pipeline()
    except TextProcessError as exc:
        logger.warning("NLP 模型预加载失败，将使用规则兜底: %s", exc)


def _load_qa_pipeline() -> Any:
    global _qa_pipeline
    if _qa_pipeline is not None:
        return _qa_pipeline

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise TextProcessError(
            "未安装 transformers，请执行: pip install transformers sentencepiece"
        ) from exc

    logger.info("正在加载 NLP 模型（首次可能需下载）…")
    try:
        _qa_pipeline = pipeline(
            "question-answering",
            model=NLP_QA_MODEL,
            tokenizer=NLP_QA_MODEL,
        )
    except Exception as exc:
        raise TextProcessError(f"加载 NLP 模型失败: {exc}") from exc

    logger.info("NLP 模型已就绪")
    return _qa_pipeline


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _rule_answer(question: str) -> str | None:
    q = question.lower()
    for key, answer in _KNOWLEDGE.items():
        if key.lower() in q or key in question:
            return answer
    return None


def _rule_keywords(text: str) -> str:
    stop = {"什么", "是", "的", "吗", "呢", "请", "如何", "怎么", "a", "the", "is"}
    words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", text)
    picked = [w for w in words if w.lower() not in stop and len(w) > 1]
    if not picked:
        picked = words[:5]
    return "关键词：" + "、".join(picked[:8]) if picked else "未能提取明显关键词。"


def _rule_summary(text: str) -> str:
    text = _normalize(text)
    if len(text) <= 80:
        return f"摘要：{text}"
    return f"摘要：{text[:80]}…（共 {len(text)} 字）"


def _rule_study_tip(text: str) -> str:
    return (
        f"针对「{text[:30]}{'…' if len(text) > 30 else ''}」的学习建议："
        "1) 先查阅教材对应章节；2) 用思维导图整理概念；"
        "3) 完成 2～3 道相关练习题；4) 向同学或老师复述一遍以巩固记忆。"
    )


def _transformers_qa(question: str, context: str) -> str | None:
    try:
        pipe = _load_qa_pipeline()
        out = pipe(question=question, context=context)
        ans = (out.get("answer") or "").strip()
        score = float(out.get("score") or 0)
        if ans and score >= 0.05:
            return ans
    except TextProcessError:
        raise
    except Exception as exc:
        logger.warning("transformers 问答失败: %s", exc)
    return None


def _build_context(question: str) -> str:
    parts = [f"用户问题：{question}"]
    for answer in _KNOWLEDGE.values():
        parts.append(answer)
    return "\n".join(parts)


def process_text(text: str, mode: str = ProcessMode.QA) -> str:
    """对文本进行智能处理，返回回复字符串。"""
    text = _normalize(text)
    if not text:
        raise TextProcessError("输入文本为空。")

    if mode == ProcessMode.KEYWORDS:
        return _rule_keywords(text)

    if mode == ProcessMode.SUMMARY:
        return _rule_summary(text)

    if mode == ProcessMode.STUDY_TIP:
        return _rule_study_tip(text)

    if mode != ProcessMode.QA:
        raise TextProcessError(f"未知处理模式: {mode}")

    ruled = _rule_answer(text)
    if ruled:
        return ruled

    try:
        ctx = _build_context(text)
        ml = _transformers_qa(text, ctx)
        if ml:
            return ml
    except TextProcessError:
        pass

    return (
        f"已收到你的问题：「{text}」。"
        "当前为课设演示模式：未在本地知识库命中，且深度学习模型未返回有效答案。"
        "建议将问题拆成更短的关键词，或联系管理员扩充知识库。"
    )
