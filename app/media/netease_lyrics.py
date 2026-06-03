from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any

from app.media.lrc_parser import parse_synced_lyrics, split_plain_lyrics

_NETEASE_SEARCH_URL = "https://music.163.com/api/search/get/web"
_NETEASE_LYRIC_URL = "https://music.163.com/api/song/lyric"
_REQUEST_TIMEOUT_SECONDS = 15
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://music.163.com/",
}


def fetch_netease_track_lyrics(
    title: str,
    artist: str,
    *,
    album: str = "",
    duration_hint: float = 0,
) -> object | None:
    from app.media.lyrics_fetcher import TrackLyrics
    title = title.strip()
    artist = artist.strip()
    if not title and not artist:
        return None
    if not title:
        title = artist
    elif not artist:
        artist = title

    song = _search_best_song(title, artist)
    if song is None:
        return None

    synced_text, plain_text = _fetch_lyric_texts(int(song["id"]))
    synced = tuple(parse_synced_lyrics(synced_text)) if synced_text.strip() else ()
    plain = tuple(split_plain_lyrics(plain_text)) if plain_text.strip() else ()
    if not synced and not plain:
        return None

    duration_ms = song.get("duration") or 0
    duration_seconds = float(duration_ms) / 1000.0 if duration_ms else duration_hint
    artists = song.get("artists") or []
    artist_name = " / ".join(
        str(item.get("name", "")).strip() for item in artists if isinstance(item, dict)
    ).strip() or artist
    return TrackLyrics(
        title=str(song.get("name") or title),
        artist=artist_name,
        album=str(song.get("album", {}).get("name", "") if isinstance(song.get("album"), dict) else album),
        duration_seconds=duration_seconds,
        synced_lines=synced,
        plain_lines=plain,
    )


def _search_best_song(title: str, artist: str) -> dict[str, Any] | None:
    queries: list[str] = []
    if title and artist:
        queries.append(f"{title} {artist}")
        queries.append(title)
    elif title:
        queries.append(title)
    else:
        queries.append(artist)

    best: dict[str, Any] | None = None
    best_score = -1
    title_key = _normalize_key(title)
    artist_key = _normalize_key(artist)
    for query in queries:
        for song in _search_songs(query):
            score = _score_song(song, title_key=title_key, artist_key=artist_key)
            if score > best_score:
                best_score = score
                best = song
        if best is not None and best_score >= 25:
            break
    return best


def _search_songs(keyword: str) -> list[dict[str, Any]]:
    params = {
        "csrf_prevent_token": "",
        "type": "1",
        "s": keyword.strip(),
        "limit": "8",
    }
    payload = _http_post_json(_NETEASE_SEARCH_URL, params)
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    songs = result.get("songs")
    if not isinstance(songs, list):
        return []
    return [song for song in songs if isinstance(song, dict)]


def _fetch_lyric_texts(song_id: int) -> tuple[str, str]:
    params = {"id": str(song_id), "lv": "1", "kv": "1", "tv": "1"}
    payload = _http_get_json(_NETEASE_LYRIC_URL, params)
    if not isinstance(payload, dict):
        return "", ""
    lrc_block = payload.get("lrc") if isinstance(payload.get("lrc"), dict) else {}
    tlyric_block = payload.get("tlyric") if isinstance(payload.get("tlyric"), dict) else {}
    synced = str(lrc_block.get("lyric") or "")
    plain = str(tlyric_block.get("lyric") or "")
    if not plain.strip():
        plain = _plain_from_synced(synced)
    return synced, plain


def _plain_from_synced(synced_text: str) -> str:
    lines: list[str] = []
    for raw in synced_text.splitlines():
        line = raw.strip()
        match = re.match(r"^\[\d+:\d+(?:\.\d+)?\](.*)$", line)
        if match:
            text = match.group(1).strip()
            if text:
                lines.append(text)
    return "\n".join(lines)


def _score_song(song: dict[str, Any], *, title_key: str, artist_key: str) -> int:
    name_key = _normalize_key(str(song.get("name") or ""))
    artists = song.get("artists") or []
    artist_names = " ".join(
        _normalize_key(str(item.get("name", ""))) for item in artists if isinstance(item, dict)
    )
    score = 0
    if title_key and (title_key in name_key or name_key in title_key):
        score += 30
    if artist_key and (artist_key in artist_names or any(part in artist_names for part in artist_key.split())):
        score += 20
    if title_key and artist_key and score >= 40:
        score += 10
    return score


def _normalize_key(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _http_get_json(base_url: str, params: dict[str, str]) -> object | None:
    query = urllib.parse.urlencode(params)
    url = f"{base_url}?{query}"
    request = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _http_post_json(base_url: str, params: dict[str, str]) -> object | None:
    body = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(base_url, data=body, headers=_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            text = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
