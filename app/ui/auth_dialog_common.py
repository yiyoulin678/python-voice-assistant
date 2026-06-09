from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.ui.themes import DEFAULT_UI_THEME, build_auth_dialog_stylesheet, normalize_ui_theme


def resolve_auth_ui_theme(base_dir: Path | None) -> str:
    if base_dir is None:
        return DEFAULT_UI_THEME
    try:
        from app.config.settings_service import AppSettingsService

        settings = AppSettingsService(base_dir=base_dir).load_pet_ui_settings()
        return settings.normalized().ui_theme
    except OSError:
        return DEFAULT_UI_THEME


def apply_auth_dialog_theme(dialog: QDialog, theme_id: str | None) -> str:
    normalized = normalize_ui_theme(theme_id)
    dialog.setObjectName("authDialog")
    dialog.setStyleSheet(build_auth_dialog_stylesheet(normalized))
    return normalized


def build_auth_header(
    parent: QWidget,
    *,
    title: str,
    subtitle: str,
) -> tuple[QLabel, QLabel]:
    title_label = QLabel(title, parent)
    title_label.setObjectName("authTitle")
    title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

    subtitle_label = QLabel(subtitle, parent)
    subtitle_label.setObjectName("authSubtitle")
    subtitle_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    subtitle_label.setWordWrap(True)
    return title_label, subtitle_label


def build_auth_card(parent: QWidget) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame(parent)
    card.setObjectName("authCard")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(22, 18, 22, 22)
    card_layout.setSpacing(12)

    accent = QFrame(card)
    accent.setObjectName("authAccentBar")
    card_layout.addWidget(accent)
    return card, card_layout


def build_auth_field(
    parent: QWidget,
    *,
    label: str,
    placeholder: str,
    password: bool = False,
) -> tuple[QLabel, QLineEdit]:
    field_label = QLabel(label, parent)
    field_label.setObjectName("authFieldLabel")
    field_input = QLineEdit(parent)
    field_input.setObjectName("authInput")
    field_input.setPlaceholderText(placeholder)
    if password:
        field_input.setEchoMode(QLineEdit.EchoMode.Password)
    return field_label, field_input
