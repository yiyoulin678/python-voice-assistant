from __future__ import annotations

import re

from app.llm.chat_reply import ChatSegment
from app.llm.expression_chunks import split_tts_expression_chunks

_CHINESE_LEADING_FILLER_RE = re.compile(
    r"^(?:嗯{1,3}|啊{1,3}|唔+|哦+|诶+|哎+|哼+|那个|这个|就是|其实|怎么说呢)+[，,、…\.。！!？?]*"
)
_JAPANESE_LEADING_FILLER_RE = re.compile(
    r"^(?:え{1,3}|えっと|あ{1,3}|あの|うん|ん{1,3}|まあ|その|ほら|で)+[、。…！!？?]*"
)
_CHINESE_TRAILING_PARTICLE_RE = re.compile(r"(?:啊|呀|呢|吧|哦|嘛|啦|咯)[。！？…]*$")
_JAPANESE_TRAILING_PARTICLE_RE = re.compile(r"(?:ね|よ|さ|な|か|わ|の)[。！？…]*$")
_ZH_LEADING_FILLER_TOKENS = ("嗯", "哈", "啊", "那个", "这个", "怎么说呢")
_ZH_BODY_FILLER_TOKENS = ("其实", "就是")
_SURFACE_NOISE_RE = re.compile(r"[\s，,、。．.！!？?；;：:…·—\-~～「」『』（）()【】\[\]\"'“”‘’]+")
_ZH_DISCOURSE_MARKERS = (
    "因为",
    "所以",
    "但是",
    "如果",
    "不过",
    "而且",
    "另外",
    "首先",
    "然后",
    "其实",
    "可能",
    "需要",
    "建议",
    "注意",
    "顺便",
    "总之",
    "也就是说",
)
_JA_DISCOURSE_MARKERS = (
    "だから",
    "でも",
    "けど",
    "ので",
    "から",
    "もし",
    "また",
    "それで",
    "つまり",
    "ちなみに",
    "ただ",
    "まず",
    "それから",
    "要するに",
)
_CLAUSE_PUNCTUATION_RE = re.compile(r"[，,、；;。．.！!？?]")


def segment_has_correspondence_issue(segment: ChatSegment) -> bool:
    """检测 ja/zh 在语气词或句意上是否明显不对称。"""
    japanese = segment.text.strip()
    chinese = segment.translation.strip()
    if not japanese or not chinese:
        return False

    if _has_filler_correspondence_issue(japanese, chinese):
        return True
    return _has_semantic_correspondence_issue(japanese, chinese)


def _has_filler_correspondence_issue(japanese: str, chinese: str) -> bool:
    chinese_leading = _CHINESE_LEADING_FILLER_RE.match(chinese)
    japanese_leading = _JAPANESE_LEADING_FILLER_RE.match(japanese)
    if chinese_leading and not japanese_leading:
        return True

    if _CHINESE_TRAILING_PARTICLE_RE.search(chinese) and not _JAPANESE_TRAILING_PARTICLE_RE.search(
        japanese
    ):
        return True

    if not (chinese_leading and japanese_leading):
        for token in _ZH_LEADING_FILLER_TOKENS:
            if token in chinese and token not in japanese:
                return True
    for token in _ZH_BODY_FILLER_TOKENS:
        if token in chinese and token not in japanese:
            return True

    japanese_len = max(len(japanese), 1)
    filler_tokens = _ZH_LEADING_FILLER_TOKENS + _ZH_BODY_FILLER_TOKENS
    if len(chinese) > int(japanese_len * 1.35) + 4 and (
        chinese_leading or any(token in chinese for token in filler_tokens)
    ):
        return True

    return False


def _has_semantic_correspondence_issue(japanese: str, chinese: str) -> bool:
    japanese_core = _strip_surface_noise(japanese)
    chinese_core = _strip_surface_noise(chinese)
    if not japanese_core or not chinese_core:
        return False

    japanese_len = max(len(japanese_core), 1)
    chinese_len = len(chinese_core)
    if chinese_len >= 12 and chinese_len > int(japanese_len * 1.4) + 3:
        return True
    if japanese_len >= 12 and japanese_len > int(chinese_len * 1.4) + 3:
        return True

    chinese_markers = _count_markers(chinese, _ZH_DISCOURSE_MARKERS)
    japanese_markers = _count_markers(japanese, _JA_DISCOURSE_MARKERS)
    if chinese_markers >= 2 and japanese_markers == 0 and chinese_len > japanese_len + 4:
        return True
    if chinese_markers >= 1 and japanese_markers == 0 and chinese_len > int(japanese_len * 1.25) + 6:
        return True

    chinese_clauses = len(_CLAUSE_PUNCTUATION_RE.findall(chinese))
    japanese_clauses = len(_CLAUSE_PUNCTUATION_RE.findall(japanese))
    if chinese_clauses >= 2 and japanese_clauses == 0 and chinese_len > japanese_len + 5:
        return True

    chinese_expression_chunks = len(split_tts_expression_chunks(chinese))
    japanese_expression_chunks = len(split_tts_expression_chunks(japanese))
    if chinese_expression_chunks >= 3 and japanese_expression_chunks < chinese_expression_chunks:
        return True
    if chinese_expression_chunks >= 2 and japanese_expression_chunks == 1 and chinese_len > japanese_len + 8:
        return True

    return False


def segments_have_correspondence_issue(segments: list[ChatSegment]) -> bool:
    return any(
        segment_has_correspondence_issue(segment)
        for segment in segments
        if segment.text.strip() and segment.translation.strip()
    )


def _strip_surface_noise(text: str) -> str:
    stripped = _CHINESE_LEADING_FILLER_RE.sub("", text.strip())
    stripped = _JAPANESE_LEADING_FILLER_RE.sub("", stripped)
    stripped = _SURFACE_NOISE_RE.sub("", stripped)
    return stripped


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)
