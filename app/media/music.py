from __future__ import annotations

import webbrowser
from typing import Any
from urllib.parse import quote

from app.media.keys import send_media_key


SUPPORTED_MUSIC_SOURCES = ("netease", "qq")
DEFAULT_MUSIC_SOURCE = "netease"


def normalize_music_source(source: str | None) -> str:
    normalized = str(source or DEFAULT_MUSIC_SOURCE).strip().lower()
    if normalized in {"163", "netease", "wangyiyun", "网易云"}:
        return "netease"
    if normalized in {"qq", "qqmusic", "q音"}:
        return "qq"
    return DEFAULT_MUSIC_SOURCE


def build_music_search_url(query: str, source: str | None = None) -> str:
    text = str(query).strip()
    if not text:
        raise ValueError("搜索关键词不能为空。")
    encoded = quote(text)
    if normalize_music_source(source) == "qq":
        return f"https://y.qq.com/n/ryqq/search?w={encoded}"
    return f"https://music.163.com/#/search/m/?s={encoded}"


def open_music_search(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query") or arguments.get("keyword") or "").strip()
    if not query:
        raise ValueError("缺少 query。")
    source = normalize_music_source(str(arguments.get("source") or ""))
    url = build_music_search_url(query, source)
    opened = webbrowser.open(url)
    return {
        "query": query,
        "source": source,
        "url": url,
        "opened": bool(opened),
    }


def media_play_pause(_arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return send_media_key("play_pause")


def media_next_track(_arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return send_media_key("next")


def media_previous_track(_arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return send_media_key("previous")
