from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.brand import APP_USER_AGENT
from app.media.lrc_parser import parse_synced_lyrics, split_plain_lyrics


LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"
LRCLIB_GET_CACHED_URL = "https://lrclib.net/api/get-cached"
_REQUEST_TIMEOUT_SECONDS = 18
_lyrics_session_cache: dict[str, TrackLyrics] = {}


@dataclass(frozen=True)
class TrackLyrics:
    title: str
    artist: str
    album: str
    duration_seconds: float
    synced_lines: tuple[tuple[float, str], ...] = ()
    plain_lines: tuple[str, ...] = ()

    def has_synced(self) -> bool:
        return bool(self.synced_lines)

    def has_plain(self) -> bool:
        return bool(self.plain_lines)


def fetch_track_lyrics(
    title: str,
    artist: str,
    *,
    album: str = "",
    duration_hint: float = 0,
    music_source: str = "netease",
) -> TrackLyrics | None:
    title = title.strip()
    artist = artist.strip()
    album = album.strip()
    if not title and not artist:
        return None

    cache_key = f"{title.lower()}|{artist.lower()}|{music_source}"
    cached = _lyrics_session_cache.get(cache_key)
    if cached is not None:
        return cached

    source = str(music_source).strip().lower()
    if source == "netease":
        from app.media.netease_lyrics import fetch_netease_track_lyrics

        netease = fetch_netease_track_lyrics(
            title,
            artist,
            album=album,
            duration_hint=duration_hint,
        )
        if netease is not None:
            _lyrics_session_cache[cache_key] = netease
            return netease

    record = _search_best_match(title, artist, album)
    if record is None:
        record = _search_by_query(f"{title} {artist}".strip())
    if record is None and duration_hint > 0:
        record = _get_cached(title, artist, album, duration_hint)
    if record is None:
        return None

    synced_text = str(record.get("syncedLyrics") or "")
    plain_text = str(record.get("plainLyrics") or "")
    synced = tuple(parse_synced_lyrics(synced_text)) if synced_text.strip() else ()
    plain = tuple(split_plain_lyrics(plain_text)) if plain_text.strip() else ()
    if not synced and not plain:
        return None

    duration = _float_value(record.get("duration"), duration_hint)
    result = TrackLyrics(
        title=str(record.get("trackName") or title),
        artist=str(record.get("artistName") or artist),
        album=str(record.get("albumName") or album),
        duration_seconds=duration,
        synced_lines=synced,
        plain_lines=plain,
    )
    _lyrics_session_cache[cache_key] = result
    return result


def _search_by_query(query: str) -> dict[str, object] | None:
    query = query.strip()
    if not query:
        return None
    payload = _http_get_json(LRCLIB_SEARCH_URL, {"q": query})
    return _pick_best_lrclib_record(payload, title=query, artist="")


def _search_best_match(title: str, artist: str, album: str) -> dict[str, object] | None:
    params: dict[str, object] = {"track_name": title}
    if artist:
        params["artist_name"] = artist
    if album:
        params["album_name"] = album
    payload = _http_get_json(LRCLIB_SEARCH_URL, params)
    return _pick_best_lrclib_record(payload, title=title, artist=artist)


def _pick_best_lrclib_record(
    payload: object,
    *,
    title: str,
    artist: str,
) -> dict[str, object] | None:
    if not isinstance(payload, list) or not payload:
        return None

    best: dict[str, object] | None = None
    best_score = -1
    title_lower = title.lower()
    artist_lower = artist.lower()
    for item in payload:
        if not isinstance(item, dict):
            continue
        score = 0
        track_name = str(item.get("trackName") or "").lower()
        artist_name = str(item.get("artistName") or "").lower()
        if title_lower and (title_lower in track_name or track_name in title_lower):
            score += 20
        if artist_lower and (artist_lower in artist_name or artist_name in artist_lower):
            score += 15
        if item.get("syncedLyrics"):
            score += 10
        elif item.get("plainLyrics"):
            score += 4
        if score > best_score:
            best_score = score
            best = item
    if best_score <= 0 and payload and isinstance(payload[0], dict):
        return payload[0]
    return best


def _get_cached(title: str, artist: str, album: str, duration: float) -> dict[str, object] | None:
    params = {
        "track_name": title,
        "artist_name": artist,
        "album_name": album or title,
        "duration": int(max(duration, 1)),
    }
    payload = _http_get_json(LRCLIB_GET_CACHED_URL, params)
    if isinstance(payload, dict) and (payload.get("syncedLyrics") or payload.get("plainLyrics")):
        return payload
    return None


def _http_get_json(base_url: str, params: dict[str, object]) -> object | None:
    query = urllib.parse.urlencode(params)
    url = f"{base_url}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": APP_USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _float_value(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
