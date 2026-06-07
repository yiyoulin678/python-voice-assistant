from __future__ import annotations

from app.config.character_loader import CharacterExpressionPreset, CharacterLive2D


def build_manual_expression_presets(
    live2d_config: CharacterLive2D,
    available_expression_ids: set[str],
) -> list[CharacterExpressionPreset]:
    """把角色配置里的语气/组合预设整理成可选手动菜单项。"""

    if live2d_config.expression_presets:
        configured = list(live2d_config.expression_presets)
    else:
        configured = [
            CharacterExpressionPreset(label=label, expression=expression_id)
            for label, expression_id in live2d_config.tone_expressions.items()
        ]

    presets: list[CharacterExpressionPreset] = []
    for preset in configured:
        if not _preset_available(preset, available_expression_ids):
            continue
        presets.append(preset)

    default_expression = (live2d_config.default_expression or "").strip()
    if default_expression and default_expression in available_expression_ids:
        if not any(
            preset.expression == default_expression and not preset.overlays
            for preset in presets
        ):
            presets.insert(
                0,
                CharacterExpressionPreset(label="默认", expression=default_expression),
            )
    return presets


def extra_expression_ids(
    available_expression_ids: set[str],
    presets: list[CharacterExpressionPreset],
) -> list[str]:
    covered = {preset.expression for preset in presets}
    for preset in presets:
        covered.update(preset.overlays)
    return sorted(expression_id for expression_id in available_expression_ids if expression_id not in covered)


def preset_menu_label(preset: CharacterExpressionPreset) -> str:
    if not preset.overlays:
        return preset.label
    return f"{preset.label}（+{len(preset.overlays)}）"


def _preset_available(
    preset: CharacterExpressionPreset,
    available_expression_ids: set[str],
) -> bool:
    if preset.expression not in available_expression_ids:
        return False
    return all(overlay in available_expression_ids for overlay in preset.overlays)
