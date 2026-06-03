from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QWidget


def apply_locked_window_region(window: QWidget, locked: bool) -> None:
    """锁定后把窗口命中/绘制区域裁成仅立绘矩形，其余区域穿透到桌面。"""
    if sys.platform != "win32":
        return
    import ctypes

    hwnd = int(window.winId())
    if hwnd == 0:
        return

    if not locked:
        ctypes.windll.user32.SetWindowRgn(hwnd, 0, True)
        return

    rect = portrait_hit_rect(window)
    if rect is None or rect.isEmpty():
        return

    left, top, right, bottom = _native_rect_edges(window, rect)
    region = ctypes.windll.gdi32.CreateRectRgn(left, top, right, bottom)
    if not region:
        return
    ctypes.windll.user32.SetWindowRgn(hwnd, region, True)


def portrait_hit_rect(window: QWidget) -> QRect | None:
    from PySide6.QtCore import QRect

    cached = getattr(window, "_portrait_hit_rect", None)
    if isinstance(cached, QRect) and not cached.isEmpty():
        return cached

    controller = getattr(window, "portrait_controller", None)
    if controller is None:
        return None
    stage = getattr(controller, "portrait_stage_widget", None)
    if stage is None or not stage.isVisible():
        return None
    top_left = stage.mapTo(window, QPoint(0, 0))
    return QRect(top_left, stage.size())


def point_in_portrait(window: QWidget, local: QPoint) -> bool:
    rect = portrait_hit_rect(window)
    if rect is None:
        return False
    return rect.contains(local)


def apply_locked_mouse_transparency(window: QWidget, locked: bool) -> None:
    """歌词层等叠在立绘上的控件不参与命中，事件落到 Live2D。"""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget

    passthrough_names = {
        "speechBubble",
        "inputBar",
        "inputBackdrop",
        "musicLyricsOverlay",
    }
    for child in window.findChildren(QWidget):
        if child is window:
            continue
        name = child.objectName()
        if name in passthrough_names or child is getattr(window, "label", None):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, locked)

    controller = getattr(window, "portrait_controller", None)
    if controller is not None:
        stage = getattr(controller, "portrait_stage_widget", None)
        if stage is not None:
            stage.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            stage.setEnabled(True)


def _native_rect_edges(window: QWidget, rect: QRect) -> tuple[int, int, int, int]:
    ratio = float(window.devicePixelRatioF())
    if ratio <= 0:
        ratio = 1.0
    left = int(rect.left() * ratio)
    top = int(rect.top() * ratio)
    right = int(rect.right() * ratio) + 1
    bottom = int(rect.bottom() * ratio) + 1
    return left, top, right, bottom
