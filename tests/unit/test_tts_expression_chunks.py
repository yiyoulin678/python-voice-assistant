from __future__ import annotations

from app.llm.chat_reply import ChatSegment
from app.llm.ja_zh_correspondence import segment_has_correspondence_issue
from app.llm.expression_chunks import split_tts_expression_chunks


def test_split_tts_expression_chunks_splits_on_ellipsis_runs() -> None:
    text = "哈啊，嗯……嗯，好……嗯，随你喜欢……嗯，再激烈一点……嗯！"

    chunks = split_tts_expression_chunks(text)

    assert chunks == [
        "哈啊，嗯",
        "嗯，好",
        "嗯，随你喜欢",
        "嗯，再激烈一点",
        "嗯",
    ]


def test_split_tts_expression_chunks_keeps_plain_sentence_intact() -> None:
    text = "今天天气不错，我们出去走走吧。"

    assert split_tts_expression_chunks(text) == [text]


def test_segment_detects_ellipsis_rich_zh_with_short_ja() -> None:
    segment = ChatSegment(
        "もっと激しく。",
        "中性",
        "哈啊，嗯……嗯，好……嗯，随你喜欢……嗯，再激烈一点……嗯！",
        "",
    )

    assert segment_has_correspondence_issue(segment) is True
