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
    applied: list[str] = []

    def capture_tap(expression_id: str) -> None:
        applied.append(expression_id)

    controller._on_tap_expression = capture_tap  # type: ignore[method-assign]
    controller.handle_tap(100.0, 200.0)
    assert len(applied) == 1
    assert applied[0] in {"sur1", "shy"}
    widget.show_fleeting_expression.assert_not_called()
    widget.set_persistent_expression.assert_not_called()
    widget.update.assert_called_once()


def test_handle_tap_uses_expression_even_when_tap_motions_configured() -> None:
    config = CharacterLive2D(
        model_json_path=__import__("pathlib").Path("model.model3.json"),
        tap_motions=("有点不好意思而摇晃身体",),
        tap_expressions=("shy",),
    )
    widget = MagicMock()
    widget.is_ready.return_value = True
    widget.update = MagicMock()
    controller = Live2DInteractionController(
        widget,
        config,
        restore_expression=lambda: None,
    )
    controller._started = True
    applied: list[str] = []
    controller._on_tap_expression = applied.append  # type: ignore[method-assign]
    controller.handle_tap(10.0, 20.0)
    widget.play_motion_by_name.assert_not_called()
    widget.show_fleeting_expression.assert_not_called()
    assert applied == ["shy"]


def test_idle_variation_keeps_expression_until_next_schedule() -> None:
    config = CharacterLive2D(
        model_json_path=__import__("pathlib").Path("model.model3.json"),
        idle_variation_expressions=("think", "abb"),
        idle_variation_min_seconds=12.0,
        idle_variation_max_seconds=12.0,
    )
    widget = MagicMock()
    widget.is_ready.return_value = True
    widget.is_holding_expression.return_value = False
    widget.update = MagicMock()
    applied: list[str] = []
    controller = Live2DInteractionController(
        widget,
        config,
        restore_expression=lambda: None,
        on_tap_expression=applied.append,
    )
    controller._started = True
    controller._play_idle_variation()

    assert len(applied) == 1
    assert applied[0] in {"think", "abb"}
    widget.show_fleeting_expression.assert_not_called()
    assert controller._fleeting_timer.isActive() is False
