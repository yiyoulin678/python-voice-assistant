from __future__ import annotations

from app.media.lrc_parser import parse_lrc_offset_ms, parse_synced_lyrics, synced_line_at


def test_parse_lrc_offset_ms() -> None:
    text = "[offset:-500]\n[00:01.00]歌词"
    assert parse_lrc_offset_ms(text) == -500
    lines = parse_synced_lyrics(text)
    assert lines[0][0] == 0.5


def test_parse_synced_lyrics_and_pick_line() -> None:
    text = """[00:00.00]第一行
[00:05.00]第二行
[00:10.00]第三行"""
    lines = parse_synced_lyrics(text)
    assert len(lines) == 3
    assert synced_line_at(lines, 0.0) == "第一行"
    assert synced_line_at(lines, 7.5) == "第二行"
    assert synced_line_at(lines, 30.0) == "第三行"
