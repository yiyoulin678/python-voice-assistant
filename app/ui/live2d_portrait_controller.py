from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget

from app.config.character_loader import CharacterLive2D, CharacterProfile
from app.llm.chat_reply import ChatSegment
from app.ui.live2d_interaction import Live2DInteractionController
from app.ui.live2d_lipsync import Live2DLipSyncController
from app.ui.live2d_input_overlay import Live2DInputOverlay
from app.ui.live2d_widget import Live2DWidget
from app.ui.portrait_controller import (
    PORTRAIT_BASE_MAX_HEIGHT,
    PORTRAIT_BASE_MAX_WIDTH,
    normalize_portrait_scale_percent,
)


class Live2DPortraitController(QObject):
    """Live2D 立绘：表情切换 + 托盘图标仍用 PNG 默认图。"""

    def __init__(
        self,
        *,
        profile: CharacterProfile,
        live2d_config: CharacterLive2D,
        parent_widget: QWidget,
        stage_size: tuple[int, int],
        relayout: Callable[[], None],
        on_portrait_changed: Callable[[QPixmap], None],
        portrait_scale_percent: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if profile.live2d is None:
            raise ValueError("角色未配置 Live2D")
        self.profile = profile
        self.live2d_config = live2d_config
        self.parent_widget = parent_widget
        self.stage_size = stage_size
        self.portrait_scale_percent = normalize_portrait_scale_percent(portrait_scale_percent)
        self._relayout = relayout
        self._on_portrait_changed = on_portrait_changed
        self._current_expression: str | None = live2d_config.default_expression
        self._persistent_expression_applied = False
        self._is_speaking = False

        self._stage_width, self._stage_height = self._scaled_stage_dimensions()
        self.live2d_widget = Live2DWidget(
            live2d_config=live2d_config,
            parent=parent_widget,
            on_ready=self._on_live2d_ready,
        )
        self.live2d_widget.setFixedSize(self._stage_width, self._stage_height)
        self.live2d_widget.set_display_scale(self.portrait_scale_percent / 100)
        self.live2d_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.live2d_widget.show()

        self.input_overlay = Live2DInputOverlay(parent_widget)
        self.input_overlay.setFixedSize(self._stage_width, self._stage_height)
        self.input_overlay.show()
        self.input_overlay.raise_()

        self._tray_pixmap = self._load_tray_pixmap(profile.default_portrait_path)
        self.pixmap = self._tray_pixmap

        self._hidden_label = QLabel(parent_widget)
        self._hidden_label.hide()

        self._lip_sync = Live2DLipSyncController(
            self.live2d_widget.set_mouth_open,
            parent=self,
        )
        self._interaction = Live2DInteractionController(
            self.live2d_widget,
            live2d_config,
            restore_expression=self._restore_base_expression,
            parent=self,
        )

    @property
    def portrait_stage_widget(self) -> QWidget:
        return self.live2d_widget

    @property
    def portrait_input_widget(self) -> QWidget:
        return self.input_overlay

    @property
    def portrait_stage_size(self) -> tuple[int, int]:
        return self.live2d_widget.width(), self.live2d_widget.height()

    def apply_current(self) -> None:
        self._relayout()

    def set_stage_size(self, stage_size: tuple[int, int]) -> None:
        self.stage_size = stage_size

    def set_portrait_scale_percent(self, portrait_scale_percent: int) -> None:
        self.portrait_scale_percent = normalize_portrait_scale_percent(portrait_scale_percent)
        self._stage_width, self._stage_height = self._scaled_stage_dimensions()
        self.live2d_widget.setFixedSize(self._stage_width, self._stage_height)
        self.live2d_widget.set_display_scale(self.portrait_scale_percent / 100)
        self.input_overlay.setFixedSize(self._stage_width, self._stage_height)

    def set_profile(self, profile: CharacterProfile) -> QPixmap:
        self.profile = profile
        self._tray_pixmap = self._load_tray_pixmap(profile.default_portrait_path)
        self.pixmap = self._tray_pixmap
        if profile.live2d is not None and profile.live2d.model_json_path != self.live2d_config.model_json_path:
            self.live2d_config = profile.live2d
            self.live2d_widget.reload_config(profile.live2d)
        self._current_expression = profile.live2d.default_expression if profile.live2d else None
        self.apply_current()
        self._on_portrait_changed(self.pixmap)
        return self.pixmap

    @property
    def has_speaking_board(self) -> bool:
        return bool(
            self.live2d_config.speaking_expression
            or self.live2d_config.speaking_overlay_expressions
        )

    def preload_for_segment(self, segment: ChatSegment) -> None:
        if self.has_speaking_board:
            self.begin_speech_segment()

    def apply_for_segment(self, segment: ChatSegment) -> None:
        expression_id = self._expression_for_segment(segment)
        if expression_id == self._current_expression and self.live2d_widget.is_ready():
            if self._is_speaking:
                self._apply_speaking_expressions()
            return
        self._current_expression = expression_id
        self._persistent_expression_applied = True
        self.live2d_widget.set_persistent_expression(expression_id)
        if self._is_speaking:
            self._apply_speaking_expressions()

    def begin_speech_segment(self) -> None:
        """段落开始或等待 TTS 时举起画板。"""
        if not self.has_speaking_board:
            return
        self._is_speaking = True
        self._apply_speaking_expressions()

    def attach_speech_audio(self, audio_path: Path | str | None) -> None:
        """有音频时驱动口型；无配置画板时仍可作为说话入口。"""
        if not self._is_speaking and self.has_speaking_board:
            self.begin_speech_segment()
        elif not self._is_speaking:
            self._is_speaking = True
        path = Path(audio_path) if audio_path else None
        self._lip_sync.start(path)

    def detach_speech_audio(self) -> None:
        """本段音频结束，仅停口型，画板保持到整轮回复结束。"""
        self._lip_sync.stop()

    def begin_speech(self, audio_path: Path | str | None) -> None:
        self.begin_speech_segment()
        self.attach_speech_audio(audio_path)

    def end_speech(self) -> None:
        self._is_speaking = False
        self._lip_sync.stop()
        self.live2d_widget.clear_expression_overlays()

    def dispose(self) -> None:
        self._interaction.stop()

    def _apply_speaking_expressions(self) -> None:
        speaking = self.live2d_config.speaking_expression
        if speaking:
            self.live2d_widget.add_expression_overlay(speaking)
        for expression_id in self.live2d_config.speaking_overlay_expressions:
            self.live2d_widget.add_expression_overlay(expression_id)

    def _expression_for_segment(self, segment: ChatSegment) -> str | None:
        portrait_key = (segment.portrait or "").strip()
        if portrait_key and portrait_key in self.live2d_config.tone_expressions:
            return self.live2d_config.tone_expressions[portrait_key]
        tone_key = (segment.tone or "").strip()
        if tone_key and tone_key in self.live2d_config.tone_expressions:
            return self.live2d_config.tone_expressions[tone_key]
        return self.live2d_config.default_expression

    def _scaled_stage_dimensions(self) -> tuple[int, int]:
        scale = self.portrait_scale_percent / 100
        return (
            round(PORTRAIT_BASE_MAX_WIDTH * scale),
            round(PORTRAIT_BASE_MAX_HEIGHT * scale),
        )

    def _on_live2d_ready(self) -> None:
        self.apply_current()
        if self._is_speaking:
            self._apply_speaking_expressions()
        self._interaction.start()

    def trigger_tap(self, x: float, y: float) -> None:
        self._interaction.handle_tap(x, y)

    @property
    def current_expression(self) -> str | None:
        return self._current_expression

    def apply_expression(self, expression_id: str) -> bool:
        """菜单手动切换表情；未就绪时会排队，模型加载后自动应用。"""
        expression_id = expression_id.strip()
        if not expression_id:
            return False
        if expression_id not in self.live2d_widget.list_expression_ids():
            return False
        self._interaction.cancel_scheduled_restore()
        self._interaction.cancel_idle_variation()
        self._current_expression = expression_id
        self._persistent_expression_applied = True
        self.live2d_widget.set_persistent_expression(expression_id)
        self._interaction.resume_idle_variation()
        if self._is_speaking and self.live2d_widget.is_ready():
            self._apply_speaking_expressions()
        return True

    def _restore_base_expression(self) -> None:
        self.live2d_widget.clear_fleeting_expressions(restart_motion=not self._is_speaking)
        if self._is_speaking:
            self._apply_speaking_expressions()

    def _load_tray_pixmap(self, portrait_path: Path) -> QPixmap:
        pixmap = QPixmap(str(portrait_path))
        if pixmap.isNull():
            QMessageBox.critical(
                self.parent_widget,
                "立绘加载失败",
                f"无法加载托盘图标立绘：{portrait_path}",
            )
        return pixmap
