from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QDoubleSpinBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.agent.memory import MemoryStore
from app.agent.mcp import MCPRuntimeSettings
from app.config.character_archive import (
    CharacterArchiveError,
    export_character_archive,
    import_character_archive,
)
from app.agent.memory_curator import (
    DEFAULT_AUTO_MEMORY_BACKFILL_LIMIT,
    DEFAULT_AUTO_MEMORY_TRIGGER_TURNS,
    MemoryCurationSettings,
)
from app.config.deskpet_settings import (
    PANEL_WIDTH_PERCENT_MAX,
    PANEL_WIDTH_PERCENT_MIN,
    REMINDER_CHECK_INTERVAL_DEFAULT_SECONDS,
    REMINDER_CHECK_INTERVAL_MAX_SECONDS,
    REMINDER_CHECK_INTERVAL_MIN_SECONDS,
    PetUISettings,
    ReminderSettings,
    ScreenObservationSettings,
    SUBTITLE_LANGUAGE_JA,
    SUBTITLE_LANGUAGE_ZH,
    normalize_panel_width_percent,
)
from app.config.settings_service import AppSettingsService, DebugLogSettings
from app.llm.api_client import ApiSettings, OpenAICompatibleClient
from app.config.character_loader import (
    CharacterConfigError,
    CharacterProfile,
    CharacterRegistry,
    read_character_card,
    write_character_card,
)
from app.ui.themes import (
    UI_THEME_CHOICES,
    build_settings_dialog_stylesheet,
    ui_theme_palette,
)
from app.ui.portrait_controller import (
    PORTRAIT_SCALE_DEFAULT_PERCENT,
    PORTRAIT_SCALE_MAX_PERCENT,
    PORTRAIT_SCALE_MIN_PERCENT,
    normalize_portrait_scale_percent,
)
from app.ui.subtitle_controller import (
    REPLY_SEGMENT_PAUSE_MAX_MS,
    REPLY_SEGMENT_PAUSE_MIN_MS,
    REPLY_SEGMENT_PAUSE_MS,
    SPEECH_TYPING_INTERVAL_MS,
    SUBTITLE_TYPING_INTERVAL_MAX_MS,
    SUBTITLE_TYPING_INTERVAL_MIN_MS,
    normalize_subtitle_display_speed,
)
from app.agent.proactive_care import (
    PROACTIVE_MAX_COOLDOWN_MINUTES,
    PROACTIVE_MAX_CHECK_INTERVAL_MINUTES,
    PROACTIVE_MAX_SCREEN_CONTEXT_BATCH_LIMIT,
    PROACTIVE_MIN_COOLDOWN_MINUTES,
    PROACTIVE_MIN_CHECK_INTERVAL_MINUTES,
    PROACTIVE_MIN_SCREEN_CONTEXT_BATCH_LIMIT,
    ProactiveCareSettings,
)
from app.voice import audio_io
from app.voice.stt_settings import (
    DEFAULT_WHISPER_LANGUAGE,
    DEFAULT_WHISPER_MODEL_NAME,
    STTSettings,
)
from app.voice.tts import (
    DEFAULT_GPT_SOVITS_API_URL,
    TTS_PROVIDER_GPT_SOVITS,
    GPTSoVITSTTSSettings,
    TTSConfigError,
)
from app.platforms.napcat.network import suggested_connect_hosts
from app.platforms.napcat.settings import (
    DEFAULT_NAPCAT_BIND_HOST,
    DEFAULT_NAPCAT_HOST,
    DEFAULT_NAPCAT_PATH,
    DEFAULT_NAPCAT_PORT,
    NAPCAT_REPLY_BOTH,
    NAPCAT_REPLY_TEXT_ONLY,
    NAPCAT_REPLY_VOICE_ONLY,
    NapCatSettings,
)
from app.ui.tts_bundle_dialog import TTSBundleDownloadDialog
from sdk.types import ToolsTabContribution


class ApiConnectionTestWorker(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, settings: ApiSettings) -> None:
        super().__init__()
        self.settings = settings

    @Slot()
    def run(self) -> None:
        try:
            message = OpenAICompatibleClient(self.settings).test_connection()
        except Exception as exc:  # UI 边界统一转成可读错误。
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(message)
        finally:
            self.finished.emit()


class MemoryListWorker(QObject):
    succeeded = Signal(list)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, memory_store: MemoryStore, limit: int = 200) -> None:
        super().__init__()
        self.memory_store = memory_store
        self.limit = limit

    @Slot()
    def run(self) -> None:
        try:
            memories = self.memory_store.list_memories(limit=self.limit)
        except Exception as exc:  # UI 边界统一转成可读错误。
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(memories)
        finally:
            self.finished.emit()


class CharacterArchiveExportWorker(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, profile: CharacterProfile, output_path: Path) -> None:
        super().__init__()
        self.profile = profile
        self.output_path = output_path

    @Slot()
    def run(self) -> None:
        try:
            export_character_archive(self.profile, self.output_path)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(str(self.output_path))
        finally:
            self.finished.emit()


class SettingsDialog(QDialog):
    def __init__(
        self,
        api_settings: ApiSettings,
        tts_settings: GPTSoVITSTTSSettings,
        base_dir: Path,
        character_registry: CharacterRegistry | None = None,
        current_character: CharacterProfile | None = None,
        proactive_care_settings: ProactiveCareSettings | None = None,
        mcp_settings: MCPRuntimeSettings | None = None,
        debug_log_settings: DebugLogSettings | None = None,
        memory_store: MemoryStore | None = None,
        tools_tab_contributions: list[ToolsTabContribution] | None = None,
        parent=None,  # type: ignore[no-untyped-def]
        portrait_scale_percent: int = PORTRAIT_SCALE_DEFAULT_PERCENT,
        subtitle_typing_interval_ms: int = SPEECH_TYPING_INTERVAL_MS,
        reply_segment_pause_ms: int = REPLY_SEGMENT_PAUSE_MS,
        stt_settings: STTSettings | None = None,
        pet_ui_settings: PetUISettings | None = None,
        screen_observation_settings: ScreenObservationSettings | None = None,
        reminder_settings: ReminderSettings | None = None,
        memory_curation_settings: MemoryCurationSettings | None = None,
        napcat_settings: NapCatSettings | None = None,
        on_open_napcat_console: Callable[[], None] | None = None,
        subtitle_language: str = SUBTITLE_LANGUAGE_ZH,
        free_access_enabled: bool = False,
    ) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        settings_service = AppSettingsService(base_dir=base_dir)
        self.tts_settings = tts_settings
        self.stt_settings = stt_settings or settings_service.load_stt_settings()
        self.pet_ui_settings = pet_ui_settings or settings_service.load_pet_ui_settings()
        self.screen_observation_settings = (
            screen_observation_settings or settings_service.load_screen_observation_settings()
        )
        self.reminder_settings = reminder_settings or settings_service.load_reminder_settings()
        self.memory_curation_settings = (
            memory_curation_settings or settings_service.load_memory_curation_settings()
        )
        self.napcat_settings = (
            napcat_settings or settings_service.load_napcat_settings()
        ).normalized()
        self._on_open_napcat_console = on_open_napcat_console
        self.initial_subtitle_language = (
            SUBTITLE_LANGUAGE_ZH
            if str(subtitle_language).strip().lower() == SUBTITLE_LANGUAGE_ZH
            else SUBTITLE_LANGUAGE_JA
        )
        self.initial_free_access_enabled = bool(free_access_enabled)
        self.character_registry = character_registry
        self.current_character = current_character
        self.portrait_scale_percent = normalize_portrait_scale_percent(portrait_scale_percent)
        (
            self.subtitle_typing_interval_ms,
            self.reply_segment_pause_ms,
        ) = normalize_subtitle_display_speed(
            subtitle_typing_interval_ms,
            reply_segment_pause_ms,
        )
        self.memory_store = memory_store
        self._all_memories: list[dict[str, object]] = []
        self._visible_memories: list[dict[str, object]] = []
        self._selected_memory_ids: set[str] = set()
        self._memory_editor_mode: Literal["new", "edit"] | None = None
        self._editing_memory_id: str | None = None
        self._active_memory_id: str | None = None
        self.result_api_settings: ApiSettings | None = None
        self.result_tts_settings: GPTSoVITSTTSSettings | None = None
        self.result_character_id: str | None = None
        self.result_portrait_scale_percent: int | None = None
        self.result_subtitle_typing_interval_ms: int | None = None
        self.result_reply_segment_pause_ms: int | None = None
        self.result_proactive_care_settings: ProactiveCareSettings | None = None
        self.result_mcp_settings: MCPRuntimeSettings | None = None
        self.result_debug_log_settings: DebugLogSettings | None = None
        self.result_stt_settings: STTSettings | None = None
        self.result_pet_ui_settings: PetUISettings | None = None
        self.result_screen_observation_settings: ScreenObservationSettings | None = None
        self.result_reminder_settings: ReminderSettings | None = None
        self.result_memory_curation_settings: MemoryCurationSettings | None = None
        self.result_napcat_settings: NapCatSettings | None = None
        self._api_test_thread: QThread | None = None
        self._api_test_worker: ApiConnectionTestWorker | None = None
        self._memory_list_thread: QThread | None = None
        self._memory_list_worker: MemoryListWorker | None = None
        self._character_export_thread: QThread | None = None
        self._character_export_worker: CharacterArchiveExportWorker | None = None
        self._memory_reload_pending = False
        self._syncing_memory_selection = False

        self.setWindowTitle("设置")
        self.resize(680, 620)

        tabs = QTabWidget(self)
        tabs.addTab(self._build_character_tab(character_registry, current_character), "角色")
        tabs.addTab(self._build_deskpet_tab(), "桌宠")
        tabs.addTab(self._build_api_tab(api_settings), "API")
        tabs.addTab(self._build_tts_tab(tts_settings), "TTS")
        tabs.addTab(self._build_stt_tab(self.stt_settings), "语音输入")
        tabs.addTab(
            self._build_privacy_tab(
                proactive_care_settings or ProactiveCareSettings(),
            ),
            "隐私",
        )
        tabs.addTab(
            self._build_mcp_tab(
                mcp_settings or MCPRuntimeSettings(),
                tools_tab_contributions or [],
            ),
            "工具",
        )
        tabs.addTab(self._build_platform_tab(self.napcat_settings), "平台")
        tabs.addTab(self._build_system_tab(debug_log_settings or DebugLogSettings()), "系统")
        if memory_store is not None:
            tabs.addTab(self._build_memory_tab(memory_store), "记忆")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box = buttons
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(tabs, 1)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self._apply_dialog_theme(self.pet_ui_settings.normalized().ui_theme)

    def _build_character_tab(
        self,
        character_registry: CharacterRegistry | None,
        current_character: CharacterProfile | None,
    ) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(12)

        self.character_combo = QComboBox(tab)
        self.character_empty_label = QLabel("尚未导入角色", tab)
        self._refresh_character_combo(
            current_character.id if current_character is not None else None
        )
        self.character_combo.currentIndexChanged.connect(self._load_selected_character_card)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)
        form_layout.addRow("状态", self.character_empty_label)
        form_layout.addRow("当前角色", self.character_combo)
        form_layout.addRow("立绘大小", self._build_portrait_scale_control(tab))
        form_layout.addRow("角色包", self._build_character_archive_controls(tab))
        layout.addLayout(form_layout)

        self.desktop_pet_rules_check = QCheckBox(
            "附加桌宠运行规则（边界、朗读习惯等通用约束，会拼在人设后面）",
            tab,
        )
        normalized_ui = self.pet_ui_settings.normalized()
        self.desktop_pet_rules_check.setChecked(normalized_ui.desktop_pet_rules_enabled)

        self.character_card_hint = QLabel(
            "人设会作为系统提示词影响回复风格。切换角色时会加载对应 card 文件，点保存后写入角色包。",
            tab,
        )
        self.character_card_hint.setWordWrap(True)
        self.character_card_edit = QTextEdit(tab)
        self.character_card_edit.setPlaceholderText("在此编写角色人设（Markdown 文本）……")
        self.character_card_edit.setMinimumHeight(240)
        layout.addWidget(self.desktop_pet_rules_check)
        layout.addWidget(self.character_card_hint)
        layout.addWidget(self.character_card_edit, 1)

        self._load_selected_character_card()
        self._sync_character_archive_controls()
        return tab

    def _build_deskpet_tab(self) -> QWidget:
        tab = QWidget(self)
        normalized_ui = self.pet_ui_settings.normalized()

        self.hover_only_ui_check = QCheckBox(
            "平时只显示 Live2D 立绘，鼠标悬停时再显示气泡与输入栏",
            tab,
        )
        self.hover_only_ui_check.setChecked(normalized_ui.hover_only_ui)

        self.ui_theme_combo = QComboBox(tab)
        for theme_id, label in UI_THEME_CHOICES:
            self.ui_theme_combo.addItem(label, theme_id)
        theme_index = self.ui_theme_combo.findData(normalized_ui.ui_theme)
        self.ui_theme_combo.setCurrentIndex(theme_index if theme_index >= 0 else 0)
        self.ui_theme_combo.currentIndexChanged.connect(self._on_ui_theme_changed)

        self.subtitle_language_combo = QComboBox(tab)
        self.subtitle_language_combo.addItem("中文", SUBTITLE_LANGUAGE_ZH)
        self.subtitle_language_combo.addItem("日本語", SUBTITLE_LANGUAGE_JA)
        language_index = self.subtitle_language_combo.findData(
            normalized_ui.subtitle_language
        )
        self.subtitle_language_combo.setCurrentIndex(
            language_index if language_index >= 0 else 0
        )

        self.strict_ja_zh_correspondence_check = QCheckBox(
            "完全对应（字幕与日语 TTS 语气、句意一致，禁止概括缩写）",
            tab,
        )
        self.strict_ja_zh_correspondence_check.setChecked(
            normalized_ui.strict_ja_zh_correspondence_enabled
        )
        self.strict_ja_zh_correspondence_check.setToolTip(
            "开启后，模型会被要求让 ja 与 zh 的语气、因果转折和完整句意成对出现；"
            "若检测到 zh 比 ja 明显更长或只写了一半意思，会自动请求模型修复一次。"
            "同时 TTS 会整段合成，减少切分丢句。"
        )

        normalized_reminders = self.reminder_settings.normalized()
        self.reminders_enabled_check = QCheckBox("启用到点提醒（本地 TTS + 表情播报）", tab)
        self.reminders_enabled_check.setChecked(normalized_reminders.enabled)
        self.reminder_interval_spin = QSpinBox(tab)
        self.reminder_interval_spin.setRange(
            REMINDER_CHECK_INTERVAL_MIN_SECONDS,
            REMINDER_CHECK_INTERVAL_MAX_SECONDS,
        )
        self.reminder_interval_spin.setSuffix(" 秒")
        self.reminder_interval_spin.setValue(normalized_reminders.check_interval_seconds)
        self.reminders_enabled_check.toggled.connect(self.reminder_interval_spin.setEnabled)
        self.reminder_interval_spin.setEnabled(normalized_reminders.enabled)

        self.music_plugin_enabled_check = QCheckBox(
            "立绘前显示透明歌词（跟随网易云等正在播放的歌曲）",
            tab,
        )
        self.music_plugin_enabled_check.setChecked(normalized_ui.music_plugin_enabled)

        self.lyric_sync_offset_spin = QDoubleSpinBox(tab)
        self.lyric_sync_offset_spin.setRange(-5.0, 5.0)
        self.lyric_sync_offset_spin.setSingleStep(0.1)
        self.lyric_sync_offset_spin.setDecimals(1)
        self.lyric_sync_offset_spin.setSuffix(" 秒")
        self.lyric_sync_offset_spin.setValue(normalized_ui.lyric_sync_offset_seconds)
        self.lyric_sync_offset_spin.setToolTip(
            "歌词相对播放进度的提前量。偏慢可加大（如 2.0），偏快可减小或为负。"
        )

        self.music_sing_along_enabled_check = QCheckBox(
            "音乐播放时安安跟唱（Live2D 口型与表情，不播放语音）",
            tab,
        )
        self.music_sing_along_enabled_check.setChecked(normalized_ui.music_sing_along_enabled)

        self.deskpet_hint = QLabel(
            "悬停 UI 仅对 Live2D 角色生效；「锁定界面」后仅立绘区可点，窗口空白处穿透。\n"
            "歌词从 LRCLIB 拉取；网易云 SMTC 无进度，靠本地计时，可用「歌词提前量」微调同步。",
            tab,
        )
        self.deskpet_hint.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("", self.hover_only_ui_check)
        form_layout.addRow("面板宽度", self._build_panel_width_control(tab))
        form_layout.addRow("界面主题", self.ui_theme_combo)
        form_layout.addRow("字幕语言", self.subtitle_language_combo)
        form_layout.addRow("", self.strict_ja_zh_correspondence_check)
        form_layout.addRow("", self.reminders_enabled_check)
        form_layout.addRow("提醒检查间隔", self.reminder_interval_spin)
        form_layout.addRow("", self.music_plugin_enabled_check)
        form_layout.addRow("歌词提前量", self.lyric_sync_offset_spin)
        form_layout.addRow("", self.music_sing_along_enabled_check)
        form_layout.addRow(self.deskpet_hint)
        tab.setLayout(form_layout)
        return tab

    def _on_ui_theme_changed(self) -> None:
        if not hasattr(self, "ui_theme_combo"):
            return
        theme_id = str(self.ui_theme_combo.currentData() or "")
        self._apply_dialog_theme(theme_id)

    def _apply_dialog_theme(self, theme_id: str) -> None:
        self.setStyleSheet(build_settings_dialog_stylesheet(theme_id))
        palette = ui_theme_palette(theme_id)
        if hasattr(self, "deskpet_hint"):
            self.deskpet_hint.setStyleSheet(f"color: {palette.hint_text};")
        if hasattr(self, "restart_hint"):
            self.restart_hint.setStyleSheet(f"color: {palette.hint_text};")
        if hasattr(self, "memory_status_label"):
            self.memory_status_label.setStyleSheet(f"color: {palette.hint_text};")
        if hasattr(self, "memory_selection_label"):
            self.memory_selection_label.setStyleSheet(f"color: {palette.tab_text};")
        if hasattr(self, "memory_preview_label"):
            self.memory_preview_label.setStyleSheet(f"color: {palette.system_text};")
        if hasattr(self, "character_card_hint"):
            self.character_card_hint.setStyleSheet(f"color: {palette.hint_text};")

    def _build_character_archive_controls(self, parent: QWidget) -> QWidget:
        container = QWidget(parent)
        self.character_import_button = QPushButton("导入 .char", container)
        self.character_export_button = QPushButton("导出当前角色", container)
        self.character_import_button.clicked.connect(self._import_character_archive)
        self.character_export_button.clicked.connect(self._export_current_character_archive)
        self._sync_character_archive_controls()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.character_import_button)
        layout.addWidget(self.character_export_button)
        layout.addStretch(1)
        container.setLayout(layout)
        return container

    def _build_panel_width_control(self, parent: QWidget) -> QWidget:
        container = QWidget(parent)
        normalized_ui = self.pet_ui_settings.normalized()
        panel_width_percent = normalized_ui.panel_width_percent

        self.panel_width_slider = QSlider(Qt.Orientation.Horizontal, container)
        self.panel_width_slider.setRange(
            PANEL_WIDTH_PERCENT_MIN,
            PANEL_WIDTH_PERCENT_MAX,
        )
        self.panel_width_slider.setSingleStep(5)
        self.panel_width_slider.setPageStep(25)
        self.panel_width_slider.setTickInterval(50)
        self.panel_width_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.panel_width_slider.setValue(panel_width_percent)

        self.panel_width_spin = QSpinBox(container)
        self.panel_width_spin.setRange(
            PANEL_WIDTH_PERCENT_MIN,
            PANEL_WIDTH_PERCENT_MAX,
        )
        self.panel_width_spin.setSingleStep(5)
        self.panel_width_spin.setSuffix("%")
        self.panel_width_spin.setValue(panel_width_percent)
        self.panel_width_spin.setToolTip(
            "调整气泡与输入栏整体宽度（20%–500%）。100% 为默认宽度。"
        )

        self.panel_width_slider.valueChanged.connect(self.panel_width_spin.setValue)
        self.panel_width_spin.valueChanged.connect(self.panel_width_slider.setValue)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.panel_width_slider, 1)
        layout.addWidget(self.panel_width_spin)
        container.setLayout(layout)
        return container

    def _build_portrait_scale_control(self, parent: QWidget) -> QWidget:
        container = QWidget(parent)
        self.portrait_scale_slider = QSlider(Qt.Orientation.Horizontal, container)
        self.portrait_scale_slider.setRange(
            PORTRAIT_SCALE_MIN_PERCENT,
            PORTRAIT_SCALE_MAX_PERCENT,
        )
        self.portrait_scale_slider.setSingleStep(5)
        self.portrait_scale_slider.setPageStep(25)
        self.portrait_scale_slider.setTickInterval(50)
        self.portrait_scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.portrait_scale_slider.setValue(self.portrait_scale_percent)

        self.portrait_scale_spin = QSpinBox(container)
        self.portrait_scale_spin.setRange(
            PORTRAIT_SCALE_MIN_PERCENT,
            PORTRAIT_SCALE_MAX_PERCENT,
        )
        self.portrait_scale_spin.setSingleStep(5)
        self.portrait_scale_spin.setSuffix("%")
        self.portrait_scale_spin.setValue(self.portrait_scale_percent)
        self.portrait_scale_spin.setToolTip(
            "调整立绘显示大小（20%–500%）。100% 为原始尺寸。"
        )

        self.portrait_scale_slider.valueChanged.connect(self.portrait_scale_spin.setValue)
        self.portrait_scale_spin.valueChanged.connect(self.portrait_scale_slider.setValue)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.portrait_scale_slider, 1)
        layout.addWidget(self.portrait_scale_spin)
        container.setLayout(layout)
        return container

    def _build_api_tab(self, settings: ApiSettings) -> QWidget:
        tab = QWidget(self)
        self.base_url_edit = QLineEdit(settings.base_url, tab)
        self.base_url_edit.setPlaceholderText("https://api.openai.com/v1")

        self.api_key_edit = QLineEdit(settings.api_key, tab)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("请输入 API Key")

        self.model_edit = QLineEdit(settings.model, tab)
        self.model_edit.setPlaceholderText("gpt-4.1-mini")

        self.api_timeout_spin = QSpinBox(tab)
        self.api_timeout_spin.setRange(1, 600)
        self.api_timeout_spin.setSuffix(" 秒")
        self.api_timeout_spin.setValue(settings.timeout_seconds)

        self.api_test_button = QPushButton("测试 API", tab)
        self.api_test_button.clicked.connect(self._test_api_settings)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("Base URL", self.base_url_edit)
        form_layout.addRow("API Key", self.api_key_edit)
        form_layout.addRow("模型", self.model_edit)
        form_layout.addRow("超时", self.api_timeout_spin)
        form_layout.addRow("", self.api_test_button)
        tab.setLayout(form_layout)
        return tab

    def _build_tts_tab(self, settings: GPTSoVITSTTSSettings) -> QWidget:
        tab = QWidget(self)
        self.tts_enabled_check = QCheckBox("启用 TTS 语音", tab)
        self.tts_enabled_check.setChecked(settings.enabled)

        self.tts_provider_combo = QComboBox(tab)
        self.tts_provider_combo.addItem("GPT-SoVITS（GPU）", TTS_PROVIDER_GPT_SOVITS)
        provider_index = self.tts_provider_combo.findData(settings.provider)
        self.tts_provider_combo.setCurrentIndex(provider_index if provider_index >= 0 else 0)

        self.tts_api_url_edit = QLineEdit(settings.api_url, tab)
        self.tts_api_url_edit.setPlaceholderText(_default_tts_api_url(settings.provider))
        self.tts_work_dir_edit = QLineEdit(str(settings.work_dir or ""), tab)
        self.tts_work_dir_edit.setPlaceholderText("data/tts_bundles/installed/gpt_sovits_nvidia50/GPT-SoVITS-v2pro-20250604-nvidia50")
        self.tts_bundle_download_button = QPushButton("一键下载 TTS 整合包", tab)
        self.tts_bundle_download_button.clicked.connect(self._download_gpt_sovits_bundle)
        self.tts_provider_combo.currentIndexChanged.connect(lambda _index: self._sync_tts_provider_controls())

        self.ref_lang_edit = QLineEdit(settings.ref_lang, tab)
        self.text_lang_edit = QLineEdit(settings.text_lang, tab)

        self.tts_timeout_spin = QSpinBox(tab)
        self.tts_timeout_spin.setRange(1, 600)
        self.tts_timeout_spin.setSuffix(" 秒")
        self.tts_timeout_spin.setValue(settings.timeout_seconds)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("", self.tts_enabled_check)
        form_layout.addRow("TTS 提供器", self.tts_provider_combo)
        form_layout.addRow("API URL", self.tts_api_url_edit)
        form_layout.addRow("TTS 工作目录", self.tts_work_dir_edit)
        form_layout.addRow("", self.tts_bundle_download_button)
        form_layout.addRow("参考语言", self.ref_lang_edit)
        form_layout.addRow("文本语言", self.text_lang_edit)
        form_layout.addRow("超时", self.tts_timeout_spin)
        tab.setLayout(form_layout)
        self._sync_tts_provider_controls()
        return tab

    def _build_stt_tab(self, settings: STTSettings) -> QWidget:
        tab = QWidget(self)
        try:
            audio_io.configure_audio_paths(settings, self.base_dir)
        except OSError:
            pass

        self.stt_enabled_check = QCheckBox("启用语音输入（Whisper）", tab)
        self.stt_enabled_check.setChecked(settings.enabled)

        self.stt_input_device_combo = QComboBox(tab)
        self.stt_refresh_devices_button = QPushButton("刷新设备列表", tab)
        self.stt_refresh_devices_button.clicked.connect(self._refresh_stt_input_devices)

        self.stt_model_edit = QLineEdit(settings.model_name, tab)
        self.stt_model_edit.setPlaceholderText(DEFAULT_WHISPER_MODEL_NAME)

        self.stt_language_combo = QComboBox(tab)
        for label, code in (
            ("中文", "zh"),
            ("日本語", "ja"),
            ("English", "en"),
        ):
            self.stt_language_combo.addItem(label, code)
        language_index = self.stt_language_combo.findData(settings.language)
        self.stt_language_combo.setCurrentIndex(language_index if language_index >= 0 else 0)

        stt_hint = QLabel(
            "选择录音用的麦克风；「系统默认」使用 Windows 当前默认输入设备。\n"
            "若提示读不到声音：在 Windows 声音设置里调高该麦克风的输入音量；"
            "使用 Voicemeeter 时请确认路由到所选设备；实体麦优先选名称含 Microphone 的项。\n"
            "「语音」为点击或长按录音，松手/再次点击后识别为文字。"
        )
        stt_hint.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("", self.stt_enabled_check)
        form_layout.addRow("麦克风", self.stt_input_device_combo)
        form_layout.addRow("", self.stt_refresh_devices_button)
        form_layout.addRow("Whisper 模型", self.stt_model_edit)
        form_layout.addRow("识别语言", self.stt_language_combo)
        form_layout.addRow(stt_hint)
        tab.setLayout(form_layout)
        self._refresh_stt_input_devices(select_index=settings.input_device_index)
        return tab

    def _refresh_stt_input_devices(self, select_index: int | None = None) -> None:
        if not hasattr(self, "stt_input_device_combo"):
            return
        if select_index is None:
            select_index = self.stt_input_device_combo.currentData()
        try:
            devices = audio_io.list_input_devices()
        except audio_io.AudioIOError as exc:
            QMessageBox.warning(self, "音频设备", str(exc))
            return

        combo = self.stt_input_device_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("系统默认", None)
        selected_row = 0
        for row, device in enumerate(devices, start=1):
            combo.addItem(audio_io.device_combo_label(device), device["index"])
            if select_index is not None and device["index"] == select_index:
                selected_row = row
        combo.setCurrentIndex(selected_row)
        combo.blockSignals(False)

    def _validated_stt_settings(self) -> STTSettings | None:
        if not hasattr(self, "stt_enabled_check"):
            return self.stt_settings
        model_name = self.stt_model_edit.text().strip() or DEFAULT_WHISPER_MODEL_NAME
        language = str(self.stt_language_combo.currentData() or DEFAULT_WHISPER_LANGUAGE)
        device_index = self.stt_input_device_combo.currentData()
        input_device_index: int | None = None
        if device_index is not None:
            try:
                input_device_index = int(device_index)
            except (TypeError, ValueError):
                QMessageBox.warning(self, "配置无效", "无效的麦克风设备编号。")
                return None
        return STTSettings(
            enabled=self.stt_enabled_check.isChecked(),
            model_name=model_name,
            language=language,
            input_device_index=input_device_index,
        )

    def _build_privacy_tab(
        self,
        proactive_care_settings: ProactiveCareSettings,
    ) -> QWidget:
        tab = QWidget(self)
        normalized_screen = self.screen_observation_settings.normalized()
        self.screen_observation_enabled_check = QCheckBox(
            "允许发送屏幕截图给模型（聊天栏截图按钮）",
            tab,
        )
        self.screen_observation_enabled_check.setChecked(normalized_screen.enabled)
        normalized_proactive = proactive_care_settings.normalized()
        self.proactive_topic_enabled_check = QCheckBox(
            "空闲时主动找话题聊天（无需截图）",
            tab,
        )
        self.proactive_topic_enabled_check.setChecked(normalized_proactive.enabled)
        self.autonomous_screen_observation_check = QCheckBox(
            "主动搭话时附带后台屏幕截图（需开启上方截图权限）",
            tab,
        )
        self.autonomous_screen_observation_check.setChecked(
            normalized_proactive.screen_context_enabled
        )
        self.screen_observation_enabled_check.toggled.connect(
            self._sync_screen_observation_controls
        )
        self._sync_screen_observation_controls(
            self.screen_observation_enabled_check.isChecked()
        )

        self.proactive_check_interval_spin = QSpinBox(tab)
        self.proactive_check_interval_spin.setRange(
            PROACTIVE_MIN_CHECK_INTERVAL_MINUTES,
            PROACTIVE_MAX_CHECK_INTERVAL_MINUTES,
        )
        self.proactive_check_interval_spin.setSuffix(" 分钟")
        self.proactive_check_interval_spin.setValue(
            proactive_care_settings.normalized().check_interval_minutes
        )

        self.proactive_cooldown_spin = QSpinBox(tab)
        self.proactive_cooldown_spin.setRange(
            PROACTIVE_MIN_COOLDOWN_MINUTES,
            PROACTIVE_MAX_COOLDOWN_MINUTES,
        )
        self.proactive_cooldown_spin.setSuffix(" 分钟")
        self.proactive_cooldown_spin.setValue(
            proactive_care_settings.normalized().cooldown_minutes
        )

        self.proactive_batch_limit_spin = QSpinBox(tab)
        self.proactive_batch_limit_spin.setRange(
            PROACTIVE_MIN_SCREEN_CONTEXT_BATCH_LIMIT,
            PROACTIVE_MAX_SCREEN_CONTEXT_BATCH_LIMIT,
        )
        self.proactive_batch_limit_spin.setSuffix(" 张")
        self.proactive_batch_limit_spin.setValue(
            proactive_care_settings.normalized().screen_context_batch_limit
        )
        self.proactive_topic_enabled_check.toggled.connect(
            self._sync_proactive_interval_controls
        )
        self.autonomous_screen_observation_check.toggled.connect(
            self._sync_proactive_interval_controls
        )
        self._sync_proactive_interval_controls(
            self.proactive_topic_enabled_check.isChecked()
            or self.autonomous_screen_observation_check.isChecked()
        )

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("", self.screen_observation_enabled_check)
        form_layout.addRow("", self.proactive_topic_enabled_check)
        form_layout.addRow("", self.autonomous_screen_observation_check)
        form_layout.addRow("主动检查间隔", self.proactive_check_interval_spin)
        form_layout.addRow("主动打扰冷却", self.proactive_cooldown_spin)
        self.proactive_countdown_hint_label = QLabel(
            "开启后，托盘图标悬停与输入框会显示下次主动搭话的倒计时。",
            tab,
        )
        self.proactive_countdown_hint_label.setWordWrap(True)
        form_layout.addRow("", self.proactive_countdown_hint_label)
        form_layout.addRow("单次最多发送截图", self.proactive_batch_limit_spin)
        tab.setLayout(form_layout)
        return tab

    def _build_platform_tab(self, settings: NapCatSettings) -> QWidget:
        tab = QWidget(self)
        normalized = settings.normalized()

        self.napcat_enabled_check = QCheckBox(
            "启用 NapCat / QQ 接入（反向 WebSocket）",
            tab,
        )
        self.napcat_enabled_check.setChecked(normalized.enabled)

        self.napcat_host_edit = QLineEdit(normalized.host, tab)
        self.napcat_host_edit.setPlaceholderText("0.0.0.0（监听本机所有网卡，同 AstrBot 反向 WS）")
        self.napcat_connect_host_combo = QComboBox(tab)
        self.napcat_connect_host_combo.setEditable(True)
        for host in suggested_connect_hosts():
            self.napcat_connect_host_combo.addItem(host)
        connect_index = self.napcat_connect_host_combo.findText(normalized.connect_host)
        if connect_index >= 0:
            self.napcat_connect_host_combo.setCurrentIndex(connect_index)
        else:
            self.napcat_connect_host_combo.setEditText(normalized.resolve_connect_host())
        self.napcat_port_spin = QSpinBox(tab)
        self.napcat_port_spin.setRange(1, 65535)
        self.napcat_port_spin.setValue(normalized.port)
        self.napcat_path_edit = QLineEdit(normalized.path, tab)
        self.napcat_token_edit = QLineEdit(normalized.token, tab)
        self.napcat_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.napcat_token_edit.setPlaceholderText("可选，与 NapCat WebSocket 客户端 token 一致")

        self.napcat_allow_private_check = QCheckBox("允许私聊", tab)
        self.napcat_allow_private_check.setChecked(normalized.allow_private)
        self.napcat_allow_group_check = QCheckBox("允许群聊（实验性）", tab)
        self.napcat_allow_group_check.setChecked(normalized.allow_group)

        self.napcat_history_limit_spin = QSpinBox(tab)
        self.napcat_history_limit_spin.setRange(2, 100)
        self.napcat_history_limit_spin.setValue(normalized.history_limit)
        self.napcat_history_limit_spin.setSuffix(" 条")

        self.napcat_busy_reply_edit = QLineEdit(normalized.busy_reply_text, tab)

        self.napcat_reply_mode_combo = QComboBox(tab)
        self.napcat_reply_mode_combo.addItem("文字 + 语音", NAPCAT_REPLY_BOTH)
        self.napcat_reply_mode_combo.addItem("仅文字", NAPCAT_REPLY_TEXT_ONLY)
        self.napcat_reply_mode_combo.addItem("仅语音", NAPCAT_REPLY_VOICE_ONLY)
        reply_mode_index = self.napcat_reply_mode_combo.findData(normalized.reply_mode)
        self.napcat_reply_mode_combo.setCurrentIndex(
            reply_mode_index if reply_mode_index >= 0 else 0
        )

        self.napcat_url_hint_label = QLabel(self._napcat_websocket_url_hint_text(), tab)
        self.napcat_url_hint_label.setWordWrap(True)

        napcat_setup_hint = QLabel(
            "桌宠相当于 AstrBot 的「反向 WebSocket 服务端」：监听填 0.0.0.0，"
            "NapCat 客户端 URL 填下方具体 IP 地址。先启动桌宠，再启动 NapCat。",
            tab,
        )
        napcat_setup_hint.setWordWrap(True)

        for widget in (
            self.napcat_host_edit,
            self.napcat_port_spin,
            self.napcat_path_edit,
        ):
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._refresh_napcat_url_hint)
            else:
                widget.valueChanged.connect(self._refresh_napcat_url_hint)
        self.napcat_connect_host_combo.currentTextChanged.connect(self._refresh_napcat_url_hint)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("", self.napcat_enabled_check)
        form_layout.addRow("", napcat_setup_hint)
        form_layout.addRow("反向 WS 监听", self.napcat_host_edit)
        form_layout.addRow("监听端口", self.napcat_port_spin)
        form_layout.addRow("WebSocket 路径", self.napcat_path_edit)
        form_layout.addRow("NapCat 填写 IP", self.napcat_connect_host_combo)
        form_layout.addRow("NapCat 连接地址", self.napcat_url_hint_label)
        form_layout.addRow("Token", self.napcat_token_edit)
        form_layout.addRow("", self.napcat_allow_private_check)
        form_layout.addRow("", self.napcat_allow_group_check)
        form_layout.addRow("每会话历史条数", self.napcat_history_limit_spin)
        form_layout.addRow("QQ 回复内容", self.napcat_reply_mode_combo)
        form_layout.addRow("桌宠忙碌时回复", self.napcat_busy_reply_edit)
        if self._on_open_napcat_console is not None:
            self.napcat_console_button = QPushButton("打开 QQ 控制台", tab)
            self.napcat_console_button.clicked.connect(self._on_open_napcat_console)
            form_layout.addRow("", self.napcat_console_button)
        tab.setLayout(form_layout)
        return tab

    def _current_napcat_form_settings(self) -> NapCatSettings:
        host_edit = getattr(self, "napcat_host_edit", None)
        port_spin = getattr(self, "napcat_port_spin", None)
        path_edit = getattr(self, "napcat_path_edit", None)
        connect_combo = getattr(self, "napcat_connect_host_combo", None)
        if host_edit is None or port_spin is None or path_edit is None:
            return self.napcat_settings.normalized()
        return NapCatSettings(
            host=host_edit.text() or DEFAULT_NAPCAT_BIND_HOST,
            port=port_spin.value() or DEFAULT_NAPCAT_PORT,
            path=path_edit.text() or DEFAULT_NAPCAT_PATH,
            connect_host=(
                connect_combo.currentText().strip() if connect_combo is not None else ""
            ),
        ).normalized()

    def _napcat_websocket_url_hint_text(self) -> str:
        lines = self._current_napcat_form_settings().websocket_url_hint_lines()
        if len(lines) == 1:
            return lines[0]
        return f"{lines[0]}\n同机调试：{lines[1]}"

    def _refresh_napcat_url_hint(self) -> None:
        label = getattr(self, "napcat_url_hint_label", None)
        if label is not None:
            label.setText(self._napcat_websocket_url_hint_text())

    def _build_mcp_tab(
        self,
        settings: MCPRuntimeSettings,
        tools_tab_contributions: list[ToolsTabContribution],
    ) -> QWidget:
        tab = QWidget(self)
        self.windows_mcp_enabled_check = QCheckBox("启用 Windows MCP 桌面控制（高级）", tab)
        self.windows_mcp_enabled_check.setChecked(settings.windows_enabled)
        self.playwright_mcp_enabled_check = QCheckBox(
            "启用 Playwright 可见浏览器 MCP（网页自动化，需 Node）",
            tab,
        )
        self.playwright_mcp_enabled_check.setChecked(settings.playwright_enabled)

        restart_hint = QLabel(
            "保存后需要重启 Mutsuki 才会加载或卸载 MCP 工具（Windows / Playwright）。",
            tab,
        )
        restart_hint.setWordWrap(True)
        self.restart_hint = restart_hint

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("", self.windows_mcp_enabled_check)
        form_layout.addRow("", self.playwright_mcp_enabled_check)
        form_layout.addRow("生效方式", restart_hint)
        for contribution in sorted(tools_tab_contributions, key=lambda item: item.order):
            try:
                widget = contribution.build(None)
            except Exception as exc:
                widget = QLabel(f"{contribution.title} 设置加载失败：{exc}", tab)
                widget.setWordWrap(True)
            form_layout.addRow(contribution.title, widget)
        tab.setLayout(form_layout)
        return tab

    def _build_system_tab(self, debug_settings: DebugLogSettings) -> QWidget:
        tab = QWidget(self)
        self.debug_log_enabled_check = QCheckBox("输出终端调试日志", tab)
        self.debug_log_enabled_check.setChecked(debug_settings.enabled)
        self.debug_body_enabled_check = QCheckBox("输出完整请求/回复正文", tab)
        self.debug_body_enabled_check.setChecked(debug_settings.body_enabled)
        self.debug_log_enabled_check.toggled.connect(self.debug_body_enabled_check.setEnabled)
        self.debug_body_enabled_check.setEnabled(self.debug_log_enabled_check.isChecked())
        self.debug_file_enabled_check = QCheckBox("输出文件运行日志", tab)
        self.debug_file_enabled_check.setChecked(debug_settings.file_enabled)

        self.free_access_enabled_check = QCheckBox(
            "完整工具访问权限（跳过部分高风险工具确认）",
            tab,
        )
        self.free_access_enabled_check.setChecked(self.initial_free_access_enabled)

        normalized_memory = self.memory_curation_settings
        self.memory_curation_enabled_check = QCheckBox("自动整理长期记忆", tab)
        self.memory_curation_enabled_check.setChecked(normalized_memory.enabled)
        self.memory_curation_trigger_spin = QSpinBox(tab)
        self.memory_curation_trigger_spin.setRange(2, 50)
        self.memory_curation_trigger_spin.setSuffix(" 轮对话")
        self.memory_curation_trigger_spin.setValue(normalized_memory.trigger_turns)
        self.memory_curation_backfill_spin = QSpinBox(tab)
        self.memory_curation_backfill_spin.setRange(20, 500)
        self.memory_curation_backfill_spin.setSuffix(" 条")
        self.memory_curation_backfill_spin.setValue(normalized_memory.backfill_limit)
        self.memory_curation_enabled_check.toggled.connect(
            self._sync_memory_curation_controls
        )
        self._sync_memory_curation_controls(
            self.memory_curation_enabled_check.isChecked()
        )

        self.subtitle_typing_interval_spin = QSpinBox(tab)
        self.subtitle_typing_interval_spin.setRange(
            SUBTITLE_TYPING_INTERVAL_MIN_MS,
            SUBTITLE_TYPING_INTERVAL_MAX_MS,
        )
        self.subtitle_typing_interval_spin.setSuffix(" 毫秒")
        self.subtitle_typing_interval_spin.setValue(self.subtitle_typing_interval_ms)

        self.reply_segment_pause_spin = QSpinBox(tab)
        self.reply_segment_pause_spin.setRange(
            REPLY_SEGMENT_PAUSE_MIN_MS,
            REPLY_SEGMENT_PAUSE_MAX_MS,
        )
        self.reply_segment_pause_spin.setSuffix(" 毫秒")
        self.reply_segment_pause_spin.setValue(self.reply_segment_pause_ms)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(16, 18, 16, 16)
        form_layout.setSpacing(12)
        form_layout.addRow("", self.debug_log_enabled_check)
        form_layout.addRow("", self.debug_body_enabled_check)
        form_layout.addRow("", self.debug_file_enabled_check)
        form_layout.addRow("", self.free_access_enabled_check)
        form_layout.addRow("", self.memory_curation_enabled_check)
        form_layout.addRow("自动整理触发", self.memory_curation_trigger_spin)
        form_layout.addRow("历史回填上限", self.memory_curation_backfill_spin)
        form_layout.addRow("字幕逐字间隔", self.subtitle_typing_interval_spin)
        form_layout.addRow("回复分段停顿", self.reply_segment_pause_spin)

        restart_button = QPushButton("重启 Mutsuki", tab)
        restart_button.clicked.connect(self._restart_application_from_settings)
        restart_hint = QLabel("修改 API/语音/MCP 等配置后，可一键重启使全部设置生效。", tab)
        restart_hint.setWordWrap(True)
        form_layout.addRow(restart_button)
        form_layout.addRow(restart_hint)
        tab.setLayout(form_layout)
        return tab

    @Slot()
    def _restart_application_from_settings(self) -> None:
        answer = QMessageBox.question(
            self,
            "重启 Mutsuki",
            "将重新启动 Mutsuki。若刚改过设置，请先点「保存」再重启。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        from app.ui.restart import request_app_restart

        request_app_restart(parent=self, base_dir=self.base_dir)

    @Slot(bool)
    def _sync_screen_observation_controls(self, enabled: bool) -> None:
        self.autonomous_screen_observation_check.setEnabled(enabled)
        if not enabled:
            self.autonomous_screen_observation_check.setChecked(False)

    @Slot(bool)
    def _sync_memory_curation_controls(self, enabled: bool) -> None:
        self.memory_curation_trigger_spin.setEnabled(enabled)
        self.memory_curation_backfill_spin.setEnabled(enabled)

    @Slot(bool)
    def _sync_proactive_interval_controls(self, enabled: bool) -> None:
        topic_enabled = self.proactive_topic_enabled_check.isChecked()
        screen_enabled = (
            self.screen_observation_enabled_check.isChecked()
            and self.autonomous_screen_observation_check.isChecked()
        )
        controls_enabled = topic_enabled or screen_enabled
        self.proactive_check_interval_spin.setEnabled(controls_enabled)
        self.proactive_cooldown_spin.setEnabled(controls_enabled)
        self.proactive_batch_limit_spin.setEnabled(screen_enabled)

    def _build_memory_tab(self, memory_store: MemoryStore) -> QWidget:
        tab = QWidget(self)
        _ = memory_store

        self.memory_search_edit = QLineEdit(tab)
        self.memory_search_edit.setPlaceholderText("搜索记忆内容或 ID")
        self.memory_search_edit.textChanged.connect(self._refresh_memory_table)

        self.memory_refresh_button = QPushButton("刷新", tab)
        self.memory_refresh_button.clicked.connect(self._load_memory_entries)
        self.memory_status_label = QLabel("正在加载长期记忆...", tab)

        self.memory_table = QTableWidget(0, 4, tab)
        self.memory_table.setHorizontalHeaderLabels(["", "内容", "更新时间", "ID"])
        self.memory_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.memory_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.memory_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.memory_table.verticalHeader().setVisible(False)
        self.memory_table.setAlternatingRowColors(True)
        self.memory_table.setWordWrap(True)
        self.memory_table.itemClicked.connect(self._handle_memory_item_clicked)
        header = self.memory_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.memory_table.setColumnWidth(0, 56)
        self.memory_table.setColumnWidth(3, 82)
        self.memory_select_all_check = QCheckBox(header)
        self.memory_select_all_check.setToolTip("全选当前结果")
        self.memory_select_all_check.stateChanged.connect(
            self._handle_memory_select_all_check_changed
        )
        header.sectionResized.connect(
            lambda *_args: self._sync_memory_select_all_check_geometry()
        )
        self._sync_memory_select_all_check_geometry()

        self.memory_selection_label = QLabel("已选择 0 条", tab)
        self.memory_delete_button = QPushButton("删除选中", tab)
        self.memory_delete_button.setEnabled(False)
        self.memory_delete_button.clicked.connect(self._delete_memory_entry)
        self.memory_clear_selection_button = QPushButton("清空选择", tab)
        self.memory_clear_selection_button.setEnabled(False)
        self.memory_clear_selection_button.clicked.connect(self._clear_memory_selection)
        self.memory_preview_label = QLabel("未选择记忆", tab)
        self.memory_preview_label.setWordWrap(True)

        self.memory_new_button = QPushButton("新增记忆", tab)
        self.memory_new_button.setCheckable(True)
        self.memory_new_button.toggled.connect(self._toggle_memory_new_editor)
        self.memory_content_edit = QTextEdit(tab)
        self.memory_content_edit.setPlaceholderText("新增长期记忆内容")
        self.memory_content_edit.setFixedHeight(84)
        self.memory_save_button = QPushButton("保存", tab)
        self.memory_save_button.clicked.connect(self._save_memory_entry)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.memory_search_edit, 1)
        filter_layout.addWidget(self.memory_refresh_button)

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.memory_status_label, 1)
        status_layout.addWidget(self.memory_new_button)

        selection_layout = QHBoxLayout()
        selection_layout.addWidget(self.memory_selection_label)
        selection_layout.addStretch(1)
        selection_layout.addWidget(self.memory_clear_selection_button)
        selection_layout.addWidget(self.memory_delete_button)

        self.memory_editor_container = QWidget(tab)
        editor_layout = QFormLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)
        editor_layout.addRow("内容", self.memory_content_edit)
        editor_layout.addRow("", self.memory_save_button)
        self.memory_editor_container.setLayout(editor_layout)
        self.memory_editor_container.setVisible(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(filter_layout)
        layout.addLayout(status_layout)
        layout.addWidget(self.memory_table, 1)
        layout.addLayout(selection_layout)
        layout.addWidget(self.memory_editor_container)
        tab.setLayout(layout)

        self._show_memory_placeholder("正在加载长期记忆...")
        self._clear_memory_editor()
        self._load_memory_entries()
        return tab

    def _load_memory_entries(self) -> None:
        if self.memory_store is None or not hasattr(self, "memory_table"):
            return
        if self._memory_list_thread is not None:
            self._memory_reload_pending = True
            return

        self.memory_status_label.setText("正在加载长期记忆...")
        self.memory_refresh_button.setEnabled(False)
        self._show_memory_placeholder("正在加载长期记忆...")

        thread = QThread(self)
        worker = MemoryListWorker(self.memory_store, limit=200)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._handle_memory_load_success)
        worker.failed.connect(self._handle_memory_load_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(self._reset_memory_list_worker)  # 在 worker 结束时立即重置，避免依赖 thread.finished 的多轮事件链
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._memory_list_thread = thread
        self._memory_list_worker = worker
        thread.start()

    @Slot(list)
    def _handle_memory_load_success(self, memories: list[dict[str, object]]) -> None:
        self._all_memories = list(memories)
        all_ids = {str(memory.get("id", "")) for memory in self._all_memories}
        self._selected_memory_ids &= all_ids
        if self._editing_memory_id and self._editing_memory_id not in all_ids:
            self._memory_editor_mode = None
            self._editing_memory_id = None
            self._active_memory_id = None
            self._clear_memory_editor()
            self.memory_editor_container.setVisible(False)
        self.memory_status_label.setText(f"已加载 {len(self._all_memories)} 条记忆")
        self._refresh_memory_table()

    @Slot(str)
    def _handle_memory_load_failed(self, message: str) -> None:
        self._all_memories = []
        self.memory_status_label.setText(f"读取失败：{message}")
        self._show_memory_placeholder("记忆读取失败，请稍后重试。")
        QMessageBox.warning(self, "读取失败", message)

    @Slot()
    def _reset_memory_list_worker(self) -> None:
        self.memory_refresh_button.setEnabled(True)
        self._memory_list_thread = None
        self._memory_list_worker = None
        if self._memory_reload_pending:
            self._memory_reload_pending = False
            self._load_memory_entries()

    def _refresh_memory_table(self) -> None:
        if not hasattr(self, "memory_table"):
            return
        keyword = self.memory_search_edit.text().strip()
        keyword_lower = keyword.lower()
        if keyword_lower:
            self._visible_memories = [
                memory
                for memory in self._all_memories
                if keyword_lower in str(memory.get("content", "")).lower()
                or keyword_lower in str(memory.get("id", "")).lower()
            ]
        else:
            self._visible_memories = list(self._all_memories)
        if not self._visible_memories:
            self._show_memory_placeholder("没有匹配的记忆。" if keyword else "暂无长期记忆。")
            return

        self._syncing_memory_selection = True
        self.memory_table.blockSignals(True)
        self.memory_table.clearContents()
        self.memory_table.setRowCount(len(self._visible_memories))
        for row, memory in enumerate(self._visible_memories):
            memory_id = str(memory.get("id", ""))
            content = str(memory.get("content", ""))
            updated_at = str(memory.get("updated_at") or memory.get("created_at") or "")
            is_checked = memory_id in self._selected_memory_ids

            select_item = QTableWidgetItem("")
            select_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            select_item.setData(Qt.ItemDataRole.UserRole, memory_id)

            values = [
                content,
                _format_memory_time(updated_at),
                _compact_memory_id(memory_id),
            ]
            self.memory_table.setItem(row, 0, select_item)
            self._set_memory_checkbox_widget(row, memory_id, is_checked)
            for column, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if column == 1:
                    item.setToolTip(content)
                elif column == 3:
                    item.setToolTip(memory_id)
                    item.setData(Qt.ItemDataRole.UserRole, memory_id)
                self.memory_table.setItem(row, column, item)
            self._apply_memory_row_checked_style(row, is_checked)
        self.memory_table.blockSignals(False)
        self._syncing_memory_selection = False
        self._sync_memory_select_all_check_geometry()
        self._sync_memory_bulk_actions()

    def _show_memory_placeholder(self, text: str) -> None:
        if not hasattr(self, "memory_table"):
            return
        self._visible_memories = []
        self._syncing_memory_selection = True
        self.memory_table.blockSignals(True)
        self.memory_table.clearContents()
        self.memory_table.setRowCount(1)
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.memory_table.setItem(0, 1, item)
        self.memory_table.setItem(0, 0, QTableWidgetItem(""))
        self.memory_table.setItem(0, 2, QTableWidgetItem(""))
        self.memory_table.setItem(0, 3, QTableWidgetItem(""))
        self.memory_table.blockSignals(False)
        self._syncing_memory_selection = False
        self._sync_memory_bulk_actions()

    def _handle_memory_item_clicked(self, item: QTableWidgetItem) -> None:
        if self._syncing_memory_selection:
            return
        if self._memory_editor_mode == "new" and self.memory_new_button.isChecked():
            self.memory_new_button.setChecked(False)
        row = item.row()
        if row < 0 or row >= len(self._visible_memories):
            return
        memory_id = str(self._visible_memories[row].get("id", ""))
        if not memory_id:
            return
        if item.column() == 0:
            self._set_memory_checked(row, memory_id not in self._selected_memory_ids)
            return
        self._switch_memory_single_selection(row)

    def _handle_memory_checkbox_state_changed(self, memory_id: str, checked: bool) -> None:
        if self._syncing_memory_selection:
            return
        if self._memory_editor_mode == "new" and self.memory_new_button.isChecked():
            self.memory_new_button.setChecked(False)
        row = self._visible_memory_row_by_id(memory_id)
        if row is None:
            return
        self._set_memory_checked(row, checked)

    def _switch_memory_single_selection(self, row: int) -> None:
        if row < 0 or row >= len(self._visible_memories):
            return
        memory_id = str(self._visible_memories[row].get("id", ""))
        if not memory_id:
            return
        self._selected_memory_ids = {memory_id}
        self._refresh_memory_table()
        self._open_memory_editor(row)

    def _handle_memory_select_all_check_changed(self, state: int) -> None:
        if self._syncing_memory_selection:
            return
        checked = state == Qt.CheckState.Checked.value
        self._set_all_visible_memories_checked(checked)

    def _set_memory_checked(self, row: int, checked: bool) -> None:
        if row < 0 or row >= len(self._visible_memories):
            return
        memory_id = str(self._visible_memories[row].get("id", ""))
        if not memory_id:
            return
        if checked:
            self._selected_memory_ids.add(memory_id)
        else:
            self._selected_memory_ids.discard(memory_id)

        item = self.memory_table.item(row, 0)
        if item is not None:
            self.memory_table.blockSignals(True)
            self.memory_table.blockSignals(False)
        self._sync_memory_checkbox_widget(row, checked)
        self._apply_memory_row_checked_style(row, checked)
        self._sync_memory_bulk_actions()

    def _open_memory_editor(self, row: int) -> None:
        if row < 0 or row >= len(self._visible_memories):
            return
        if self._memory_editor_mode == "new" and self.memory_new_button.isChecked():
            self.memory_new_button.setChecked(False)
        memory = self._visible_memories[row]
        memory_id = str(memory.get("id", ""))
        if not memory_id:
            return
        self._memory_editor_mode = "edit"
        self._editing_memory_id = memory_id
        self._active_memory_id = memory_id
        self.memory_content_edit.setPlainText(str(memory.get("content", "")))
        self.memory_content_edit.setPlaceholderText("编辑长期记忆内容")
        self.memory_save_button.setText("保存修改")
        self.memory_editor_container.setVisible(True)
        self.memory_preview_label.setText("")

    def _set_all_visible_memories_checked(self, checked: bool) -> None:
        visible_ids = {
            str(memory.get("id", ""))
            for memory in self._visible_memories
            if str(memory.get("id", ""))
        }
        if not visible_ids:
            return
        if checked:
            self._selected_memory_ids |= visible_ids
        else:
            self._selected_memory_ids -= visible_ids
        self._refresh_memory_table()

    def _toggle_select_all_visible_memories(self) -> None:
        visible_ids = {
            str(memory.get("id", ""))
            for memory in self._visible_memories
            if str(memory.get("id", ""))
        }
        if not visible_ids:
            return
        self._set_all_visible_memories_checked(
            not visible_ids.issubset(self._selected_memory_ids)
        )

    def _visible_memory_row_by_id(self, memory_id: str) -> int | None:
        for row, memory in enumerate(self._visible_memories):
            if str(memory.get("id", "")) == memory_id:
                return row
        return None

    def _set_memory_checkbox_widget(self, row: int, memory_id: str, checked: bool) -> None:
        container = QWidget(self.memory_table)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        checkbox = QCheckBox(container)
        checkbox.setChecked(checked)
        checkbox.setToolTip("选择这条记忆")
        checkbox.stateChanged.connect(
            lambda state, current_id=memory_id: self._handle_memory_checkbox_state_changed(
                current_id,
                state == Qt.CheckState.Checked.value,
            )
        )
        layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignCenter)
        container.setLayout(layout)
        self.memory_table.setCellWidget(row, 0, container)
        self._style_memory_checkbox_container(container, row, checked)

    def _sync_memory_checkbox_widget(self, row: int, checked: bool) -> None:
        container = self.memory_table.cellWidget(row, 0)
        if container is None:
            return
        checkbox = container.findChild(QCheckBox)
        if checkbox is not None:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)
        self._style_memory_checkbox_container(container, row, checked)

    def _style_memory_checkbox_container(self, container: QWidget, row: int, checked: bool) -> None:
        color = _memory_row_background_color(row, checked)
        container.setStyleSheet(f"background: {color};")

    def _sync_memory_select_all_check_geometry(self) -> None:
        if not hasattr(self, "memory_select_all_check"):
            return
        header = self.memory_table.horizontalHeader()
        checkbox_size = self.memory_select_all_check.sizeHint()
        section_x = header.sectionViewportPosition(0)
        section_width = header.sectionSize(0)
        x = section_x + max(0, (section_width - checkbox_size.width()) // 2)
        y = max(0, (header.height() - checkbox_size.height()) // 2)
        self.memory_select_all_check.setGeometry(
            x,
            y,
            checkbox_size.width(),
            checkbox_size.height(),
        )
        self.memory_select_all_check.raise_()

    def _toggle_memory_new_editor(self, checked: bool) -> None:
        if not hasattr(self, "memory_editor_container"):
            return
        if checked:
            self._clear_memory_selection()
            self._memory_editor_mode = "new"
            self._editing_memory_id = None
            self._active_memory_id = None
            self.memory_content_edit.clear()
            self.memory_content_edit.setPlaceholderText("新增长期记忆内容")
            self.memory_save_button.setText("保存")
            self.memory_preview_label.setText("正在新增记忆")
            self.memory_editor_container.setVisible(True)
        elif self._memory_editor_mode == "new":
            self._memory_editor_mode = None
            self._editing_memory_id = None
            self._active_memory_id = None
            self._clear_memory_editor()
            self.memory_editor_container.setVisible(False)
            self._sync_memory_bulk_actions()
        self.memory_new_button.setText("收起新增" if checked else "新增记忆")

    def _clear_memory_selection(self) -> None:
        if not hasattr(self, "memory_table"):
            return
        self._selected_memory_ids.clear()
        self._refresh_memory_table()

    def _sync_memory_bulk_actions(self) -> None:
        if not hasattr(self, "memory_table"):
            return
        selected_memories = self._selected_memories()
        selected_count = len(selected_memories)
        visible_ids = {
            str(memory.get("id", ""))
            for memory in self._visible_memories
            if str(memory.get("id", ""))
        }
        all_visible_selected = bool(visible_ids) and visible_ids.issubset(self._selected_memory_ids)

        self.memory_selection_label.setText(f"已选择 {selected_count} 条")
        self.memory_select_all_check.setEnabled(bool(visible_ids))
        self.memory_select_all_check.blockSignals(True)
        self.memory_select_all_check.setChecked(all_visible_selected)
        self.memory_select_all_check.blockSignals(False)
        self.memory_delete_button.setEnabled(selected_count > 0)
        self.memory_clear_selection_button.setEnabled(selected_count > 0)

        if self._memory_editor_mode != "new":
            self.memory_preview_label.setText("")

    def _apply_memory_row_checked_style(self, row: int, checked: bool) -> None:
        brush = _memory_row_background(row, checked)
        for column in range(self.memory_table.columnCount()):
            item = self.memory_table.item(row, column)
            if item is not None:
                item.setBackground(brush)
        container = self.memory_table.cellWidget(row, 0)
        if container is not None:
            self._style_memory_checkbox_container(container, row, checked)

    def _clear_memory_editor(self) -> None:
        if not hasattr(self, "memory_content_edit"):
            return
        self.memory_content_edit.clear()

    def _save_memory_entry(self) -> None:
        if self.memory_store is None:
            return
        content = self.memory_content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "内容为空", "记忆内容不能为空。")
            return
        try:
            if self._memory_editor_mode == "edit" and self._editing_memory_id:
                editing_id = self._editing_memory_id
                self.memory_store.update_memory(
                    {"id": editing_id, "content": content, "source": "manual"},
                    allow_sensitive=True,
                )
                self._selected_memory_ids = {editing_id}
                self._active_memory_id = editing_id
                success_message = "记忆已更新。"
            else:
                self.memory_store.create_memory(
                    {"content": content, "source": "manual"},
                    allow_sensitive=True,
                )
                self._memory_editor_mode = None
                self._editing_memory_id = None
                self._active_memory_id = None
                self._clear_memory_editor()
                self.memory_new_button.setChecked(False)
                success_message = "记忆已保存。"
        except (RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self._load_memory_entries()
        QMessageBox.information(self, "保存成功", success_message)

    def _delete_memory_entry(self) -> None:
        if self.memory_store is None:
            return
        memories = self._selected_memories()
        if not memories:
            QMessageBox.information(self, "未选择", "请先选择要删除的记忆。")
            return
        result = QMessageBox.question(
            self,
            "删除记忆",
            f"确定要删除选中的 {len(memories)} 条长期记忆吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        failed: list[str] = []
        deleted = 0
        for memory in memories:
            memory_id = str(memory.get("id", "")).strip()
            if not memory_id:
                failed.append("缺少记忆 ID")
                continue
            try:
                self.memory_store.forget_memory({"id": memory_id})
            except (RuntimeError, ValueError) as exc:
                failed.append(f"{_compact_memory_id(memory_id)}：{exc}")
            else:
                deleted += 1
        if self._editing_memory_id in self._selected_memory_ids:
            self._memory_editor_mode = None
            self._editing_memory_id = None
            self._active_memory_id = None
            self._clear_memory_editor()
            self.memory_editor_container.setVisible(False)
        self._clear_memory_selection()
        self._load_memory_entries()
        if failed:
            QMessageBox.warning(
                self,
                "删除完成",
                f"已删除 {deleted} 条，失败 {len(failed)} 条。\n" + "\n".join(failed),
            )

    def _selected_memory_rows(self) -> list[int]:
        if not hasattr(self, "memory_table"):
            return []
        return [
            row
            for row, memory in enumerate(self._visible_memories)
            if str(memory.get("id", "")) in self._selected_memory_ids
        ]

    def _selected_memories(self) -> list[dict[str, object]]:
        return [
            memory
            for memory in self._all_memories
            if str(memory.get("id", "")) in self._selected_memory_ids
        ]

    def _selected_memory(self) -> dict[str, object] | None:
        memories = self._selected_memories()
        if not memories:
            return None
        return memories[0]

    def accept(self) -> None:
        if self._api_test_thread is not None:
            QMessageBox.information(self, "测试中", "API 测试仍在进行，请等待完成后再保存设置。")
            return
        if self._character_export_thread is not None:
            QMessageBox.information(self, "导出中", "角色包导出仍在进行，请等待完成后再保存设置。")
            return

        api_settings = self._validated_api_settings()
        if api_settings is None:
            return
        tts_settings = self._validated_tts_settings()
        if tts_settings is None:
            return
        character_id = self._selected_character_id()
        if character_id is None:
            QMessageBox.warning(self, "配置无效", "请先导入并选择一个角色包。")
            return

        self.result_api_settings = api_settings
        self.result_tts_settings = tts_settings
        if not self._save_selected_character_card():
            return

        self.result_character_id = character_id
        self.result_portrait_scale_percent = self._selected_portrait_scale_percent()
        (
            self.result_subtitle_typing_interval_ms,
            self.result_reply_segment_pause_ms,
        ) = normalize_subtitle_display_speed(
            self.subtitle_typing_interval_spin.value(),
            self.reply_segment_pause_spin.value(),
        )
        proactive_screen_context_enabled = (
            self.proactive_topic_enabled_check.isChecked()
            and self.screen_observation_enabled_check.isChecked()
            and self.autonomous_screen_observation_check.isChecked()
        )
        self.result_proactive_care_settings = ProactiveCareSettings(
            enabled=self.proactive_topic_enabled_check.isChecked(),
            screen_context_enabled=proactive_screen_context_enabled,
            check_interval_minutes=self.proactive_check_interval_spin.value(),
            cooldown_minutes=self.proactive_cooldown_spin.value(),
            screen_context_batch_limit=self.proactive_batch_limit_spin.value(),
        )
        pet_ui = self.pet_ui_settings.normalized()
        self.result_pet_ui_settings = PetUISettings(
            hover_only_ui=self.hover_only_ui_check.isChecked(),
            subtitle_language=str(self.subtitle_language_combo.currentData() or SUBTITLE_LANGUAGE_ZH),
            free_access_enabled=self.free_access_enabled_check.isChecked(),
            music_plugin_enabled=self.music_plugin_enabled_check.isChecked(),
            music_default_source=pet_ui.music_default_source,
            lyric_sync_offset_seconds=self.lyric_sync_offset_spin.value(),
            music_sing_along_enabled=self.music_sing_along_enabled_check.isChecked(),
            ui_theme=str(self.ui_theme_combo.currentData() or ""),
            desktop_pet_rules_enabled=self.desktop_pet_rules_check.isChecked(),
            strict_ja_zh_correspondence_enabled=self.strict_ja_zh_correspondence_check.isChecked(),
            panel_width_percent=self._selected_panel_width_percent(),
        ).normalized()
        self.result_screen_observation_settings = ScreenObservationSettings(
            enabled=self.screen_observation_enabled_check.isChecked(),
            autonomous_enabled=self.autonomous_screen_observation_check.isChecked(),
        ).normalized()
        self.result_reminder_settings = ReminderSettings(
            enabled=self.reminders_enabled_check.isChecked(),
            check_interval_seconds=self.reminder_interval_spin.value(),
        ).normalized()
        self.result_memory_curation_settings = MemoryCurationSettings(
            enabled=self.memory_curation_enabled_check.isChecked(),
            trigger_turns=self.memory_curation_trigger_spin.value(),
            backfill_limit=self.memory_curation_backfill_spin.value(),
        )
        self.result_mcp_settings = MCPRuntimeSettings(
            windows_enabled=self.windows_mcp_enabled_check.isChecked(),
            playwright_enabled=self.playwright_mcp_enabled_check.isChecked(),
        )
        self.result_napcat_settings = NapCatSettings(
            enabled=self.napcat_enabled_check.isChecked(),
            host=self.napcat_host_edit.text() or DEFAULT_NAPCAT_BIND_HOST,
            port=self.napcat_port_spin.value(),
            path=self.napcat_path_edit.text() or DEFAULT_NAPCAT_PATH,
            connect_host=self.napcat_connect_host_combo.currentText().strip(),
            token=self.napcat_token_edit.text(),
            allow_private=self.napcat_allow_private_check.isChecked(),
            allow_group=self.napcat_allow_group_check.isChecked(),
            history_limit=self.napcat_history_limit_spin.value(),
            busy_reply_text=self.napcat_busy_reply_edit.text(),
            reply_mode=str(
                self.napcat_reply_mode_combo.currentData() or NAPCAT_REPLY_BOTH
            ),
        ).normalized()
        self.result_debug_log_settings = DebugLogSettings(
            enabled=self.debug_log_enabled_check.isChecked(),
            body_enabled=(
                self.debug_log_enabled_check.isChecked()
                and self.debug_body_enabled_check.isChecked()
            ),
            file_enabled=self.debug_file_enabled_check.isChecked(),
        )
        stt_settings = self._validated_stt_settings()
        if stt_settings is None:
            return
        try:
            audio_io.configure_audio_paths(stt_settings, self.base_dir)
            audio_io.set_input_device(stt_settings.input_device_index)
        except (OSError, audio_io.AudioIOError) as exc:
            QMessageBox.warning(self, "语音输入", f"无法应用麦克风设置：{exc}")
            return
        self.result_stt_settings = stt_settings
        super().accept()

    def reject(self) -> None:
        if self._api_test_thread is not None:
            QMessageBox.information(self, "测试中", "API 测试仍在进行，请等待完成后再关闭设置。")
            return
        if self._character_export_thread is not None:
            QMessageBox.information(self, "导出中", "角色包导出仍在进行，请等待完成后再关闭设置。")
            return
        super().reject()

    def closeEvent(self, event):  # type: ignore[no-untyped-def]
        if self._character_export_thread is not None:
            QMessageBox.information(self, "导出中", "角色包导出仍在进行，请等待完成后再关闭设置。")
            event.ignore()
            return
        super().closeEvent(event)

    def _test_api_settings(self) -> None:
        settings = self._validated_api_settings()
        if settings is None or self._api_test_thread is not None:
            return

        self.api_test_button.setEnabled(False)
        self.api_test_button.setText("测试中...")

        thread = QThread(self)
        worker = ApiConnectionTestWorker(settings)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._handle_api_test_success)
        worker.failed.connect(self._handle_api_test_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._reset_api_test_state)

        self._api_test_thread = thread
        self._api_test_worker = worker
        thread.start()

    @Slot(str)
    def _handle_api_test_success(self, message: str) -> None:
        QMessageBox.information(self, "测试成功", f"API 连接成功，模型返回：{message}")

    @Slot(str)
    def _handle_api_test_failed(self, message: str) -> None:
        QMessageBox.warning(self, "测试失败", message)

    @Slot()
    def _reset_api_test_state(self) -> None:
        self.api_test_button.setEnabled(True)
        self.api_test_button.setText("测试 API")
        self._api_test_thread = None
        self._api_test_worker = None

    def _download_gpt_sovits_bundle(self) -> None:
        dialog = TTSBundleDownloadDialog(self.base_dir, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.downloaded_work_dir is None:
            return
        provider = TTS_PROVIDER_GPT_SOVITS
        provider_index = self.tts_provider_combo.findData(provider)
        if provider_index >= 0:
            self.tts_provider_combo.setCurrentIndex(provider_index)
        self.tts_work_dir_edit.setText(str(dialog.downloaded_work_dir))
        self.tts_api_url_edit.setText(_default_tts_api_url(provider))
        self.tts_enabled_check.setChecked(True)

    @Slot()
    def _sync_tts_provider_controls(self) -> None:
        provider = str(self.tts_provider_combo.currentData() or TTS_PROVIDER_GPT_SOVITS)
        self.tts_api_url_edit.setPlaceholderText(_default_tts_api_url(provider))
        self.tts_work_dir_edit.setPlaceholderText("data/tts_bundles/installed/gpt_sovits_nvidia50/GPT-SoVITS-v2pro-20250604-nvidia50")

    def _import_character_archive(self) -> None:
        if self._character_export_thread is not None:
            QMessageBox.information(self, "导出中", "角色包导出仍在进行，请等待完成后再导入。")
            return
        path_text, _ = QFileDialog.getOpenFileName(
            self,
            "导入 Mutsuki 角色包",
            str(self.base_dir),
            "Mutsuki 角色包 (*.char)",
        )
        if not path_text:
            return
        try:
            result = import_character_archive(Path(path_text), self.base_dir)
            self.character_registry = CharacterRegistry(self.base_dir)
            self._refresh_character_combo(result.character_id)
            self._sync_character_archive_controls()
        except (CharacterArchiveError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        QMessageBox.information(
            self,
            "导入成功",
            f"已导入角色「{result.display_name}」。点击保存后会切换到该角色。",
        )

    def _export_current_character_archive(self) -> None:
        if self._character_export_thread is not None:
            return
        profile = self._selected_character_profile()
        if profile is None:
            QMessageBox.warning(self, "导出失败", "当前没有可导出的角色。")
            return
        output_text, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Mutsuki 角色包",
            str(self.base_dir / f"{profile.id}.char"),
            "Mutsuki 角色包 (*.char)",
        )
        if not output_text:
            return
        output_path = Path(output_text)
        if output_path.suffix.lower() != ".char":
            output_path = output_path.with_suffix(".char")
        self._start_character_archive_export(profile, output_path)

    def _start_character_archive_export(
        self,
        profile: CharacterProfile,
        output_path: Path,
    ) -> None:
        self._set_character_export_busy(True)
        thread = QThread(self)
        worker = CharacterArchiveExportWorker(profile, output_path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._handle_character_export_success)
        worker.failed.connect(self._handle_character_export_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._reset_character_export_state)

        self._character_export_thread = thread
        self._character_export_worker = worker
        thread.start()

    @Slot(str)
    def _handle_character_export_success(self, output_path: str) -> None:
        QMessageBox.information(self, "导出成功", f"角色包已导出到：{output_path}")

    @Slot(str)
    def _handle_character_export_failed(self, message: str) -> None:
        QMessageBox.warning(self, "导出失败", message)

    @Slot()
    def _reset_character_export_state(self) -> None:
        self._character_export_thread = None
        self._character_export_worker = None
        self._set_character_export_busy(False)

    def _set_character_export_busy(self, busy: bool) -> None:
        if hasattr(self, "button_box"):
            save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
            cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
            if save_button is not None:
                save_button.setEnabled(not busy)
            if cancel_button is not None:
                cancel_button.setEnabled(not busy)
        if hasattr(self, "character_import_button"):
            self.character_import_button.setEnabled(not busy)
        if hasattr(self, "character_export_button"):
            self.character_export_button.setEnabled(
                not busy and self._selected_character_profile() is not None
            )

    def _sync_character_archive_controls(self) -> None:
        self._set_character_export_busy(self._character_export_thread is not None)

    def _validated_api_settings(self) -> ApiSettings | None:
        base_url = self.base_url_edit.text().strip().rstrip("/")
        api_key = self.api_key_edit.text().strip()
        model = self.model_edit.text().strip()

        if not _is_http_url(base_url):
            QMessageBox.warning(self, "配置无效", "Base URL 必须是有效的 http 或 https 地址。")
            return None
        if not api_key:
            QMessageBox.warning(self, "配置无效", "API Key 不能为空。")
            return None
        if not model:
            QMessageBox.warning(self, "配置无效", "模型不能为空。")
            return None

        return ApiSettings(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=self.api_timeout_spin.value(),
        )

    def _validated_tts_settings(self) -> GPTSoVITSTTSSettings | None:
        enabled = self.tts_enabled_check.isChecked()
        provider = str(self.tts_provider_combo.currentData() or TTS_PROVIDER_GPT_SOVITS)
        api_url = self.tts_api_url_edit.text().strip()
        work_dir = _optional_path(self.tts_work_dir_edit.text(), self.base_dir)
        ref_lang = self.ref_lang_edit.text().strip()
        text_lang = self.text_lang_edit.text().strip()

        if enabled and not _is_http_url(api_url):
            QMessageBox.warning(self, "配置无效", "TTS API URL 必须是有效的 http 或 https 地址。")
            return None

        selected_profile = self._selected_character_profile()
        if selected_profile is not None:
            settings = GPTSoVITSTTSSettings.from_character_profile(
                character_profile=selected_profile,
                enabled=enabled,
                api_url=api_url,
                ref_lang=ref_lang,
                text_lang=text_lang,
                timeout_seconds=self.tts_timeout_spin.value(),
                provider=provider,
                work_dir=work_dir,
                validate_enabled=False,
            )
            settings = replace(settings, streaming_enabled=True)
        else:
            settings = GPTSoVITSTTSSettings(
                enabled=enabled,
                api_url=api_url,
                ref_audio_path=self.tts_settings.ref_audio_path,
                ref_text_path=self.tts_settings.ref_text_path,
                ref_text=self.tts_settings.ref_text,
                provider=provider,
                gpt_model_path=self.tts_settings.gpt_model_path,
                sovits_model_path=self.tts_settings.sovits_model_path,
                work_dir=work_dir,
                character_name=self.tts_settings.character_name or "sakura",
                ref_lang=ref_lang,
                text_lang=text_lang,
                timeout_seconds=self.tts_timeout_spin.value(),
                streaming_enabled=True,
                tone_references=self.tts_settings.tone_references,
            )
        if enabled:
            try:
                settings.validate()
            except TTSConfigError as exc:
                QMessageBox.warning(self, "配置无效", str(exc))
                return None
        return settings

    def _selected_character_id(self) -> str | None:
        if self.character_registry is None or not hasattr(self, "character_combo"):
            return self.current_character.id if self.current_character is not None else None
        character_id = self.character_combo.currentData()
        if isinstance(character_id, str) and character_id.strip():
            return character_id.strip()
        return self.current_character.id if self.current_character is not None else None

    def _selected_character_profile(self) -> CharacterProfile | None:
        character_id = self._selected_character_id()
        if character_id is None or self.character_registry is None:
            return self.current_character
        return self.character_registry.get(character_id)

    def _load_selected_character_card(self) -> None:
        if not hasattr(self, "character_card_edit"):
            return
        profile = self._selected_character_profile()
        if profile is None:
            self.character_card_edit.clear()
            self.character_card_edit.setEnabled(False)
            if hasattr(self, "character_card_hint"):
                self.character_card_hint.setEnabled(False)
            return
        self.character_card_edit.setEnabled(True)
        if hasattr(self, "character_card_hint"):
            self.character_card_hint.setEnabled(True)
        try:
            content = read_character_card(profile)
        except CharacterConfigError as exc:
            self.character_card_edit.setPlainText("")
            self.character_card_edit.setEnabled(False)
            if hasattr(self, "character_card_hint"):
                self.character_card_hint.setText(str(exc))
            return
        self.character_card_edit.setPlainText(content)
        if hasattr(self, "character_card_hint"):
            palette = ui_theme_palette(
                str(self.ui_theme_combo.currentData() or "")
                if hasattr(self, "ui_theme_combo")
                else None
            )
            self.character_card_hint.setStyleSheet(f"color: {palette.hint_text};")
            self.character_card_hint.setText(
                f"正在编辑：{profile.display_name}（{profile.card_path.name}）\n"
                "人设会作为系统提示词影响回复风格。保存后立即作用于后续对话。"
            )

    def _save_selected_character_card(self) -> bool:
        if not hasattr(self, "character_card_edit") or not self.character_card_edit.isEnabled():
            return True
        profile = self._selected_character_profile()
        if profile is None:
            return True
        content = self.character_card_edit.toPlainText()
        try:
            write_character_card(profile, content)
        except CharacterConfigError as exc:
            QMessageBox.warning(self, "人设保存失败", str(exc))
            return False
        return True

    def _selected_portrait_scale_percent(self) -> int:
        if hasattr(self, "portrait_scale_spin"):
            return normalize_portrait_scale_percent(self.portrait_scale_spin.value())
        return self.portrait_scale_percent

    def _selected_panel_width_percent(self) -> int:
        if hasattr(self, "panel_width_spin"):
            return normalize_panel_width_percent(self.panel_width_spin.value())
        return self.pet_ui_settings.normalized().panel_width_percent

    def _refresh_character_combo(self, selected_character_id: str | None = None) -> None:
        if not hasattr(self, "character_combo"):
            return
        selected_id = selected_character_id or self._selected_character_id()
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        selected_index = -1
        profiles = list(self.character_registry.all()) if self.character_registry is not None else []
        for profile in profiles:
            self.character_combo.addItem(profile.display_name, profile.id)
            if profile.id == selected_id:
                selected_index = self.character_combo.count() - 1
        if selected_index >= 0:
            self.character_combo.setCurrentIndex(selected_index)
        elif self.character_combo.count() > 0:
            self.character_combo.setCurrentIndex(0)
        else:
            self.character_combo.addItem("尚未导入角色", None)
        has_character = bool(profiles)
        self.character_combo.setEnabled(has_character)
        if hasattr(self, "character_empty_label"):
            self.character_empty_label.setVisible(not has_character)
        self.character_combo.blockSignals(False)
        self._sync_character_archive_controls()
        self._load_selected_character_card()


def _is_http_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def _default_tts_api_url(provider: str) -> str:
    return DEFAULT_GPT_SOVITS_API_URL


def _optional_path(value: str, base_dir: Path) -> Path | None:
    text = value.strip().strip('"').strip("'")
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return base_dir / path


def _compact_memory_id(memory_id: str) -> str:
    if len(memory_id) <= 16:
        return memory_id
    return f"{memory_id[:8]}...{memory_id[-4:]}"


def _memory_row_background(row: int, checked: bool) -> QBrush:
    return QBrush(QColor(_memory_row_background_color(row, checked)))


def _memory_row_background_color(row: int, checked: bool) -> str:
    if checked:
        return "#f4c4da"
    if row % 2:
        return "#fff4f9"
    return "#fffafd"


def _format_memory_time(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        legacy_text = text.replace("T", " ").replace("Z", "")
        for separator in ("+", "."):
            legacy_text = legacy_text.split(separator, 1)[0]
        return legacy_text
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone()
    return parsed.strftime("%Y-%m-%d %H:%M:%S")
