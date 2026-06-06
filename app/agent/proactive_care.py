from __future__ import annotations

import math
from dataclasses import dataclass

PROACTIVE_DEFAULT_CHECK_INTERVAL_MINUTES = 2
PROACTIVE_DEFAULT_COOLDOWN_MINUTES = 10
PROACTIVE_DEFAULT_SCREEN_CONTEXT_BATCH_LIMIT = 6
PROACTIVE_MIN_CHECK_INTERVAL_MINUTES = 1
PROACTIVE_MAX_CHECK_INTERVAL_MINUTES = 120
PROACTIVE_MIN_COOLDOWN_MINUTES = 1
PROACTIVE_MAX_COOLDOWN_MINUTES = 120
PROACTIVE_MIN_SCREEN_CONTEXT_BATCH_LIMIT = 1
PROACTIVE_MAX_SCREEN_CONTEXT_BATCH_LIMIT = 20
PROACTIVE_TIMER_POLL_INTERVAL_MS = 10_000
PROACTIVE_TIMER_DUE_GRACE_SECONDS = 1.0
PROACTIVE_SCREEN_CONTEXT_HISTORY_MARKER = "[已抓取屏幕上下文]"
PROACTIVE_TOPIC_HISTORY_MARKER = "[主动找话题]"


@dataclass(frozen=True)
class ProactiveCareSettings:
    """主动关怀配置：enabled 控制空闲搭话；screen_context_enabled 控制是否附带截图。"""

    enabled: bool = True
    screen_context_enabled: bool = False
    check_interval_minutes: int = PROACTIVE_DEFAULT_CHECK_INTERVAL_MINUTES
    cooldown_minutes: int = PROACTIVE_DEFAULT_COOLDOWN_MINUTES
    screen_context_batch_limit: int = PROACTIVE_DEFAULT_SCREEN_CONTEXT_BATCH_LIMIT

    def normalized(self) -> "ProactiveCareSettings":
        return ProactiveCareSettings(
            enabled=bool(self.enabled),
            screen_context_enabled=bool(self.screen_context_enabled),
            check_interval_minutes=_clamp_interval_minutes(
                self.check_interval_minutes,
                min_value=PROACTIVE_MIN_CHECK_INTERVAL_MINUTES,
                max_value=PROACTIVE_MAX_CHECK_INTERVAL_MINUTES,
            ),
            cooldown_minutes=_clamp_interval_minutes(
                self.cooldown_minutes,
                min_value=PROACTIVE_MIN_COOLDOWN_MINUTES,
                max_value=PROACTIVE_MAX_COOLDOWN_MINUTES,
            ),
            screen_context_batch_limit=_clamp_bounded_int(
                self.screen_context_batch_limit,
                min_value=PROACTIVE_MIN_SCREEN_CONTEXT_BATCH_LIMIT,
                max_value=PROACTIVE_MAX_SCREEN_CONTEXT_BATCH_LIMIT,
            ),
        )

    def allows_proactive_topics(self) -> bool:
        """是否允许在空闲时主动找话题。"""
        return bool(self.enabled)

    def allows_screen_context(self) -> bool:
        """主动搭话时是否附带后台屏幕截图。"""
        return bool(self.enabled and self.screen_context_enabled)


def _clamp_interval_minutes(value: int, *, min_value: int, max_value: int) -> int:
    return _clamp_bounded_int(value, min_value=min_value, max_value=max_value)


def _clamp_bounded_int(value: int, *, min_value: int, max_value: int) -> int:
    return max(
        min_value,
        min(max_value, value),
    )


def compute_proactive_care_countdown_seconds(
    *,
    settings: ProactiveCareSettings,
    now: float,
    last_user_activity_at: float,
    last_proactive_care_at: float | None,
    screen_context_allowed: bool,
    screen_context_count: int,
    screen_context_batch_started_at: float | None,
) -> int | None:
    """返回距离下次可主动搭话还剩多少秒；None 表示功能未开启。"""
    normalized = settings.normalized()
    if not normalized.allows_proactive_topics():
        return None

    cooldown_seconds = normalized.cooldown_minutes * 60
    check_interval_seconds = normalized.check_interval_minutes * 60
    waits: list[float] = []

    idle_wait = check_interval_seconds - (now - last_user_activity_at)
    if idle_wait > PROACTIVE_TIMER_DUE_GRACE_SECONDS:
        waits.append(idle_wait)

    if last_proactive_care_at is not None:
        cooldown_wait = cooldown_seconds - (now - last_proactive_care_at)
        if cooldown_wait > PROACTIVE_TIMER_DUE_GRACE_SECONDS:
            waits.append(cooldown_wait)

    if screen_context_allowed:
        if screen_context_count <= 0 or screen_context_batch_started_at is None:
            waits.append(check_interval_seconds)
        else:
            batch_wait = cooldown_seconds - (now - screen_context_batch_started_at)
            if batch_wait > PROACTIVE_TIMER_DUE_GRACE_SECONDS:
                waits.append(batch_wait)

    if not waits:
        return 0
    return max(0, int(math.ceil(max(waits))))


def format_proactive_care_countdown_hint(seconds: int | None) -> str:
    if seconds is None:
        return ""
    if seconds <= 0:
        return "即将可能主动找你聊天"
    minutes, remainder = divmod(seconds, 60)
    if minutes > 0:
        return f"约 {minutes} 分 {remainder:02d} 秒后可能主动找你"
    return f"约 {seconds} 秒后可能主动找你"
