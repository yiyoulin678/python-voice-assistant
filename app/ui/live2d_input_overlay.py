from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget

LONG_PRESS_MS = 520
DRAG_THRESHOLD = 18


class Live2DInputOverlay(QWidget):
    """盖在 Live2D OpenGL 控件上的透明层，负责接收鼠标（Windows 下 GL 控件常收不到事件）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("live2dInputOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self._mouse_handler: Callable[[QMouseEvent], bool] | None = None
        self._press_position: QPointF | None = None
        self._press_global: QPointF | None = None
        self._on_tap: Callable[[QPointF], None] | None = None
        self._on_long_press_start: Callable[[], None] | None = None
        self._on_long_press_end: Callable[[], None] | None = None
        self._dragging = False
        self._long_press_triggered = False
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._trigger_long_press)

    def bind_mouse_handler(self, handler: Callable[[QMouseEvent], bool] | None) -> None:
        self._mouse_handler = handler

    def bind_tap_handler(self, handler: Callable[[QPointF], None] | None) -> None:
        self._on_tap = handler

    def bind_long_press_handlers(
        self,
        on_start: Callable[[], None] | None,
        on_end: Callable[[], None] | None,
    ) -> None:
        self._on_long_press_start = on_start
        self._on_long_press_end = on_end

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        # Windows 下全透明控件常不参与命中测试，用极低 alpha 铺满以接收鼠标
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

    def _dispatch(self, event: QMouseEvent) -> bool:
        if self._mouse_handler is not None and self._mouse_handler(event):
            return True
        return False

    def _reset_press_state(self) -> None:
        self._press_position = None
        self._press_global = None
        self._dragging = False
        self._long_press_triggered = False

    def _trigger_long_press(self) -> None:
        if self._press_position is None or self._dragging:
            return
        self._long_press_triggered = True
        if self._on_long_press_start is not None:
            self._on_long_press_start()

    def _synthetic_press_event(self) -> QMouseEvent | None:
        if self._press_position is None or self._press_global is None:
            return None
        return QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            self._press_position,
            self._press_global,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            if self._dispatch(event):
                return
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_timer.stop()
            self._press_position = event.position()
            self._press_global = event.globalPosition()
            self._dragging = False
            self._long_press_triggered = False
            if self._on_long_press_start is not None:
                self._long_press_timer.start(LONG_PRESS_MS)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._press_position is not None
            and not self._dragging
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = event.position() - self._press_position
            if delta.manhattanLength() > DRAG_THRESHOLD:
                self._long_press_timer.stop()
                if self._long_press_triggered:
                    if self._on_long_press_end is not None:
                        self._on_long_press_end()
                    self._reset_press_state()
                    return
                press_event = self._synthetic_press_event()
                if press_event is not None and self._dispatch(press_event):
                    self._dragging = True
        if self._dragging and self._dispatch(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            if self._dispatch(event):
                return
            super().mouseReleaseEvent(event)
            return

        self._long_press_timer.stop()
        if self._long_press_triggered:
            if self._on_long_press_end is not None:
                self._on_long_press_end()
            self._reset_press_state()
            event.accept()
            return

        if (
            self._press_position is not None
            and not self._dragging
            and self._on_tap is not None
        ):
            delta = event.position() - self._press_position
            if delta.manhattanLength() <= DRAG_THRESHOLD:
                self._on_tap(event.position())

        if self._dragging:
            self._dispatch(event)
        self._reset_press_state()
        event.accept()
