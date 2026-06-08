from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiFeatureSettings:
    """AI 增强功能开关。"""

    auto_session_summary_enabled: bool = True

    def normalized(self) -> "AiFeatureSettings":
        return AiFeatureSettings(
            auto_session_summary_enabled=bool(self.auto_session_summary_enabled),
        )
