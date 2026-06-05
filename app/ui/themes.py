from __future__ import annotations

from dataclasses import dataclass

UI_THEME_SAKURA = "sakura"
UI_THEME_SKY = "sky"
DEFAULT_UI_THEME = UI_THEME_SKY

UI_THEME_CHOICES: tuple[tuple[str, str], ...] = (
    (UI_THEME_SKY, "浅蓝"),
    (UI_THEME_SAKURA, "樱粉"),
)


@dataclass(frozen=True)
class UIThemePalette:
    id: str
    label: str
    bubble_bg: str
    bubble_border: str
    speaker_name: str
    speech_text: str
    error_text: str
    history_panel_bg: str
    history_panel_border: str
    history_button: str
    history_button_hover: str
    history_button_disabled: str
    input_bg: str
    input_border: str
    input_text: str
    input_selection: str
    input_focus_border: str
    button_bg: str
    button_hover_bg: str
    button_active_bg: str
    button_disabled_bg: str
    button_disabled_border: str
    confirm_button_bg: str
    cancel_button_bg: str
    dialog_bg: str
    dialog_text: str
    tab_pane_bg: str
    tab_pane_border: str
    tab_bg: str
    tab_border: str
    tab_text: str
    tab_selected_text: str
    form_field_border: str
    form_field_focus_border: str
    form_field_selection: str
    table_header_bg: str
    table_header_text: str
    table_grid: str
    table_alt_row: str
    checkbox_text: str
    checkbox_border: str
    checkbox_checked_bg: str
    checkbox_checked_border: str
    hint_text: str
    history_title: str
    history_count_bg: str
    history_count_border: str
    history_count_text: str
    history_scroll_bg: str
    history_scroll_border: str
    assistant_bubble_bg: str
    assistant_bubble_border: str
    user_bubble_bg: str
    user_bubble_border: str
    error_bubble_bg: str
    error_bubble_border: str
    system_bubble_bg: str
    system_bubble_border: str
    entry_meta: str
    system_text: str
    secondary_button_bg: str
    secondary_button_border: str
    secondary_button_hover_bg: str
    danger_button_bg: str
    danger_button_border: str
    danger_button_text: str
    danger_button_hover_bg: str


_PALETTES: dict[str, UIThemePalette] = {
    UI_THEME_SAKURA: UIThemePalette(
        id=UI_THEME_SAKURA,
        label="樱粉",
        bubble_bg="rgba(255, 232, 241, 220)",
        bubble_border="rgba(238, 172, 200, 158)",
        speaker_name="#d55b91",
        speech_text="#4b3440",
        error_text="#9f314e",
        history_panel_bg="rgba(255, 255, 255, 92)",
        history_panel_border="rgba(238, 172, 200, 154)",
        history_button="#7a3656",
        history_button_hover="#b13e73",
        history_button_disabled="rgba(122, 54, 86, 92)",
        input_bg="rgba(255, 255, 255, 96)",
        input_border="rgba(255, 255, 255, 218)",
        input_text="#2f2630",
        input_selection="rgba(213, 91, 145, 92)",
        input_focus_border="rgba(213, 91, 145, 210)",
        button_bg="rgba(213, 91, 145, 232)",
        button_hover_bg="rgba(191, 63, 122, 242)",
        button_active_bg="rgba(177, 62, 115, 242)",
        button_disabled_bg="rgba(213, 91, 145, 118)",
        button_disabled_border="rgba(238, 172, 200, 92)",
        confirm_button_bg="rgba(93, 181, 130, 225)",
        cancel_button_bg="rgba(180, 130, 146, 210)",
        dialog_bg="#fff6fa",
        dialog_text="#3d2b35",
        tab_pane_bg="rgba(255, 232, 241, 0.70)",
        tab_pane_border="rgba(238, 172, 200, 0.54)",
        tab_bg="rgba(255, 232, 241, 0.75)",
        tab_border="rgba(238, 172, 200, 0.48)",
        tab_text="#7a3656",
        tab_selected_text="#b13e73",
        form_field_border="rgba(238, 172, 200, 0.58)",
        form_field_focus_border="rgba(213, 91, 145, 0.76)",
        form_field_selection="rgba(213, 91, 145, 0.28)",
        table_header_bg="#ffe8f1",
        table_header_text="#7a3656",
        table_grid="rgba(238, 172, 200, 0.42)",
        table_alt_row="rgba(255, 244, 249, 0.86)",
        checkbox_text="#4b3440",
        checkbox_border="rgba(213, 91, 145, 0.68)",
        checkbox_checked_bg="#d55b91",
        checkbox_checked_border="#b13e73",
        hint_text="#9b4f72",
        history_title="#7a3656",
        history_count_bg="rgba(255, 232, 241, 0.78)",
        history_count_border="rgba(238, 172, 200, 0.48)",
        history_count_text="#9b4f72",
        history_scroll_bg="rgba(255, 244, 249, 0.94)",
        history_scroll_border="rgba(238, 172, 200, 0.54)",
        assistant_bubble_bg="#fffafd",
        assistant_bubble_border="#f1c7d9",
        user_bubble_bg="#ffe3ee",
        user_bubble_border="#eeb0ca",
        error_bubble_bg="#ffe9e7",
        error_bubble_border="#efc2bd",
        system_bubble_bg="#fff0f6",
        system_bubble_border="#efd0dc",
        entry_meta="#a0647f",
        system_text="#7e5d6b",
        secondary_button_bg="rgba(255, 255, 255, 0.90)",
        secondary_button_border="rgba(238, 172, 200, 0.58)",
        secondary_button_hover_bg="rgba(255, 232, 241, 0.96)",
        danger_button_bg="#fff1f5",
        danger_button_border="rgba(199, 88, 122, 0.52)",
        danger_button_text="#b13e5a",
        danger_button_hover_bg="#ffe1ea",
    ),
    UI_THEME_SKY: UIThemePalette(
        id=UI_THEME_SKY,
        label="浅蓝",
        bubble_bg="rgba(232, 244, 255, 220)",
        bubble_border="rgba(172, 208, 238, 158)",
        speaker_name="#4a9fd9",
        speech_text="#2f4554",
        error_text="#c45c4a",
        history_panel_bg="rgba(255, 255, 255, 92)",
        history_panel_border="rgba(172, 208, 238, 154)",
        history_button="#366580",
        history_button_hover="#2f7eb5",
        history_button_disabled="rgba(54, 101, 128, 92)",
        input_bg="rgba(255, 255, 255, 96)",
        input_border="rgba(255, 255, 255, 218)",
        input_text="#243642",
        input_selection="rgba(74, 159, 217, 92)",
        input_focus_border="rgba(74, 159, 217, 210)",
        button_bg="rgba(74, 159, 217, 232)",
        button_hover_bg="rgba(61, 143, 199, 242)",
        button_active_bg="rgba(52, 128, 184, 242)",
        button_disabled_bg="rgba(74, 159, 217, 118)",
        button_disabled_border="rgba(172, 208, 238, 92)",
        confirm_button_bg="rgba(93, 181, 130, 225)",
        cancel_button_bg="rgba(130, 158, 180, 210)",
        dialog_bg="#f4faff",
        dialog_text="#2a3d4d",
        tab_pane_bg="rgba(232, 244, 255, 0.70)",
        tab_pane_border="rgba(172, 208, 238, 0.54)",
        tab_bg="rgba(232, 244, 255, 0.75)",
        tab_border="rgba(172, 208, 238, 0.48)",
        tab_text="#366580",
        tab_selected_text="#2f7eb5",
        form_field_border="rgba(172, 208, 238, 0.58)",
        form_field_focus_border="rgba(74, 159, 217, 0.76)",
        form_field_selection="rgba(74, 159, 217, 0.28)",
        table_header_bg="#e3f2fc",
        table_header_text="#366580",
        table_grid="rgba(172, 208, 238, 0.42)",
        table_alt_row="rgba(244, 250, 255, 0.86)",
        checkbox_text="#344b5c",
        checkbox_border="rgba(74, 159, 217, 0.68)",
        checkbox_checked_bg="#4a9fd9",
        checkbox_checked_border="#2f7eb5",
        hint_text="#5a8cad",
        history_title="#366580",
        history_count_bg="rgba(232, 244, 255, 0.78)",
        history_count_border="rgba(172, 208, 238, 0.48)",
        history_count_text="#5a8cad",
        history_scroll_bg="rgba(244, 250, 255, 0.94)",
        history_scroll_border="rgba(172, 208, 238, 0.54)",
        assistant_bubble_bg="#f8fcff",
        assistant_bubble_border="#c8dff0",
        user_bubble_bg="#e3f2fc",
        user_bubble_border="#a8d0ea",
        error_bubble_bg="#fff0ee",
        error_bubble_border="#efc2bd",
        system_bubble_bg="#eef7ff",
        system_bubble_border="#cfe3f2",
        entry_meta="#6a8fa8",
        system_text="#5a7285",
        secondary_button_bg="rgba(255, 255, 255, 0.90)",
        secondary_button_border="rgba(172, 208, 238, 0.58)",
        secondary_button_hover_bg="rgba(232, 244, 255, 0.96)",
        danger_button_bg="#fff1f0",
        danger_button_border="rgba(196, 92, 74, 0.52)",
        danger_button_text="#c45c4a",
        danger_button_hover_bg="#ffe6e3",
    ),
}


def normalize_ui_theme(theme_id: str | None) -> str:
    normalized = str(theme_id or "").strip().lower()
    if normalized in _PALETTES:
        return normalized
    return DEFAULT_UI_THEME


def ui_theme_palette(theme_id: str | None) -> UIThemePalette:
    return _PALETTES[normalize_ui_theme(theme_id)]


def build_pet_window_stylesheet(theme_id: str | None) -> str:
    palette = ui_theme_palette(theme_id)
    return f"""
#speechBubble {{
    background: {palette.bubble_bg};
    border: 1px solid {palette.bubble_border};
    border-radius: 26px;
}}
#speakerName {{
    color: {palette.speaker_name};
    font-size: 13px;
    font-weight: 700;
}}
#speechText {{
    color: {palette.speech_text};
    font-size: 16px;
    line-height: 1.35;
}}
#ttsErrorText {{
    color: {palette.error_text};
    font-size: 12px;
    font-weight: 700;
    line-height: 1.25;
}}
#replyHistoryPanel {{
    background: {palette.history_panel_bg};
    border: 1px solid {palette.history_panel_border};
    border-radius: 17px;
}}
#replyHistoryButton {{
    background: transparent;
    border: none;
    border-radius: 11px;
    color: {palette.history_button};
    font-size: 13px;
    font-weight: 900;
}}
#replyHistoryButton:hover {{
    background: rgba(255, 255, 255, 130);
    color: {palette.history_button_hover};
}}
#replyHistoryButton:disabled {{
    background: transparent;
    color: {palette.history_button_disabled};
}}
#inputBar {{
    background: transparent;
    border: none;
}}
#petInput {{
    background: {palette.input_bg};
    border: 1px solid {palette.input_border};
    border-radius: 16px;
    color: {palette.input_text};
    font-size: 13px;
    font-weight: 700;
    padding: 2px 12px;
    selection-background-color: {palette.input_selection};
}}
#petInput:focus {{
    background: rgba(255, 255, 255, 132);
    border: 1px solid {palette.input_focus_border};
}}
#petInput:disabled {{
    color: rgba(47, 38, 48, 150);
}}
#sendButton, #voiceButton, #screenshotButton {{
    background: {palette.button_bg};
    border: 1px solid rgba(255, 255, 255, 150);
    border-radius: 14px;
    color: white;
    font-size: 13px;
    font-weight: 800;
    padding: 3px 10px;
}}
#sendButton {{
    min-width: 56px;
}}
#voiceButton, #screenshotButton {{
    min-width: 48px;
}}
#sendButton:hover, #voiceButton:hover, #screenshotButton:hover {{
    background: {palette.button_hover_bg};
    border: 1px solid rgba(255, 255, 255, 190);
}}
#voiceButton[recording="true"], #screenshotButton[screenshotAttached="true"] {{
    background: {palette.button_active_bg};
    border: 1px solid rgba(255, 255, 255, 220);
    color: white;
}}
#sendButton:disabled, #voiceButton:disabled, #screenshotButton:disabled {{
    background: {palette.button_disabled_bg};
    border: 1px solid {palette.button_disabled_border};
    color: rgba(255, 255, 255, 178);
}}
#confirmActionButton {{
    background: {palette.confirm_button_bg};
    border: none;
    border-radius: 16px;
    color: white;
    font-size: 15px;
    font-weight: 800;
    min-width: 58px;
    padding: 4px 12px;
}}
#cancelActionButton {{
    background: {palette.cancel_button_bg};
    border: none;
    border-radius: 16px;
    color: white;
    font-size: 15px;
    font-weight: 800;
    min-width: 58px;
    padding: 4px 12px;
}}
#musicLyricsOverlay {{
    background: transparent;
    border: none;
}}
#musicLyricsText {{
    color: rgba(255, 255, 255, 230);
    background: transparent;
    font-size: 15px;
    font-weight: 700;
    line-height: 1.35;
    padding: 0 6px;
}}
"""


def build_settings_dialog_stylesheet(theme_id: str | None) -> str:
    palette = ui_theme_palette(theme_id)
    return f"""
            QDialog {{
                background: {palette.dialog_bg};
                color: {palette.dialog_text};
                font-family: "Microsoft YaHei", "Yu Gothic UI", sans-serif;
                font-size: 14px;
            }}
            QTabWidget::pane {{
                border: 1px solid {palette.tab_pane_border};
                border-radius: 8px;
                background: {palette.tab_pane_bg};
            }}
            QTabBar::tab {{
                background: {palette.tab_bg};
                border: 1px solid {palette.tab_border};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 7px 18px;
                margin-right: 4px;
                color: {palette.tab_text};
            }}
            QTabBar::tab:selected {{
                background: #ffffff;
                color: {palette.tab_selected_text};
                font-weight: 700;
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QTableWidget, QComboBox {{
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid {palette.form_field_border};
                border-radius: 7px;
                padding: 6px 8px;
                color: {palette.dialog_text};
                selection-background-color: {palette.form_field_selection};
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {palette.form_field_focus_border};
                background: #ffffff;
            }}
            QTableWidget {{
                gridline-color: {palette.table_grid};
                alternate-background-color: {palette.table_alt_row};
            }}
            QHeaderView::section {{
                background: {palette.table_header_bg};
                border: 1px solid {palette.form_field_border};
                color: {palette.table_header_text};
                padding: 6px;
                font-weight: 700;
            }}
            QCheckBox {{
                color: {palette.checkbox_text};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {palette.checkbox_border};
                background: #ffffff;
            }}
            QCheckBox::indicator:checked {{
                background: {palette.checkbox_checked_bg};
                border: 1px solid {palette.checkbox_checked_border};
            }}
            QPushButton {{
                background: {palette.speaker_name};
                border: 1px solid {palette.button_active_bg};
                border-radius: 8px;
                color: white;
                min-width: 72px;
                padding: 8px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {palette.button_hover_bg};
            }}
            QPushButton:disabled {{
                background: {palette.button_disabled_bg};
                border: 1px solid {palette.button_disabled_border};
                color: rgba(255, 255, 255, 0.76);
            }}
            """


def build_history_window_stylesheet(theme_id: str | None) -> str:
    palette = ui_theme_palette(theme_id)
    return f"""
            QDialog {{
                background: {palette.dialog_bg};
                color: {palette.dialog_text};
                font-family: "Microsoft YaHei", "Yu Gothic UI", sans-serif;
                font-size: 16px;
            }}
            QLabel#historyTitle {{
                color: {palette.history_title};
                font-size: 22px;
                font-weight: 700;
            }}
            QLabel#historyCount {{
                color: {palette.history_count_text};
                background: {palette.history_count_bg};
                border: 1px solid {palette.history_count_border};
                border-radius: 12px;
                padding: 5px 10px;
                font-size: 13px;
            }}
            QScrollArea#historyScroll {{
                background: {palette.history_scroll_bg};
                border: 1px solid {palette.history_scroll_border};
                border-radius: 14px;
            }}
            QWidget#historyContent {{
                background: transparent;
            }}
            QFrame#assistantBubble {{
                background: {palette.assistant_bubble_bg};
                border: 1px solid {palette.assistant_bubble_border};
                border-radius: 14px;
            }}
            QFrame#userBubble {{
                background: {palette.user_bubble_bg};
                border: 1px solid {palette.user_bubble_border};
                border-radius: 14px;
            }}
            QFrame#errorBubble {{
                background: {palette.error_bubble_bg};
                border: 1px solid {palette.error_bubble_border};
                border-radius: 14px;
            }}
            QFrame#systemBubble {{
                background: {palette.system_bubble_bg};
                border: 1px solid {palette.system_bubble_border};
                border-radius: 12px;
            }}
            QLabel#entryMeta {{
                color: {palette.entry_meta};
                font-size: 13px;
            }}
            QLabel#entryText {{
                color: {palette.dialog_text};
                font-size: 16px;
                line-height: 155%;
            }}
            QLabel#errorText {{
                color: {palette.error_text};
                font-size: 16px;
                line-height: 155%;
            }}
            QLabel#systemText {{
                color: {palette.system_text};
                font-size: 15px;
                line-height: 155%;
            }}
            QPushButton#historyPlayButton {{
                background: {palette.assistant_bubble_bg};
                border: 1px solid {palette.assistant_bubble_border};
                border-radius: 10px;
                color: {palette.history_button};
                min-width: 0;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#historyPlayButton:hover {{
                background: {palette.secondary_button_hover_bg};
                border: 1px solid {palette.input_focus_border};
            }}
            QPushButton#historyPlayButton:disabled {{
                color: {palette.entry_meta};
                background: {palette.system_bubble_bg};
                border: 1px solid {palette.system_bubble_border};
            }}
            QPushButton {{
                background: {palette.secondary_button_bg};
                border: 1px solid {palette.secondary_button_border};
                border-radius: 8px;
                color: {palette.history_button};
                min-width: 72px;
                padding: 8px 12px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {palette.secondary_button_hover_bg};
                border: 1px solid {palette.input_focus_border};
            }}
            QPushButton#dangerButton {{
                background: {palette.danger_button_bg};
                border: 1px solid {palette.danger_button_border};
                color: {palette.danger_button_text};
            }}
            QPushButton#dangerButton:hover {{
                background: {palette.danger_button_hover_bg};
            }}
            QPushButton#primaryButton {{
                background: {palette.speaker_name};
                border: 1px solid {palette.button_active_bg};
                color: white;
            }}
            QPushButton#primaryButton:hover {{
                background: {palette.button_hover_bg};
            }}
            QPushButton#secondaryButton:default {{
                background: {palette.speaker_name};
                color: white;
            }}
            """
