from __future__ import annotations

from app.config.deskpet_settings import PetUISettings
from app.ui.themes import (
    DEFAULT_UI_THEME,
    UI_THEME_SAKURA,
    UI_THEME_SKY,
    build_pet_window_stylesheet,
    normalize_ui_theme,
)


def test_normalize_ui_theme_defaults_to_sky() -> None:
    assert normalize_ui_theme(None) == DEFAULT_UI_THEME
    assert normalize_ui_theme("") == UI_THEME_SKY
    assert normalize_ui_theme("unknown") == UI_THEME_SKY
    assert normalize_ui_theme(UI_THEME_SAKURA) == UI_THEME_SAKURA


def test_pet_ui_settings_persist_theme() -> None:
    settings = PetUISettings(ui_theme=UI_THEME_SAKURA).normalized()
    assert settings.ui_theme == UI_THEME_SAKURA


def test_stylesheets_include_theme_accent() -> None:
    sky = build_pet_window_stylesheet(UI_THEME_SKY)
    sakura = build_pet_window_stylesheet(UI_THEME_SAKURA)
    assert "#4a9fd9" in sky
    assert "#d55b91" in sakura
