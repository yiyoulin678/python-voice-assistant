from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent, QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from app.config.character_loader import CharacterLive2D
from app.live2d.runtime import get_live2d_module


class Live2DWidget(QOpenGLWidget):
    """在 OpenGL 上下文中渲染 Cubism 3 模型。"""

    def __init__(
        self,
        *,
        live2d_config: CharacterLive2D,
        parent: QWidget | None = None,
        on_ready: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._live2d_config = live2d_config
        self._model_json = live2d_config.model_json_path
        self._model_dir = self._model_json.parent
        self._on_ready = on_ready
        self._model = None
        self._ready = False
        self._pending_expression: str | None = None
        self._mouth_open = 0.0
        self._overlay_expressions: set[str] = set()
        self._scale = 1.0
        self._drag_offset: QPoint | None = None
        self._forward_drag: Callable[[QMouseEvent], bool] | None = None
        self._on_tap: Callable[[], None] | None = None
        self._press_position: QPointF | None = None
        self._last_frame_time = time.monotonic()
        self._expression_motion_hold_until = 0.0
        self._held_expression_id = ""
        self._held_snapshot_applied = False
        self._idle_motion_started = False
        self._physics_enabled = False

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        fmt.setSamples(4)
        self.setFormat(fmt)

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(16)
        self._frame_timer.timeout.connect(self.update)

    def set_forward_drag_handler(self, handler: Callable[[QMouseEvent], bool] | None) -> None:
        self._forward_drag = handler

    def set_on_tap(self, handler: Callable[[], None] | None) -> None:
        self._on_tap = handler

    def play_idle_motion_burst(self) -> None:
        if not self._ready or self._model is None:
            return
        live2d = get_live2d_module()
        groups = self._model.GetMotionGroups()
        if live2d.MotionGroup.IDLE not in groups or groups[live2d.MotionGroup.IDLE] <= 0:
            return
        self._model.StartMotion(
            live2d.MotionGroup.IDLE,
            0,
            live2d.MotionPriority.NORMAL,
        )

    def set_parameter(self, param_id: str, value: float) -> None:
        if self._ready and self._model is not None:
            self._model.SetParameterValue(param_id, value)

    def reset_parameter(self, param_id: str) -> None:
        if not self._ready or self._model is None:
            return
        for index, known_id in enumerate(self._model.GetParamIds()):
            if known_id == param_id:
                default = self._model.GetParameter(index).default
                self._model.SetParameterValue(param_id, default)
                return

    def set_display_scale(self, scale: float) -> None:
        self._scale = max(0.5, min(1.5, scale))
        if self._model is not None:
            self._model.SetScale(self._scale)

    def is_ready(self) -> bool:
        return self._ready

    def is_holding_expression(self) -> bool:
        return bool(self._held_expression_id)

    def list_expression_ids(self) -> list[str]:
        """列出可用表情 ID（含 model3 未登记、仅通过 LoadExtraExpression 加载的）。"""
        return self._discover_expression_ids()

    def set_expression(
        self,
        expression_id: str | None,
        *,
        hold_motion: bool = False,
    ) -> None:
        if not self._ready or self._model is None:
            self._pending_expression = expression_id
            return
        self.makeCurrent()
        self._apply_expression(expression_id, hold_motion=hold_motion)
        self.update()

    def set_mouth_open(self, value: float) -> None:
        self._mouth_open = max(0.0, min(1.0, value))
        if self._ready and self._model is not None:
            self._model.SetParameterValue("ParamMouthOpenY", self._mouth_open)

    def add_expression_overlay(self, expression_id: str) -> None:
        expression_id = expression_id.strip()
        if not expression_id or expression_id in self._overlay_expressions:
            return
        if not self._ready or self._model is None:
            self._overlay_expressions.add(expression_id)
            return
        if expression_id in set(self._discover_expression_ids()):
            self._model.AddExpression(expression_id)
            self._overlay_expressions.add(expression_id)

    def remove_expression_overlay(self, expression_id: str) -> None:
        expression_id = expression_id.strip()
        if expression_id not in self._overlay_expressions:
            return
        self._overlay_expressions.discard(expression_id)
        if self._ready and self._model is not None:
            self._model.RemoveExpression(expression_id)

    def clear_expression_overlays(self) -> None:
        if not self._overlay_expressions:
            return
        overlays = list(self._overlay_expressions)
        self._overlay_expressions.clear()
        if not self._ready or self._model is None:
            return
        for expression_id in overlays:
            self._model.RemoveExpression(expression_id)

    def reload_config(self, live2d_config: CharacterLive2D) -> None:
        self._live2d_config = live2d_config
        self._model_json = live2d_config.model_json_path
        self._model_dir = self._model_json.parent
        self._ready = False
        self._pending_expression = live2d_config.default_expression
        self._mouth_open = 0.0
        self._expression_motion_hold_until = 0.0
        self._held_expression_id = ""
        self._held_snapshot_applied = False
        self._idle_motion_started = False
        self.clear_expression_overlays()
        if self._model is not None:
            live2d = get_live2d_module()
            self._model.DestroyRenderer()
            self._model = None
            live2d.glInit()
            self._load_model()

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        if not self._ready:
            QTimer.singleShot(0, self._ensure_gl_initialized)

    def _ensure_gl_initialized(self) -> None:
        if self._ready or self._model is not None:
            return
        if not self.isVisible() or self.width() <= 0 or self.height() <= 0:
            return
        self.makeCurrent()
        if self.context() is None or not self.context().isValid():
            self.update()
            return
        self.initializeGL()

    def initializeGL(self) -> None:
        if self._model is not None:
            return
        live2d = get_live2d_module()
        live2d.glInit()
        self._load_model()

    def resizeGL(self, width: int, height: int) -> None:
        if self._model is not None and width > 0 and height > 0:
            self._model.Resize(width, height)

    def paintGL(self) -> None:
        if self._model is None:
            return
        live2d = get_live2d_module()
        live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)
        self._model.SetParameterValue("ParamMouthOpenY", self._mouth_open)
        self._advance_model_frame()
        self._model.Draw()

    def _advance_model_frame(self) -> None:
        if self._model is None:
            return
        now = time.monotonic()
        dt = min(now - self._last_frame_time, 0.1)
        self._last_frame_time = now
        if (
            self._expression_motion_hold_until > 0.0
            and now >= self._expression_motion_hold_until
        ):
            self._expression_motion_hold_until = 0.0
            self._held_expression_id = ""
            self._held_snapshot_applied = False
            self._start_idle_motion()
        core = self._model._model
        core.Update(dt)
        if self._held_expression_id:
            if not self._held_snapshot_applied:
                core.LoadParameters()
                self._apply_exp3_snapshot(self._held_expression_id)
                self._held_snapshot_applied = True
            return
        core.LoadParameters()
        if not core.IsMotionFinished() and core.UpdateMotion(dt):
            core.SaveParameters()
        core.UpdateExpression(dt)
        if self._physics_enabled:
            try:
                core.UpdatePhysics(dt)
            except Exception:
                pass

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint()
            self._press_position = event.position()
        if self._forward_drag and self._forward_drag(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._forward_drag and self._forward_drag(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._press_position is not None
            and self._on_tap is not None
        ):
            delta = event.position() - self._press_position
            if delta.manhattanLength() <= 10:
                self._on_tap()
        self._press_position = None
        self._drag_offset = None
        if self._forward_drag and self._forward_drag(event):
            return
        super().mouseReleaseEvent(event)

    def _load_model(self) -> None:
        live2d = get_live2d_module()
        self._model = live2d.LAppModel()
        self._model.LoadModelJson(str(self._model_json))
        self._idle_motion_started = False
        self._model.SetScale(self._scale)
        if self.width() > 0 and self.height() > 0:
            self._model.Resize(self.width(), self.height())
        self._ready = True
        self._frame_timer.start()
        default_expression = self._pending_expression or self._live2d_config.default_expression
        self._apply_expression(default_expression, hold_motion=False)
        self._start_idle_motion()
        if self._on_ready is not None:
            self._on_ready()

    def _start_idle_motion(self) -> None:
        if self._model is None:
            return
        motion_file = self._live2d_config.idle_motion_file
        if not motion_file:
            return
        motion_path = self._model_dir / motion_file
        if not motion_path.is_file():
            return
        live2d = get_live2d_module()
        groups = self._model.GetMotionGroups()
        if live2d.MotionGroup.IDLE not in groups or groups[live2d.MotionGroup.IDLE] <= 0:
            if not self._idle_motion_started:
                self._model.LoadExtraMotion(live2d.MotionGroup.IDLE, str(motion_path))
                self._idle_motion_started = True
        self._model.StartMotion(live2d.MotionGroup.IDLE, 0, live2d.MotionPriority.IDLE)

    def _discover_expression_ids(self) -> list[str]:
        ids: set[str] = set()
        if self._model_dir.is_dir():
            for path in self._model_dir.glob("*.exp3.json"):
                expression_id = path.stem.strip()
                if expression_id:
                    ids.add(expression_id)
        if self._ready and self._model is not None:
            for item in self._model.GetExpressionIds():
                if isinstance(item, str):
                    expression_id = item.strip()
                elif isinstance(item, (list, tuple)) and item:
                    expression_id = str(item[0]).strip()
                elif isinstance(item, dict):
                    raw = item.get("Id") or item.get("id") or item.get("Name")
                    expression_id = str(raw).strip() if raw else ""
                else:
                    expression_id = str(item).strip()
                if expression_id:
                    ids.add(expression_id)
        return sorted(ids)

    def _apply_expression(self, expression_id: str | None, *, hold_motion: bool = True) -> None:
        if self._model is None:
            return
        expression_id = (expression_id or "").strip()
        if not expression_id:
            self._expression_motion_hold_until = 0.0
            self._held_expression_id = ""
            self._held_snapshot_applied = False
            self._model.ResetExpression()
            if not hold_motion:
                return
            self._start_idle_motion()
            return
        if expression_id not in set(self._discover_expression_ids()):
            self._model.ResetExpression()
            return
        if hold_motion:
            self._expression_motion_hold_until = time.monotonic() + 2.5
            self._held_expression_id = expression_id
            self._held_snapshot_applied = False
            self._model.StopAllMotions()
            return
        self._held_expression_id = ""
        self._held_snapshot_applied = False
        self._expression_motion_hold_until = 0.0
        self._model.ResetExpression()
        self._model.SetExpression(expression_id)
        self._model._model.UpdateExpression(1.0)

    def _apply_exp3_snapshot(self, expression_id: str) -> bool:
        path = self._model_dir / f"{expression_id}.exp3.json"
        if not path.is_file():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return False
        parameters = data.get("Parameters")
        if not isinstance(parameters, list) or not parameters:
            return False
        self._model.ResetParameters()
        for entry in parameters:
            if not isinstance(entry, dict):
                continue
            param_id = str(entry.get("Id", "")).strip()
            if not param_id:
                continue
            value = float(entry.get("Value", 0.0))
            blend = str(entry.get("Blend", "Add")).strip().lower()
            if blend == "add":
                self._model.AddParameterValue(param_id, value)
            elif blend == "multiply":
                self._model.SetParameterValue(param_id, value)
            else:
                self._model.SetParameterValue(param_id, value)
        return True
