from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.builtin_tools import _builtin_fetch_url, _builtin_web_search, create_builtin_tool_registry


def test_create_builtin_tool_registry_includes_web_tools() -> None:
    registry = create_builtin_tool_registry(Path(__file__).resolve().parents[2])
    names = {tool.name for tool in registry.all()}
    assert "web_search" in names
    assert "fetch_url" in names


def test_builtin_web_search_delegates_to_search_web(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_search(query: str, max_results: int = 5) -> dict[str, object]:
        captured["query"] = query
        captured["max_results"] = max_results
        return {"query": query, "results": []}

    monkeypatch.setattr("app.agent.builtin_tools.search_web", fake_search)

    payload = _builtin_web_search({"query": "Python 3.13", "max_results": 3})

    assert captured == {"query": "Python 3.13", "max_results": 3}
    assert payload["query"] == "Python 3.13"


def test_builtin_fetch_url_delegates_to_fetch_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_fetch(url: str, max_chars: int = 6000) -> dict[str, object]:
        captured["url"] = url
        captured["max_chars"] = max_chars
        return {"url": url, "text": "hello"}

    monkeypatch.setattr("app.agent.builtin_tools.fetch_public_url", fake_fetch)

    payload = _builtin_fetch_url(
        {"url": "https://example.com/docs", "max_chars": 1200}
    )

    assert captured == {"url": "https://example.com/docs", "max_chars": 1200}
    assert payload["text"] == "hello"


def test_builtin_web_search_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="数值参数"):
        _builtin_web_search({"query": "test", "max_results": "five"})
