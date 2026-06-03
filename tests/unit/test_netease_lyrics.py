from __future__ import annotations

from app.media.lyrics_fetcher import fetch_track_lyrics


def test_fetch_netease_lyrics_for_photocopy() -> None:
    lyrics = fetch_track_lyrics(
        "フォトコピー",
        "闇音レンリ",
        music_source="netease",
    )
    assert lyrics is not None
    assert lyrics.has_synced() or lyrics.has_plain()
