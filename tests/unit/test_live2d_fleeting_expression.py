from __future__ import annotations

from unittest.mock import MagicMock

from app.ui.live2d_widget import Live2DWidget


def test_show_fleeting_expression_replaces_previous_layer() -> None:
    widget = Live2DWidget.__new__(Live2DWidget)
    widget._ready = True
    widget._model = MagicMock()
    widget._fleeting_expression_ids = ["shy"]
    widget._persistent_expression_id = "exp1"
    widget._overlay_expressions = set()
    widget.makeCurrent = MagicMock()  # type: ignore[method-assign]
    widget.update = MagicMock()  # type: ignore[method-assign]
    widget._discover_expression_ids = MagicMock(  # type: ignore[method-assign]
        return_value=["shy", "abb", "exp1"],
    )
    widget._restore_expression_overlays = MagicMock()  # type: ignore[method-assign]

    widget.show_fleeting_expression("abb")

    widget._model.RemoveExpression.assert_called_once_with("shy")
    widget._model.SetExpression.assert_called_once_with("abb")
    assert widget._fleeting_expression_ids == ["abb"]
