from __future__ import annotations

import importlib
from typing import Any

_LIVE2D_MODULE: Any | None = None
_LIVE2D_INITIALIZED = False
_IMPORT_ERROR: str | None = None


def is_live2d_available() -> bool:
    """是否已安装 live2d-py 且可导入。"""
    _ensure_import()
    return _LIVE2D_MODULE is not None


def live2d_import_error() -> str | None:
    _ensure_import()
    return _IMPORT_ERROR


def get_live2d_module() -> Any:
    _ensure_import()
    if _LIVE2D_MODULE is None:
        raise RuntimeError(_IMPORT_ERROR or "live2d-py 未安装")
    return _LIVE2D_MODULE


def ensure_live2d_init() -> None:
    global _LIVE2D_INITIALIZED
    module = get_live2d_module()
    if not _LIVE2D_INITIALIZED:
        module.init()
        _LIVE2D_INITIALIZED = True


def dispose_live2d() -> None:
    global _LIVE2D_INITIALIZED
    if not _LIVE2D_INITIALIZED or _LIVE2D_MODULE is None:
        return
    _LIVE2D_MODULE.dispose()
    _LIVE2D_INITIALIZED = False


def _ensure_import() -> None:
    global _LIVE2D_MODULE, _IMPORT_ERROR
    if _LIVE2D_MODULE is not None or _IMPORT_ERROR is not None:
        return
    try:
        _LIVE2D_MODULE = importlib.import_module("live2d.v3")
    except ImportError as exc:
        _IMPORT_ERROR = (
            f"未安装 live2d-py：{exc}。"
            "请执行：runtime\\python.exe -m pip install -r requirements-live2d.txt"
        )
