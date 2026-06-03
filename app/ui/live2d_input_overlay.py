from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget


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
        self._on_tap: Callable[[QPointF], None] | None = None

    def bind_mouse_handler(self, handler: Callable[[QMouseEvent], bool] | None) -> None:
        self._mouse_handler = handler

    def bind_tap_handler(self, handler: Callable[[QPointF], None] | None) -> None:
        self._on_tap = handler

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        # Windows 下全透明控件常不参与命中测试，用极低 alpha 铺满以接收鼠标
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

    def _dispatch(self, event: QMouseEvent) -> bool:
        if self._mouse_handler is not None and self._mouse_handler(event):
            return True
        return False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position()
        if self._dispatch(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dispatch(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._press_position is not None
            and self._on_tap is not None
        ):
            delta = event.position() - self._press_position
            if delta.manhattanLength() <= 18:
                self._on_tap(event.position())
        self._press_position = None
        if self._dispatch(event):
            return
        super().mouseReleaseEvent(event)
