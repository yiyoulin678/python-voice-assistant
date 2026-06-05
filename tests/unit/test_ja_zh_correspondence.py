from __future__ import annotations

from app.llm.chat_reply import ChatSegment, parse_chat_reply_result
from app.llm.ja_zh_correspondence import (
    segment_has_correspondence_issue,
    segments_have_correspondence_issue,
)
from app.llm.prompts.blocks import build_segment_protocol
from app.llm.prompts.recipes import build_segmented_reply_instruction


def test_segment_detects_extra_chinese_filler_without_japanese_lead() -> None:
    segment = ChatSegment("いいよ。", "中性", "嗯，好的。", "")

    assert segment_has_correspondence_issue(segment) is True


def test_segment_allows_matching_filler_on_both_sides() -> None:
    segment = ChatSegment("うん、いいよ。", "中性", "嗯，好的。", "")

    assert segment_has_correspondence_issue(segment) is False


def test_parse_chat_reply_result_flags_correspondence_issue_when_strict() -> None:
    payload = (
        '{"segments":[{"ja":"いいよ。","zh":"嗯，好的。","tone":"中性","portrait":"微笑"}]}'
    )

    relaxed = parse_chat_reply_result(payload, strict_correspondence=False)
    strict = parse_chat_reply_result(payload, strict_correspondence=True)

    assert relaxed.needs_retry is False
    assert strict.needs_retry is True
    assert strict.reason == "correspondence_issue"


def test_build_segmented_reply_instruction_includes_strict_rules_when_enabled() -> None:
    normal = build_segmented_reply_instruction([], [], strict_correspondence=False)
    strict = build_segmented_reply_instruction([], [], strict_correspondence=True)

    assert "完全对应模式" not in normal
    assert "完全对应模式" in strict


def test_build_segment_protocol_uses_strict_translation_rules() -> None:
    protocol = build_segment_protocol(
        ["中性"],
        ["微笑"],
        format_text='{"segments":[]}',
        segment_rules="",
        include_translation_rules=True,
        strict_correspondence=True,
    )

    assert "语气词、停顿、感叹、省略号都必须同时出现在 ja 和 zh 中" in protocol


def test_segments_have_correspondence_issue_ignores_empty_translation() -> None:
    segments = [ChatSegment("こんばんは。", "中性", "", "")]

    assert segments_have_correspondence_issue(segments) is False


def test_segment_detects_semantic_omission_when_zh_is_much_longer() -> None:
    segment = ChatSegment(
        "大丈夫。",
        "中性",
        "没问题，不过你最好先保存一下，不然等会可能会丢。",
        "",
    )

    assert segment_has_correspondence_issue(segment) is True


def test_segment_detects_missing_causal_clause_in_japanese() -> None:
    segment = ChatSegment(
        "保存して。",
        "中性",
        "先保存吧，因为不保存的话等会可能会丢。",
        "",
    )

    assert segment_has_correspondence_issue(segment) is True


def test_segment_allows_balanced_bilingual_clauses() -> None:
    segment = ChatSegment(
        "だから、先に保存しておいた方がいいよ。",
        "中性",
        "所以，最好先保存一下哦。",
        "",
    )

    assert segment_has_correspondence_issue(segment) is False
