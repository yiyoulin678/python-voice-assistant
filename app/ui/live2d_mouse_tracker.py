from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget

from app.config.character_loader import CharacterLive2D
from app.ui.live2d_widget import Live2DWidget

_HEAD_ANGLE_X = "ParamAngleX"
_HEAD_ANGLE_Y = "ParamAngleY"
_EYE_BALL_X = "ParamEyeBallX"
_EYE_BALL_Y = "ParamEyeBallY"
_DEFAULT_TRACKED_PARAMS = (
    _HEAD_ANGLE_X,
    _HEAD_ANGLE_Y,
    _EYE_BALL_X,
    _EYE_BALL_Y,
)


@dataclass(frozen=True)
class MouseTrackingTargets:
    head_angle_x: float = 0.0
    head_angle_y: float = 0.0
    eye_ball_x: float = 0.0
    eye_ball_y: float = 0.0


def compute_mouse_tracking_targets(
    *,
    local_x: float,
    local_y: float,
    width: int,
    height: int,
    max_angle: float,
    max_eye_offset: float = 0.85,
) -> MouseTrackingTargets:
    if width <= 0 or height <= 0:
        return MouseTrackingTargets()

    center_x = width / 2.0
    center_y = height / 2.0
    norm_x = _clamp((local_x - center_x) / center_x, -1.0, 1.0)
    norm_y = _clamp((local_y - center_y) / center_y, -1.0, 1.0)
    return MouseTrackingTargets(
        head_angle_x=norm_x * max_angle,
        head_angle_y=-norm_y * max_angle,
        eye_ball_x=norm_x * max_eye_offset,
        eye_ball_y=-norm_y * max_eye_offset,
    )


class Live2DMouseTracker(QObject):
    """让 Live2D 头部与眼球持续朝向鼠标。"""

    def __init__(
        self,
        widget: Live2DWidget,
        anchor_widget: QWidget,
        config: CharacterLive2D,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._widget = widget
        self._anchor_widget = anchor_widget
        self._config = config
        self._tracked_params: set[str] = set()
        self._current = MouseTrackingTargets()
        self._started = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        if self._started or not self._config.mouse_tracking_enabled:
            return
        self._started = True
        self._refresh_tracked_params()
        self._timer.start()

    def stop(self) -> None:
        self._started = False
        self._timer.stop()
        self._reset_tracked_parameters()

    def refresh_config(self, config: CharacterLive2D) -> None:
        self._config = config
        if not config.mouse_tracking_enabled:
            self.stop()
            return
        self._refresh_tracked_params()
        if self._started and not self._timer.isActive():
            self._timer.start()

    def _refresh_tracked_params(self) -> None:
        available = set(self._widget.list_parameter_ids())
        self._tracked_params = {
            param_id
            for param_id in _DEFAULT_TRACKED_PARAMS
            if not available or param_id in available
        }

    def _tick(self) -> None:
        if not self._started or not self._widget.is_ready():
            return
        if not self._anchor_widget.isVisible():
            return

        global_pos = QCursor.pos()
        local_pos = self._anchor_widget.mapFromGlobal(global_pos)
        targets = compute_mouse_tracking_targets(
            local_x=float(local_pos.x()),
            local_y=float(local_pos.y()),
            width=self._anchor_widget.width(),
            height=self._anchor_widget.height(),
            max_angle=self._config.mouse_tracking_max_angle,
            max_eye_offset=self._config.mouse_tracking_max_eye_offset,
        )
        smoothing = self._config.mouse_tracking_smoothing
        self._current = MouseTrackingTargets(
            head_angle_x=_lerp(self._current.head_angle_x, targets.head_angle_x, smoothing),
            head_angle_y=_lerp(self._current.head_angle_y, targets.head_angle_y, smoothing),
            eye_ball_x=_lerp(self._current.eye_ball_x, targets.eye_ball_x, smoothing),
            eye_ball_y=_lerp(self._current.eye_ball_y, targets.eye_ball_y, smoothing),
        )
        self._apply_current()

    def _apply_current(self) -> None:
        mapping = {
            _HEAD_ANGLE_X: self._current.head_angle_x,
            _HEAD_ANGLE_Y: self._current.head_angle_y,
            _EYE_BALL_X: self._current.eye_ball_x,
            _EYE_BALL_Y: self._current.eye_ball_y,
        }
        for param_id, value in mapping.items():
            if param_id in self._tracked_params:
                self._widget.set_parameter(param_id, value)

    def _reset_tracked_parameters(self) -> None:
        if not self._widget.is_ready():
            self._current = MouseTrackingTargets()
            return
        for param_id in self._tracked_params:
            self._widget.reset_parameter(param_id)
        self._current = MouseTrackingTargets()


def _lerp(current: float, target: float, factor: float) -> float:
    blend = _clamp(factor, 0.05, 1.0)
    return current + (target - current) * blend


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
