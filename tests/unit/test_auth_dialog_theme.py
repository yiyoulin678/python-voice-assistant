from __future__ import annotations

from app.ui.themes import (
    UI_THEME_SAKURA,
    UI_THEME_SKY,
    build_auth_dialog_stylesheet,
    normalize_ui_theme,
)


def test_build_auth_dialog_stylesheet_contains_theme_tokens() -> None:
    sky = build_auth_dialog_stylesheet(UI_THEME_SKY)
    sakura = build_auth_dialog_stylesheet(UI_THEME_SAKURA)
    assert "authPrimaryButton" in sky
    assert "authCard" in sakura
    assert "#f4faff" in sky
    assert "#fff6fa" in sakura


def test_normalize_ui_theme_fallback() -> None:
    assert normalize_ui_theme("unknown") == UI_THEME_SKY
