from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.ui.live2d_input_overlay import DRAG_THRESHOLD, Live2DInputOverlay


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _mouse_event(
    event_type: QMouseEvent.Type,
    *,
    local: QPointF,
    global_pos: QPointF,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
    buttons: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> QMouseEvent:
    return QMouseEvent(
        event_type,
        local,
        global_pos,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def test_long_press_triggers_voice_handlers(qapp: QApplication) -> None:
    overlay = Live2DInputOverlay()
    overlay.resize(200, 200)
    on_start = MagicMock()
    on_end = MagicMock()
    overlay.bind_long_press_handlers(on_start, on_end)

    press = _mouse_event(
        QMouseEvent.Type.MouseButtonPress,
        local=QPointF(40, 40),
        global_pos=QPointF(140, 140),
        buttons=Qt.MouseButton.LeftButton,
    )
    overlay.mousePressEvent(press)
    overlay._long_press_timer.timeout.emit()
    on_start.assert_called_once()

    release = _mouse_event(
        QMouseEvent.Type.MouseButtonRelease,
        local=QPointF(40, 40),
        global_pos=QPointF(140, 140),
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.NoButton,
    )
    overlay.mouseReleaseEvent(release)
    on_end.assert_called_once()


def test_short_tap_still_fires_without_long_press(qapp: QApplication) -> None:
    overlay = Live2DInputOverlay()
    overlay.resize(200, 200)
    on_tap = MagicMock()
    on_start = MagicMock()
    overlay.bind_tap_handler(on_tap)
    overlay.bind_long_press_handlers(on_start, MagicMock())

    press = _mouse_event(
        QMouseEvent.Type.MouseButtonPress,
        local=QPointF(20, 20),
        global_pos=QPointF(120, 120),
        buttons=Qt.MouseButton.LeftButton,
    )
    overlay.mousePressEvent(press)
    release = _mouse_event(
        QMouseEvent.Type.MouseButtonRelease,
        local=QPointF(21, 21),
        global_pos=QPointF(121, 121),
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.NoButton,
    )
    overlay.mouseReleaseEvent(release)

    on_tap.assert_called_once()
    on_start.assert_not_called()


def test_drag_threshold_cancels_long_press_and_uses_mouse_handler(qapp: QApplication) -> None:
    overlay = Live2DInputOverlay()
    overlay.resize(200, 200)
    handler = MagicMock(return_value=True)
    on_start = MagicMock()
    overlay.bind_mouse_handler(handler)
    overlay.bind_long_press_handlers(on_start, MagicMock())

    press = _mouse_event(
        QMouseEvent.Type.MouseButtonPress,
        local=QPointF(10, 10),
        global_pos=QPointF(110, 110),
        buttons=Qt.MouseButton.LeftButton,
    )
    overlay.mousePressEvent(press)
    move = _mouse_event(
        QMouseEvent.Type.MouseMove,
        local=QPointF(10 + DRAG_THRESHOLD + 4, 10),
        global_pos=QPointF(110 + DRAG_THRESHOLD + 4, 110),
        buttons=Qt.MouseButton.LeftButton,
    )
    overlay.mouseMoveEvent(move)

    on_start.assert_not_called()
    assert handler.call_count >= 1
