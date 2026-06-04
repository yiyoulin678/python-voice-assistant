from __future__ import annotations

import random
from typing import Callable

from PySide6.QtCore import QObject, QTimer

from app.config.character_loader import CharacterLive2D
from app.core.debug_log import debug_log
from app.ui.live2d_widget import Live2DWidget

_EYE_OPEN_PARAMS = ("ParamEyeLOpen", "ParamEyeROpen")
_EYE_CLOSED_VALUE = 0.0


class Live2DInteractionController(QObject):
    """闲置小动作、点击反应与自动眨眼。"""

    def __init__(
        self,
        widget: Live2DWidget,
        config: CharacterLive2D,
        *,
        restore_expression: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._widget = widget
        self._config = config
        self._restore_expression = restore_expression
        self._fleeting_timer = QTimer(self)
        self._fleeting_timer.setSingleShot(True)
        self._fleeting_timer.timeout.connect(self._finish_fleeting_expression)
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._play_idle_variation)
        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._close_eyes)
        self._blink_restore_timer = QTimer(self)
        self._blink_restore_timer.setSingleShot(True)
        self._blink_restore_timer.timeout.connect(self._open_eyes)
        self._blink_schedule_timer = QTimer(self)
        self._blink_schedule_timer.setSingleShot(True)
        self._blink_schedule_timer.timeout.connect(self._schedule_blink)
        self._eyes_open = True
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._widget.set_on_tap(lambda: self._on_tap(0.0, 0.0))
        if self._config.blink_enabled:
            self._schedule_blink()
        if self._config.idle_variation_expressions:
            self._schedule_idle_variation()

    def handle_tap(self, x: float, y: float) -> None:
        if not self._started:
            debug_log("Live2D", "轻点忽略：互动未启动", {})
            return
        if not self._widget.is_ready():
            debug_log("Live2D", "轻点忽略：模型尚未就绪", {})
            return
        self._on_tap(x, y)

    def cancel_scheduled_restore(self) -> None:
        self._fleeting_timer.stop()

    def cancel_idle_variation(self) -> None:
        self._idle_timer.stop()

    def resume_idle_variation(self) -> None:
        if self._started and self._config.idle_variation_expressions:
            self._schedule_idle_variation()

    def stop(self) -> None:
        self._started = False
        self._fleeting_timer.stop()
        self._idle_timer.stop()
        self._blink_timer.stop()
        self._blink_restore_timer.stop()
        self._blink_schedule_timer.stop()
        self._open_eyes()

    def play_fleeting_expression(
        self,
        expression_id: str,
        *,
        hold_ms: int = 1400,
        freeze_motion: bool = False,
    ) -> None:
        expression_id = expression_id.strip()
        if not expression_id or not self._widget.is_ready():
            return
        self._fleeting_timer.stop()
        if freeze_motion:
            self._widget.set_expression(expression_id, hold_motion=True)
        else:
            self._widget.show_fleeting_expression(expression_id)
        self._fleeting_timer.start(max(300, hold_ms))

    def _finish_fleeting_expression(self) -> None:
        self._restore_expression()

    def _on_tap(self, x: float, y: float) -> None:
        choices = self._config.tap_expressions
        if not choices:
            debug_log("Live2D", "轻点：未配置 tap_expressions", {})
            return
        expression_id = random.choice(choices)
        debug_log("Live2D", "轻点触发表情", {"expression": expression_id, "x": round(x, 1), "y": round(y, 1)})
        self.play_fleeting_expression(expression_id, hold_ms=1600, freeze_motion=False)
        self._widget.update()

    def _schedule_idle_variation(self) -> None:
        if not self._config.idle_variation_expressions:
            return
        delay_ms = int(
            random.uniform(
                self._config.idle_variation_min_seconds,
                self._config.idle_variation_max_seconds,
            )
            * 1000
        )
        self._idle_timer.start(max(5000, delay_ms))

    def _play_idle_variation(self) -> None:
        if (
            self._started
            and self._config.idle_variation_expressions
            and not self._widget.is_holding_expression()
        ):
            self.play_fleeting_expression(
                random.choice(self._config.idle_variation_expressions),
                hold_ms=2200,
                freeze_motion=False,
            )
        self._schedule_idle_variation()

    def _schedule_blink(self) -> None:
        if not self._started:
            return
        delay_ms = random.randint(2800, 5200)
        self._blink_schedule_timer.start(delay_ms)

    def _close_eyes(self) -> None:
        if not self._widget.is_ready():
            self._schedule_blink()
            return
        if self._widget.is_holding_expression():
            self._schedule_blink()
            return
        self._eyes_open = False
        for param_id in _EYE_OPEN_PARAMS:
            self._widget.set_parameter(param_id, _EYE_CLOSED_VALUE)
        self._blink_restore_timer.start(120)

    def _open_eyes(self) -> None:
        if self._widget.is_ready():
            for param_id in _EYE_OPEN_PARAMS:
                self._widget.reset_parameter(param_id)
        self._eyes_open = True
        self._schedule_blink()
