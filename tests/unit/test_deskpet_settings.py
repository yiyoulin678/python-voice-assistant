from app.config.deskpet_settings import (
    PANEL_WIDTH_PERCENT_DEFAULT,
    PANEL_WIDTH_PERCENT_MAX,
    PANEL_WIDTH_PERCENT_MIN,
    PetUISettings,
    normalize_panel_width_percent,
)
from app.ui.pet_window import (
    BUBBLE_MAX_WIDTH,
    DEFAULT_STAGE_WIDTH,
    _bubble_layout_width,
    _stage_size_for_layout,
)


def test_normalize_panel_width_percent_clamps_invalid_values() -> None:
    assert normalize_panel_width_percent(100) == 100
    assert normalize_panel_width_percent(10) == PANEL_WIDTH_PERCENT_MIN
    assert normalize_panel_width_percent(200) == 200
    assert normalize_panel_width_percent(600) == PANEL_WIDTH_PERCENT_MAX
    assert normalize_panel_width_percent("oops") == PANEL_WIDTH_PERCENT_DEFAULT


def test_pet_ui_settings_normalizes_panel_width_percent() -> None:
    settings = PetUISettings(panel_width_percent=999).normalized()
    assert settings.panel_width_percent == PANEL_WIDTH_PERCENT_MAX


def test_stage_size_scales_width_with_panel_width_percent() -> None:
    default_width, default_height = _stage_size_for_layout(100, 100)
    narrow_width, narrow_height = _stage_size_for_layout(100, 80)

    assert default_width == DEFAULT_STAGE_WIDTH
    assert default_height == 500
    assert narrow_width < default_width
    assert narrow_height == default_height


def test_bubble_layout_width_scales_with_panel_width_percent() -> None:
    default_bubble = _bubble_layout_width(DEFAULT_STAGE_WIDTH, 100)
    narrow_bubble = _bubble_layout_width(DEFAULT_STAGE_WIDTH, 80)

    assert default_bubble == BUBBLE_MAX_WIDTH
    assert narrow_bubble < default_bubble
