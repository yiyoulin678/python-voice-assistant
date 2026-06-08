from __future__ import annotations

import re

_ELLIPSIS_SPLIT_RE = re.compile(r"(?:……+|…+)")
_TRIM_CHARS = " \t\n\r，,、。．.！!？?；;：:"


def split_tts_expression_chunks(text: str) -> list[str]:
    """把「嗯……好……」这类多停顿文本拆成多段，避免 TTS 只念最后一句。"""
    normalized = text.strip()
    if not normalized:
        return []
    if not _ELLIPSIS_SPLIT_RE.search(normalized):
        return [normalized]

    parts = _ELLIPSIS_SPLIT_RE.split(normalized)
    chunks = [part.strip(_TRIM_CHARS) for part in parts if part.strip(_TRIM_CHARS)]
    if len(chunks) <= 1:
        return [normalized]
    return chunks
