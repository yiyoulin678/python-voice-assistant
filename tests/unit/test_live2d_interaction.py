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
    widget.play_idle_motion_burst = MagicMock()
    widget.update = MagicMock()
    controller = Live2DInteractionController(
        widget,
        config,
        restore_expression=lambda: None,
    )
    controller._started = True
    controller.handle_tap(100.0, 200.0)
    widget.set_expression.assert_called_once()
    widget.play_idle_motion_burst.assert_called_once()
    widget.update.assert_called_once()
