from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QWidget


def apply_locked_window_region(window: QWidget, locked: bool) -> None:
    """兼容旧调用：按当前布局刷新窗口命中区域。"""
    refresh_window_hit_region(window)


def refresh_window_hit_region(window: QWidget) -> None:
    """把窗口命中区域裁到立绘/可见 UI，空白边距穿透到桌面（仅 Windows）。"""
    if sys.platform != "win32":
        return
    import ctypes

    hwnd = int(window.winId())
    if hwnd == 0:
        return

    rect = _window_hit_rect(window)
    if rect is None or rect.isEmpty():
        ctypes.windll.user32.SetWindowRgn(hwnd, 0, True)
        return

    left, top, right, bottom = _native_rect_edges(window, rect)
    region = ctypes.windll.gdi32.CreateRectRgn(left, top, right, bottom)
    if not region:
        return
    ctypes.windll.user32.SetWindowRgn(hwnd, region, True)


def _window_hit_rect(window: QWidget) -> QRect | None:
    if bool(getattr(window, "ui_locked", False)):
        return portrait_hit_rect(window)

    hover_only = bool(getattr(window, "_live2d_hover_ui", False))
    if hover_only and not _ui_controls_visible(window):
        return portrait_hit_rect(window)

    return interactive_content_rect(window)


def _ui_controls_visible(window: QWidget) -> bool:
    visible = getattr(window, "_ui_controls_visible_applied", None)
    if isinstance(visible, bool):
        return visible
    checker = getattr(window, "_ui_controls_visible", None)
    if callable(checker):
        return bool(checker())
    return True


def interactive_content_rect(window: QWidget) -> QRect | None:
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QWidget as QtWidget

    bounds: QRect | None = None
    portrait = portrait_hit_rect(window)
    if portrait is not None and not portrait.isEmpty():
        bounds = QRect(portrait)

    for name in ("speechBubble", "inputBar", "musicLyricsOverlay"):
        child = window.findChild(QtWidget, name)
        if child is None or not child.isVisible():
            continue
        geometry = child.geometry()
        if geometry.isEmpty():
            continue
        bounds = geometry if bounds is None else bounds.united(geometry)

    return bounds


def portrait_hit_rect(window: QWidget) -> QRect | None:
    from PySide6.QtCore import QPoint, QRect

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


def point_in_portrait(window: QWidget, local: "QPoint") -> bool:
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
            stage.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay = getattr(controller, "input_overlay", None)
        if overlay is not None:
            overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            overlay.setEnabled(True)


def _native_rect_edges(window: QWidget, rect: QRect) -> tuple[int, int, int, int]:
    ratio = float(window.devicePixelRatioF())
    if ratio <= 0:
        ratio = 1.0
    left = int(rect.left() * ratio)
    top = int(rect.top() * ratio)
    right = int(rect.right() * ratio) + 1
    bottom = int(rect.bottom() * ratio) + 1
    return left, top, right, bottom
