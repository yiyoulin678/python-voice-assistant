"""Qwen TTS WebUI 整合包环境（ModelScope 缓存等）。"""
from __future__ import annotations

import os
from pathlib import Path

from ai import config as ai_config


def webui_root() -> Path | None:
    root = ai_config.QWEN_TTS_WEBUI_ROOT
    if root is None:
        return None
    return root if root.is_dir() else None


def webui_python_exe() -> Path | None:
    root = webui_root()
    if root is None:
        return None
    exe = ai_config.QWEN_TTS_PYTHON_EXE
    if exe is None:
        exe = root / "python" / "python.exe"
    return exe if exe.is_file() else None


def resolve_model_path(model_id: str) -> str:
    """若 WebUI 缓存里已有模型，返回本地目录路径，避免在线校验卡住。"""
    root = webui_root()
    if not root or "/" not in model_id:
        return model_id
    org, name = model_id.split("/", 1)
    models_root = root / "cache" / "modelscope" / "hub" / "models" / org
    if not models_root.is_dir():
        return model_id
    exact = models_root / name.replace(".", "___")
    if exact.is_dir():
        return str(exact.resolve())
    key = name.lower().replace(".", "").replace("-", "")
    for child in models_root.iterdir():
        if not child.is_dir():
            continue
        ckey = child.name.lower().replace("___", ".").replace("_", "").replace("-", "")
        if key in ckey or ckey in key:
            return str(child.resolve())
    return model_id


def apply_webui_env() -> None:
    """让 from_pretrained 优先使用 WebUI 已下载的 ModelScope 模型。"""
    root = webui_root()
    if root is None:
        return
    ms_cache = root / "cache" / "modelscope"
    if ms_cache.is_dir():
        os.environ["MODELSCOPE_CACHE"] = str(ms_cache.resolve())
    hf_cache = root / "cache" / "huggingface"
    if hf_cache.is_dir():
        os.environ.setdefault("HF_HOME", str(hf_cache.resolve()))
