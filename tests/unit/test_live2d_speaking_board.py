from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.config.character_loader import CharacterLive2D
from app.ui.live2d_portrait_controller import Live2DPortraitController
from app.ui.live2d_widget import Live2DWidget


def test_set_persistent_expression_restores_speaking_overlays() -> None:
    widget = Live2DWidget.__new__(Live2DWidget)
    widget._ready = True
    widget._model = MagicMock()
    widget._persistent_expression_id = None
    widget._fleeting_expression_ids = []
    widget._overlay_expressions = {"writenote", "note"}
    widget._held_expression_id = ""
    widget._held_snapshot_applied = False
    widget._expression_motion_hold_until = 0.0
    widget._expression_resume_after_hold = ""
    widget._discover_expression_ids = MagicMock(  # type: ignore[method-assign]
        return_value=["exp1", "writenote", "note"],
    )
    widget._resume_idle_motion = MagicMock()  # type: ignore[method-assign]
    widget.makeCurrent = MagicMock()  # type: ignore[method-assign]
    widget.clear_fleeting_expressions = MagicMock()  # type: ignore[method-assign]
    widget._restore_expression_overlays = Live2DWidget._restore_expression_overlays.__get__(  # type: ignore[method-assign]
        widget,
        Live2DWidget,
    )
    widget.update = MagicMock()  # type: ignore[method-assign]

    widget.set_persistent_expression("exp1")

    widget._model.SetExpression.assert_called_once_with("exp1")
    assert widget._model.AddExpression.call_count == 2
    widget._model.AddExpression.assert_any_call("writenote")
    widget._model.AddExpression.assert_any_call("note")


def test_begin_speech_segment_applies_board_expressions() -> None:
    config = CharacterLive2D(
        model_json_path=Path("model.model3.json"),
        speaking_expression="writenote",
        speaking_overlay_expressions=("note",),
    )
    controller = Live2DPortraitController.__new__(Live2DPortraitController)
    controller.live2d_config = config
    controller._is_speaking = False
    controller.live2d_widget = MagicMock()
    controller._lip_sync = MagicMock()
    controller._apply_speaking_expressions = Live2DPortraitController._apply_speaking_expressions.__get__(  # type: ignore[method-assign]
        controller,
        Live2DPortraitController,
    )

    controller.begin_speech_segment()

    assert controller._is_speaking is True
    controller.live2d_widget.add_expression_overlay.assert_any_call("writenote")
    controller.live2d_widget.add_expression_overlay.assert_any_call("note")
