from __future__ import annotations

import re

_LRC_TIMESTAMP = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\](?:\s*(.*))?$")
_LRC_OFFSET = re.compile(r"^\[offset:\s*([+-]?\d+)\s*\]$", re.IGNORECASE)


def parse_lrc_offset_ms(text: str) -> int:
    for raw in text.splitlines():
        line = raw.strip()
        match = _LRC_OFFSET.match(line)
        if not match:
            continue
        try:
            return int(match.group(1))
        except ValueError:
            return 0
    return 0


def parse_synced_lyrics(text: str) -> list[tuple[float, str]]:
    """解析 LRC 同步歌词为 (秒, 文本) 列表。"""
    offset_seconds = parse_lrc_offset_ms(text) / 1000.0
    lines: list[tuple[float, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("[ti:") or line.startswith("[ar:"):
            continue
        if line.startswith("[al:") or line.startswith("[by:") or _LRC_OFFSET.match(line):
            continue
        match = _LRC_TIMESTAMP.match(line)
        if not match:
            continue
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        lyric = (match.group(3) or "").strip()
        if not lyric:
            continue
        timestamp = minutes * 60 + seconds + offset_seconds
        if timestamp < 0:
            continue
        lines.append((timestamp, lyric))
    lines.sort(key=lambda item: item[0])
    return lines


def synced_line_at(lines: list[tuple[float, str]], position_seconds: float) -> str:
    if not lines:
        return ""
    current = ""
    for timestamp, text in lines:
        if timestamp <= position_seconds:
            current = text
        else:
            break
    if current:
        return current
    return lines[0][1]


def split_plain_lyrics(text: str) -> list[str]:
    rows: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        rows.append(line)
    return rows


def plain_line_at(lines: list[str], position_seconds: float, *, duration_seconds: float) -> str:
    if not lines:
        return ""
    if duration_seconds <= 0:
        duration_seconds = max(len(lines) * 4.0, 60.0)
    index = int(position_seconds / (duration_seconds / len(lines)))
    index = max(0, min(index, len(lines) - 1))
    return lines[index]
