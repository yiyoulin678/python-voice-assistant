"""Ollama 本地 API 客户端（qwen2.5:3b）。"""
from __future__ import annotations

import logging
from typing import Any

import requests

from ai.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Ollama 调用失败。"""


def is_available(base_url: str | None = None, timeout: float = 3) -> bool:
    url = (base_url or OLLAMA_BASE_URL).rstrip("/")
    try:
        r = requests.get(f"{url}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def get_status_label() -> str:
    """供 GUI 展示：Ollama 与目标模型是否就绪。"""
    from ai.config import OLLAMA_MODEL

    if not is_available():
        return "Ollama 未运行"
    if not ensure_model_pulled():
        return f"缺少模型 {OLLAMA_MODEL}"
    return f"Ollama · {OLLAMA_MODEL}"


def ensure_model_pulled(model: str | None = None, base_url: str | None = None) -> bool:
    """检查模型是否在 ollama list 中。"""
    name = model or OLLAMA_MODEL
    url = (base_url or OLLAMA_BASE_URL).rstrip("/")
    try:
        r = requests.get(f"{url}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return any(name in m or m.startswith(name) for m in models)
    except Exception as exc:
        logger.warning("检查 Ollama 模型列表失败: %s", exc)
        return False


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
) -> str:
    url = (base_url or OLLAMA_BASE_URL).rstrip("/")
    payload: dict[str, Any] = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    try:
        r = requests.post(
            f"{url}/api/chat",
            json=payload,
            timeout=timeout or OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        content = (data.get("message") or {}).get("content", "").strip()
        if not content:
            raise OllamaError("Ollama 返回空回复")
        return content
    except OllamaError:
        raise
    except requests.RequestException as exc:
        raise OllamaError(
            f"无法连接 Ollama（{url}）。请先安装并运行: ollama serve，再执行 ollama pull qwen2.5:3b"
        ) from exc
    except Exception as exc:
        raise OllamaError(f"Ollama 调用异常: {exc}") from exc
