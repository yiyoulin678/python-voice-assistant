from __future__ import annotations

from unittest.mock import MagicMock

from app.config.character_loader import CharacterLive2D
from app.ui.live2d_interaction import Live2DInteractionController


def test_handle_tap_plays_expression() -> None:
    config = CharacterLive2D(
        model_json_path=__import__("pathlib").Path("model.model3.json"),
        tap_expressions=("sur1", "shy"),
    )
    widget = MagicMock()
    widget.is_ready.return_value = True
    widget.play_motion_by_name.return_value = False
    widget.update = MagicMock()
    controller = Live2DInteractionController(
        widget,
        config,
        restore_expression=lambda: None,
    )
    controller._started = True
    controller.handle_tap(100.0, 200.0)
    widget.show_fleeting_expression.assert_called_once()
    widget.update.assert_called_once()


def test_handle_tap_prefers_motion_over_expression() -> None:
    config = CharacterLive2D(
        model_json_path=__import__("pathlib").Path("model.model3.json"),
        tap_motions=("有点不好意思而摇晃身体",),
        tap_expressions=("shy",),
    )
    widget = MagicMock()
    widget.is_ready.return_value = True
    widget.play_motion_by_name.return_value = True
    widget.update = MagicMock()
    controller = Live2DInteractionController(
        widget,
        config,
        restore_expression=lambda: None,
    )
    controller._started = True
    controller.handle_tap(10.0, 20.0)
    widget.play_motion_by_name.assert_called_once()
    widget.show_fleeting_expression.assert_not_called()
