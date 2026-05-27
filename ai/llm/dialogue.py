"""对话入口：优先 Ollama，失败则规则兜底。"""
from __future__ import annotations

import logging

from ai.llm import fallback, ollama_client, persona
from ai.llm.history import get_history

logger = logging.getLogger(__name__)


class DialogueError(Exception):
    """对话模块业务异常。"""


class ProcessMode:
    QA = "qa"
    SUMMARY = "summary"
    KEYWORDS = "keywords"
    STUDY_TIP = "study_tip"


def clear_history() -> None:
    get_history().clear()


def preload_dialogue() -> None:
    """检查 Ollama；不阻塞启动。"""
    from ai.config import OLLAMA_MODEL

    if ollama_client.is_available():
        if ollama_client.ensure_model_pulled():
            logger.info("Ollama 已就绪，模型: %s", OLLAMA_MODEL)
        else:
            logger.warning(
                "Ollama 已运行但未找到模型 %s，请执行: ollama pull %s",
                OLLAMA_MODEL,
                OLLAMA_MODEL,
            )
    else:
        logger.warning("Ollama 未运行，对话将使用规则兜底")


def process_dialogue(
    text: str,
    mode: str = ProcessMode.QA,
    user_nickname: str = "你",
) -> str:
    text = fallback.normalize(text)
    if not text:
        raise DialogueError("输入为空")

    if mode == ProcessMode.KEYWORDS:
        return fallback.rule_keywords(text)
    if mode == ProcessMode.SUMMARY:
        return fallback.rule_summary(text)
    if mode == ProcessMode.STUDY_TIP:
        return fallback.rule_study_tip(text)

    ruled = fallback.rule_answer(text)
    if ruled and _looks_like_factual_question(text):
        get_history().add(text, ruled)
        return ruled

    if ollama_client.is_available():
        try:
            hist = get_history()
            messages = persona.build_messages(
                text,
                user_nickname=user_nickname,
                history=hist.to_ollama_messages(),
            )
            reply = ollama_client.chat(messages)
            hist.add(text, reply)
            return reply
        except ollama_client.OllamaError as exc:
            logger.warning("Ollama 失败，使用兜底: %s", exc)

    if ruled:
        get_history().add(text, ruled)
        return ruled
    reply = fallback.generic_fallback(text)
    get_history().add(text, reply)
    return reply


def _looks_like_factual_question(text: str) -> bool:
    keys = ("什么是", "是什么", "为什么", "如何", "怎么", "死锁", "进程", "线程")
    return any(k in text for k in keys)
