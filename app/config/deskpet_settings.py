from __future__ import annotations

from dataclasses import dataclass

from app.ui.themes import DEFAULT_UI_THEME, normalize_ui_theme

SUBTITLE_LANGUAGE_ZH = "zh"
SUBTITLE_LANGUAGE_JA = "ja"

REMINDER_CHECK_INTERVAL_MIN_SECONDS = 3
REMINDER_CHECK_INTERVAL_MAX_SECONDS = 120
REMINDER_CHECK_INTERVAL_DEFAULT_SECONDS = 5


@dataclass(frozen=True)
class PetUISettings:
    """桌宠窗口与字幕展示相关配置。"""

    hover_only_ui: bool = True
    subtitle_language: str = SUBTITLE_LANGUAGE_ZH
    free_access_enabled: bool = False
    music_plugin_enabled: bool = True
    music_default_source: str = "netease"
    lyric_sync_offset_seconds: float = 1.2
    music_sing_along_enabled: bool = True
    ui_theme: str = DEFAULT_UI_THEME
    desktop_pet_rules_enabled: bool = False
    strict_ja_zh_correspondence_enabled: bool = False

    def normalized(self) -> "PetUISettings":
        language = str(self.subtitle_language).strip().lower()
        if language != SUBTITLE_LANGUAGE_ZH:
            language = SUBTITLE_LANGUAGE_JA
        source = str(self.music_default_source).strip().lower()
        if source not in {"netease", "qq"}:
            source = "netease"
        try:
            lyric_offset = float(self.lyric_sync_offset_seconds)
        except (TypeError, ValueError):
            lyric_offset = 1.2
        lyric_offset = max(-5.0, min(5.0, lyric_offset))
        return PetUISettings(
            hover_only_ui=bool(self.hover_only_ui),
            subtitle_language=language,
            free_access_enabled=bool(self.free_access_enabled),
            music_plugin_enabled=bool(self.music_plugin_enabled),
            music_default_source=source,
            lyric_sync_offset_seconds=lyric_offset,
            music_sing_along_enabled=bool(self.music_sing_along_enabled),
            ui_theme=normalize_ui_theme(self.ui_theme),
            desktop_pet_rules_enabled=bool(self.desktop_pet_rules_enabled),
            strict_ja_zh_correspondence_enabled=bool(self.strict_ja_zh_correspondence_enabled),
        )


@dataclass(frozen=True)
class ScreenObservationSettings:
    """屏幕截图/观察能力开关。"""

    enabled: bool = True
    autonomous_enabled: bool = True

    def normalized(self) -> "ScreenObservationSettings":
        enabled = bool(self.enabled)
        autonomous = bool(self.autonomous_enabled) and enabled
        return ScreenObservationSettings(
            enabled=enabled,
            autonomous_enabled=autonomous,
        )


@dataclass(frozen=True)
class ReminderSettings:
    """到点提醒轮询配置。"""

    enabled: bool = True
    check_interval_seconds: int = REMINDER_CHECK_INTERVAL_DEFAULT_SECONDS

    def normalized(self) -> "ReminderSettings":
        try:
            seconds = int(self.check_interval_seconds)
        except (TypeError, ValueError):
            seconds = REMINDER_CHECK_INTERVAL_DEFAULT_SECONDS
        seconds = max(
            REMINDER_CHECK_INTERVAL_MIN_SECONDS,
            min(REMINDER_CHECK_INTERVAL_MAX_SECONDS, seconds),
        )
        return ReminderSettings(
            enabled=bool(self.enabled),
            check_interval_seconds=seconds,
        )

    @property
    def check_interval_ms(self) -> int:
        return self.normalized().check_interval_seconds * 1000
