from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "network: 需要访问外网（网易云等），CI 默认跳过",
    )


@pytest.fixture(autouse=True)
def _ci_disable_mem0_background_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """GitHub Actions 不后台加载 mem0/HuggingFace，避免拖垮 Qt 测试。"""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    from app.agent.memory import MemoryStore

    def _noop_preload(self: MemoryStore, *, wait: bool = False) -> None:
        _ = wait

    monkeypatch.setattr(MemoryStore, "preload", _noop_preload)
