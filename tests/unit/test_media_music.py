from __future__ import annotations

import pytest

from app.media.music import build_music_search_url, normalize_music_source, open_music_search


def test_build_music_search_url_netease() -> None:
    url = build_music_search_url("晴天 周杰伦", "netease")
    assert "music.163.com" in url
    assert "%E6%99%B4" in url or "晴天" in url


def test_build_music_search_url_qq() -> None:
    url = build_music_search_url("稻香", "qq")
    assert "y.qq.com" in url


def test_normalize_music_source_aliases() -> None:
    assert normalize_music_source("网易云") == "netease"
    assert normalize_music_source("q音") == "qq"


def test_open_music_search_requires_query() -> None:
    with pytest.raises(ValueError):
        open_music_search({})
