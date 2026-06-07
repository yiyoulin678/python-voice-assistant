from pathlib import Path

from app.config.character_loader import CharacterExpressionPreset, CharacterLive2D
from app.ui.live2d_expression_presets import (
    build_manual_expression_presets,
    extra_expression_ids,
    preset_menu_label,
)


def _live2d_config(**kwargs) -> CharacterLive2D:
    defaults = {
        "model_json_path": Path("model/model3.json"),
        "default_expression": "neutral",
        "tone_expressions": {
            "中性": "neutral",
            "害羞": "shy",
        },
        "expression_presets": (),
    }
    defaults.update(kwargs)
    return CharacterLive2D(**defaults)


def test_build_manual_expression_presets_uses_tone_expressions_by_default() -> None:
    presets = build_manual_expression_presets(
        _live2d_config(),
        {"neutral", "shy", "blink"},
    )

    assert [preset.label for preset in presets] == ["中性", "害羞"]
    assert presets[0].expression == "neutral"
    assert presets[0].overlays == ()


def test_build_manual_expression_presets_adds_default_when_not_in_tone_map() -> None:
    presets = build_manual_expression_presets(
        _live2d_config(
            default_expression="base",
            tone_expressions={"害羞": "shy"},
        ),
        {"base", "shy"},
    )

    assert [preset.label for preset in presets] == ["默认", "害羞"]


def test_build_manual_expression_presets_prefers_expression_presets() -> None:
    presets = build_manual_expression_presets(
        _live2d_config(
            expression_presets=(
                CharacterExpressionPreset(
                    label="脸红害羞",
                    expression="shy",
                    overlays=("blush",),
                ),
            )
        ),
        {"shy", "blush"},
    )

    assert len(presets) == 1
    assert presets[0].label == "脸红害羞"
    assert presets[0].overlays == ("blush",)


def test_extra_expression_ids_hides_preset_members() -> None:
    presets = [
        CharacterExpressionPreset(label="害羞", expression="shy", overlays=("blush",)),
    ]
    assert extra_expression_ids({"shy", "blush", "wink"}, presets) == ["wink"]


def test_preset_menu_label_shows_overlay_count() -> None:
    preset = CharacterExpressionPreset(label="害羞", expression="shy", overlays=("a", "b"))
    assert preset_menu_label(preset) == "害羞（+2）"
