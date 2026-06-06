from __future__ import annotations

from app.agent.proactive_care import (
    ProactiveCareSettings,
    compute_proactive_care_countdown_seconds,
    format_proactive_care_countdown_hint,
)


def test_proactive_topics_can_run_without_screen_context() -> None:
    settings = ProactiveCareSettings(
        enabled=True,
        screen_context_enabled=False,
    ).normalized()
    assert settings.allows_proactive_topics()
    assert not settings.allows_screen_context()


def test_screen_context_requires_topic_enabled() -> None:
    settings = ProactiveCareSettings(
        enabled=False,
        screen_context_enabled=True,
    ).normalized()
    assert not settings.allows_proactive_topics()
    assert not settings.allows_screen_context()


def test_proactive_care_countdown_uses_idle_and_cooldown() -> None:
    settings = ProactiveCareSettings(
        enabled=True,
        check_interval_minutes=5,
        cooldown_minutes=10,
    ).normalized()
    seconds = compute_proactive_care_countdown_seconds(
        settings=settings,
        now=100.0,
        last_user_activity_at=70.0,
        last_proactive_care_at=None,
        screen_context_allowed=False,
        screen_context_count=0,
        screen_context_batch_started_at=None,
    )
    assert seconds == 270

    cooling = compute_proactive_care_countdown_seconds(
        settings=settings,
        now=500.0,
        last_user_activity_at=100.0,
        last_proactive_care_at=100.0,
        screen_context_allowed=False,
        screen_context_count=0,
        screen_context_batch_started_at=None,
    )
    assert cooling == 200

    ready = compute_proactive_care_countdown_seconds(
        settings=settings,
        now=700.0,
        last_user_activity_at=100.0,
        last_proactive_care_at=100.0,
        screen_context_allowed=False,
        screen_context_count=0,
        screen_context_batch_started_at=None,
    )
    assert ready == 0
    assert format_proactive_care_countdown_hint(ready) == "即将可能主动找你聊天"
    assert format_proactive_care_countdown_hint(125) == "约 2 分 05 秒后可能主动找你"


def test_proactive_care_countdown_waits_for_screen_batch_after_idle() -> None:
    settings = ProactiveCareSettings(
        enabled=True,
        screen_context_enabled=True,
        check_interval_minutes=2,
        cooldown_minutes=5,
    ).normalized()
    seconds = compute_proactive_care_countdown_seconds(
        settings=settings,
        now=100.0,
        last_user_activity_at=40.0,
        last_proactive_care_at=None,
        screen_context_allowed=True,
        screen_context_count=0,
        screen_context_batch_started_at=None,
        last_proactive_screen_context_at=None,
    )
    assert seconds == 360

    cooling_batch = compute_proactive_care_countdown_seconds(
        settings=settings,
        now=500.0,
        last_user_activity_at=100.0,
        last_proactive_care_at=None,
        screen_context_allowed=True,
        screen_context_count=2,
        screen_context_batch_started_at=220.0,
        last_proactive_screen_context_at=280.0,
    )
    assert cooling_batch == 20

    ready_batch = compute_proactive_care_countdown_seconds(
        settings=settings,
        now=520.0,
        last_user_activity_at=100.0,
        last_proactive_care_at=None,
        screen_context_allowed=True,
        screen_context_count=2,
        screen_context_batch_started_at=200.0,
        last_proactive_screen_context_at=280.0,
    )
    assert ready_batch == 0
