from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QWidget


def wrap_scrollable(content: QWidget, *, parent: QWidget | None = None) -> QScrollArea:
    """把设置子页包进可滚动区域，避免小窗口里内容被裁切。"""
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content.setSizePolicy(
        QSizePolicy.Policy.Preferred,
        QSizePolicy.Policy.Preferred,
    )
    scroll.setWidget(content)
    return scroll
