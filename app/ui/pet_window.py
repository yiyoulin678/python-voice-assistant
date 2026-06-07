from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRect,
    Qt,
    QThread,
    QTimer,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QCursor,
    QFont,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.agent import (
    AgentEvent,
    AgentProgress,
    AgentResult,
    PendingToolAction,
)
from app.agent.memory_curator import (
    MemoryCurationResult,
)
from app.agent.memory_curation_worker import MemoryCurationWorker
from app.agent.screen_tools import SCREEN_OBSERVATION_REQUEST_ACTION
from app.config.deskpet_settings import normalize_panel_width_percent
from app.core.app_context import AppContext
from app.config.character_loader import (
    DEFAULT_CHARACTER_ID,
    CharacterConfigError,
    CharacterProfile,
    load_character_system_prompt,
)
from app.storage.chat_history import ChatHistoryEntry, ChatHistoryStore
from app.llm.chat_reply import ChatReply, ChatSegment, parse_chat_reply_result
from app.llm.context_trimming import trim_messages_for_model
from app.core.chat_worker import ChatWorker, EventWorker
from app.core.debug_log import debug_log, summarize_messages
from app.ui.history_window import HistoryWindow
from app.platforms.napcat import NapCatBridge
from app.platforms.napcat.log import napcat_log
from app.platforms.napcat.onebot_v11 import (
    NapCatInboundMessage,
    format_agent_reply_text,
    format_inbound_pet_display,
)
from app.platforms.napcat.outbound import (
    format_outbound_pet_display,
    parse_outbound_directive,
)
from app.ui.napcat_console_window import NapCatConsoleWindow
from app.agent.proactive_care import (
    PROACTIVE_SCREEN_CONTEXT_HISTORY_MARKER,
    PROACTIVE_TOPIC_HISTORY_MARKER,
    PROACTIVE_TIMER_DUE_GRACE_SECONDS,
    PROACTIVE_TIMER_POLL_INTERVAL_MS,
    compute_proactive_care_countdown_seconds,
    format_proactive_care_countdown_hint,
)
from app.agent.screen_observation import (
    SCREEN_OBSERVATION_HISTORY_MARKER,
    ScreenObservation,
    append_manual_observation_marker,
    append_observation_marker,
    build_screen_observation_from_pixmap,
    build_screen_observation_user_message,
    capture_screen_observation,
)
from app.ui.settings_dialog import SettingsDialog
from app.ui.win_click_through import apply_locked_mouse_transparency, apply_locked_window_region
from app.live2d.runtime import ensure_live2d_init, is_live2d_available, live2d_import_error
from app.ui.live2d_portrait_controller import Live2DPortraitController
from app.ui.portrait_controller import (
    PORTRAIT_SCALE_DEFAULT_PERCENT,
    PortraitController,
    normalize_portrait_scale_percent,
)
from app.ui.subtitle_controller import (
    REPLY_SEGMENT_PAUSE_MS,
    SPEECH_TYPING_INTERVAL_MS,
    normalize_subtitle_display_speed,
)
from app.voice.tts import (
    TTS_PROVIDER_GENIE,
    GenieTTSProvider,
    GPTSoVITSTTSProvider,
    GPTSoVITSTTSSettings,
    NullTTSProvider,
    TTSConfigError,
    TTSProvider,
)
from app.storage.visual_observation import (
    VISUAL_OBSERVATION_RECENT_MINUTES,
    VisualObservationJob,
    VisualObservationStore,
    build_visual_context_message,
    generate_visual_observation_id,
    should_inject_visual_context,
)
from app.ui.app_icon import load_tray_icon
from app.ui.fonts import _rounded_chinese_font, _rounded_japanese_font
from app.ui import (
    FrostedGlassFrame,
    ManualScreenshotOverlay,
    build_pet_window_stylesheet,
    SubtitleController,
    ToolConfirmationPanel,
    build_pet_tray_menu,
    capture_virtual_desktop_pixmap,
)
from app.media.music_sing_along import MusicSingAlongController
from app.media.now_playing import set_preferred_music_source
from app.ui.music_lyrics_overlay import LYRICS_OVERLAY_HEIGHT, MusicLyricsOverlay
from app.storage.chat_audio import archive_chat_audio, export_qq_voice_audio
from app.voice.text_language_guard import should_skip_tts_text
from app.voice import VoicePlaybackController
from app.voice import audio_io, speech_to_text
from app.voice.history_audio_player import HistoryAudioPlayer
from app.voice.stt_settings import STTSettings
from app.voice.voice_workers import (
    StartRecordingWorker,
    StopRecordTranscribeWorker,
    VoiceTranscribeResult,
)

if TYPE_CHECKING:
    from app.core.bootstrap import DeferredStartupServices


REMINDER_CHECK_INTERVAL_MS = 5_000  # 默认；实际间隔由 settings.reminders 决定
STARTUP_INITIALIZING_TEXT = "初始化中……"
TTS_ERROR_DISPLAY_MS = 8_000
SUBTITLE_LANGUAGE_JA = "ja"
SUBTITLE_LANGUAGE_ZH = "zh"
MANUAL_SCREENSHOT_DEFAULT_TEXT = "请根据我框选的截图继续对话。"
PROACTIVE_RECENT_CONVERSATION_LIMIT = 12
PROACTIVE_RECENT_CONVERSATION_CONTENT_LIMIT = 800
PROACTIVE_RECENT_CONVERSATION_SUMMARY_HINT = (
    "这些 recent_conversation 消息用于理解这段时间发生了什么、用户当前阶段和 Mutsuki "
    "刚刚说过什么；不要逐字复述，应结合屏幕变化自然回应，并避免连续重复同一种休息提醒。"
)
REPLY_HISTORY_PANEL_WIDTH = 28
REPLY_HISTORY_PANEL_HEIGHT = 58
REPLY_HISTORY_BUTTON_SIZE = 26
REPLY_HISTORY_PREVIOUS_SYMBOL = "▲"
REPLY_HISTORY_NEXT_SYMBOL = "▼"
DEFAULT_STAGE_WIDTH = 560
DEFAULT_STAGE_HEIGHT = 500
BUBBLE_MAX_WIDTH = 360
BUBBLE_SIDE_MARGIN = 56
BUBBLE_HEIGHT = 108
INPUT_BAR_HEIGHT = 40
INPUT_CONTROL_HEIGHT = 28
STAGE_BOTTOM_INSET = 50
BUBBLE_TOP_GAP = 68
INPUT_ABOVE_BUBBLE_GAP = 8
LYRICS_OVERLAY_BOTTOM_INSET = 12


class PetWindow(QWidget):
    def __init__(
        self,
        context: AppContext,
    ) -> None:
        super().__init__()
        self.context = context
        self.base_dir = context.base_dir
        self.startup_initializing = context.startup_initializing
        self.deferred_startup_thread: QThread | None = None
        self.deferred_startup_worker: QObject | None = None
        self.settings_service = context.settings_service
        self.character_registry = context.character_registry
        self.character_profile = context.character_profile
        self.api_client = context.api_client
        self.system_prompt = context.system_prompt
        self.memory_store = context.memory_store
        self.reminder_store = context.reminder_store
        self.tool_registry = context.tool_registry
        self.mcp_tool_provider = context.mcp_tool_provider
        self.plugin_manager = context.plugin_manager
        self.agent_runtime = context.agent_runtime
        self.tts_provider = context.tts_provider
        self.retired_tts_providers: list[TTSProvider] = []
        self.history_store = context.history_store
        self.visual_observation_store = context.visual_observation_store
        self.mcp_settings = context.mcp_settings
        self.debug_log_settings = context.debug_log_settings
        self.memory_curation_settings = context.memory_curation_settings
        self.memory_curation_state = context.memory_curation_state
        self.memory_curator = context.memory_curator
        pet_ui_settings = self.settings_service.load_pet_ui_settings()
        self.hover_only_ui_enabled = pet_ui_settings.hover_only_ui
        self.subtitle_language = pet_ui_settings.subtitle_language
        self.free_access_enabled = pet_ui_settings.free_access_enabled
        self.music_plugin_enabled = pet_ui_settings.music_plugin_enabled
        self.music_default_source = pet_ui_settings.music_default_source
        self.lyric_sync_offset_seconds = pet_ui_settings.lyric_sync_offset_seconds
        self.music_sing_along_enabled = pet_ui_settings.music_sing_along_enabled
        self.ui_theme = pet_ui_settings.ui_theme
        self.desktop_pet_rules_enabled = pet_ui_settings.desktop_pet_rules_enabled
        self.strict_ja_zh_correspondence_enabled = (
            pet_ui_settings.strict_ja_zh_correspondence_enabled
        )
        self.panel_width_percent = pet_ui_settings.normalized().panel_width_percent
        self.agent_runtime.set_strict_ja_zh_correspondence_enabled(
            self.strict_ja_zh_correspondence_enabled
        )
        set_preferred_music_source(pet_ui_settings.music_default_source)
        self.music_lyrics_overlay: MusicLyricsOverlay | None = None
        self._music_sing_along_controller: MusicSingAlongController | None = None
        self.ui_locked = False
        self._portrait_hit_rect = QRect()
        screen_observation_settings = self.settings_service.load_screen_observation_settings()
        self.screen_observation_enabled = screen_observation_settings.enabled
        self.autonomous_screen_observation_enabled = (
            screen_observation_settings.autonomous_enabled
        )
        self.reminder_settings = self.settings_service.load_reminder_settings()
        self.proactive_care_settings = context.proactive_care_settings
        self.model_vision_enabled = self.screen_observation_enabled
        self.agent_runtime.set_model_vision_enabled(self.model_vision_enabled)
        self.agent_runtime.set_autonomous_screen_observation_enabled(
            self.autonomous_screen_observation_enabled
        )
        self.tool_registry.set_free_access_enabled(self.free_access_enabled)
        self.history_window: HistoryWindow | None = None
        self.messages: list[dict[str, Any]] = []
        self.worker_thread: QThread | None = None
        self.worker: ChatWorker | EventWorker | None = None
        self.stt_settings = self.settings_service.load_stt_settings()
        try:
            audio_io.configure_audio_paths(self.stt_settings, self.base_dir)
            speech_to_text.configure_whisper_cache(self.base_dir, self.stt_settings)
        except OSError as exc:
            print(f"[STT] 初始化音频路径失败: {exc}")
        self._voice_recording = False
        self._voice_rec_starting = False
        self._voice_from_long_press = False
        self._voice_long_press_cancel_pending = False
        self._voice_rec_worker: QObject | None = None
        self._voice_transcribe_thread: QThread | None = None
        self._voice_transcribe_worker: QObject | None = None
        self.memory_curation_thread: QThread | None = None
        self.memory_curation_worker: MemoryCurationWorker | None = None
        self.memory_curation_mode = ""
        self.memory_curation_target_history_count = 0
        self.memory_curation_consumed_turns = 0
        self.drag_offset: QPoint | None = None
        self.portrait_scale_percent = self._load_portrait_scale_percent()
        (
            self.subtitle_typing_interval_ms,
            self.reply_segment_pause_ms,
        ) = self._load_subtitle_display_speed()
        self.stage_size = _stage_size_for_layout(
            self.portrait_scale_percent,
            self.panel_width_percent,
        )
        self.pending_tool_action: PendingToolAction | None = None
        self.pending_manual_screen_observation: ScreenObservation | None = None
        self.manual_screenshot_overlay: ManualScreenshotOverlay | None = None
        self._pending_napcat_message: NapCatInboundMessage | None = None
        self._pending_napcat_voice_message: NapCatInboundMessage | None = None
        self._outbound_napcat_target: NapCatInboundMessage | None = None
        self.pending_screen_observation_messages: list[dict[str, Any]] | None = None
        self.pending_screen_observation_event: AgentEvent | None = None
        self.pending_screen_observation_event_reminder_id: str | None = None
        self.pending_visual_observation_jobs: list[VisualObservationJob] = []
        self.pending_event_visual_observation_jobs: list[VisualObservationJob] = []
        self.screen_observation_followup_in_progress = False
        self.active_reminder_id: str | None = None
        self.active_reminder_text = ""
        self.active_event_type = ""
        self.active_event: AgentEvent | None = None
        self.last_user_activity_at = time.perf_counter()
        self.last_proactive_care_at: float | None = None
        self.last_proactive_screen_context_at: float | None = None
        self.proactive_screen_context_batch_started_at: float | None = None
        self.proactive_screen_contexts: list[dict[str, Any]] = []
        self.proactive_screen_context_dropped_count = 0
        self.interaction_sequence = 0
        self.active_interaction_id = ""
        self.active_interaction_started_at: float | None = None
        self.active_interaction_last_at: float | None = None
        self.reply_history_segments: list[ChatSegment] = []
        self.reply_history_index: int | None = None
        self.reply_history_review_active = False
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(self.reminder_settings.check_interval_ms)
        self.reminder_timer.timeout.connect(self._check_due_reminders)
        self.proactive_care_timer = QTimer(self)
        self.proactive_care_timer.setInterval(PROACTIVE_TIMER_POLL_INTERVAL_MS)
        self.proactive_care_timer.timeout.connect(self._on_proactive_care_timer)
        if not self.startup_initializing:
            if self.reminder_settings.enabled:
                self.reminder_timer.start()
            self._sync_proactive_care_timer()
            QTimer.singleShot(0, self._maybe_start_memory_backfill)
        debug_log(
            "PetWindow",
            "窗口运行状态初始化",
            {
                "character_id": self.character_profile.id,
                "character_name": self.character_profile.display_name,
                "tool_count": len(self.tool_registry.all()),
                "mcp_enabled": self.mcp_tool_provider is not None,
                "windows_mcp_enabled": self.mcp_settings.windows_enabled,
                "tts_provider": type(self.tts_provider).__name__,
                "subtitle_language": self.subtitle_language,
                "screen_observation_enabled": self.screen_observation_enabled,
                "autonomous_screen_observation_enabled": self.autonomous_screen_observation_enabled,
                "subtitle_typing_interval_ms": self.subtitle_typing_interval_ms,
                "reply_segment_pause_ms": self.reply_segment_pause_ms,
                "proactive_care": self.proactive_care_settings,
                "auto_memory": self.memory_curation_settings,
            },
        )

        self.setWindowTitle(self.character_profile.display_name)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.label.customContextMenuRequested.connect(self._show_context_menu)
        self.portrait_opacity_effect = QGraphicsOpacityEffect(self.label)
        self.portrait_opacity_effect.setOpacity(1.0)
        self.label.setGraphicsEffect(self.portrait_opacity_effect)

        self.portrait_transition_label = QLabel(self)
        self.portrait_transition_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait_transition_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.portrait_transition_label.customContextMenuRequested.connect(self._show_context_menu)
        self.portrait_transition_label.hide()
        self.portrait_transition_opacity_effect = QGraphicsOpacityEffect(self.portrait_transition_label)
        self.portrait_transition_opacity_effect.setOpacity(0.0)
        self.portrait_transition_label.setGraphicsEffect(self.portrait_transition_opacity_effect)
        self._using_live2d = False
        self._live2d_hover_ui = False
        self._ui_controls_holds: set[str] = set()
        self._ui_hover_count = 0
        self._ui_controls_visible_applied = False
        self.portrait_controller = self._build_portrait_controller(self.character_profile)
        self._connect_live2d_tts_signals(self.tts_provider)
        self._ui_hover_leave_timer = QTimer(self)
        self._ui_hover_leave_timer.setSingleShot(True)
        self._ui_hover_leave_timer.timeout.connect(self._finalize_ui_hover_release)

        self.bubble = QFrame(self)
        self.bubble.setObjectName("speechBubble")
        self.bubble.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bubble.customContextMenuRequested.connect(self._show_context_menu)

        self.name_label = QLabel(self.character_profile.display_name, self.bubble)
        self.name_label.setObjectName("speakerName")

        initial_speech = (
            STARTUP_INITIALIZING_TEXT
            if self.startup_initializing
            else self.character_profile.initial_message
        )
        self.speech_label = QLabel(initial_speech, self.bubble)
        self.speech_label.setObjectName("speechText")
        self.speech_label.setWordWrap(True)
        self.speech_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self.tts_error_label = QLabel("", self.bubble)
        self.tts_error_label.setObjectName("ttsErrorText")
        self.tts_error_label.setWordWrap(True)
        self.tts_error_label.setVisible(False)
        self.tts_error_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.tts_error_timer = QTimer(self)
        self.tts_error_timer.setSingleShot(True)
        self.tts_error_timer.timeout.connect(self._hide_tts_error)

        self.reply_history_panel = QFrame(self.bubble)
        _configure_reply_history_panel(self.reply_history_panel)

        self.reply_history_previous_button = QToolButton(self.reply_history_panel)
        _configure_reply_history_button(
            self.reply_history_previous_button,
            text=REPLY_HISTORY_PREVIOUS_SYMBOL,
            tooltip="上一条历史消息",
        )
        self.reply_history_previous_button.clicked.connect(self._show_previous_reply_history)

        self.reply_history_next_button = QToolButton(self.reply_history_panel)
        _configure_reply_history_button(
            self.reply_history_next_button,
            text=REPLY_HISTORY_NEXT_SYMBOL,
            tooltip="下一条历史消息",
        )
        self.reply_history_next_button.clicked.connect(self._show_next_reply_history)

        self.voice_playback_controller = VoicePlaybackController(
            self.tts_provider,
            self._log_interaction_stage,
            lambda: str(getattr(getattr(self.tts_provider, "settings", None), "text_lang", "ja")),
            self._show_tts_error,
        )
        self.history_audio_player = HistoryAudioPlayer(self)
        self._active_segment_audio_path: str | None = None
        self._connect_tts_error_signal(self.tts_provider)
        self.subtitle_controller = SubtitleController(
            self.speech_label,
            self.voice_playback_controller,
            self.subtitle_language,
            self._log_interaction_stage,
            self._apply_reply_segment,
            self._finish_reply_interaction,
            lambda: bool(self.active_interaction_id),
            self,
            preload_segment=self.portrait_controller.preload_for_segment,
            on_segment_completed=self._on_reply_segment_completed,
            on_reply_flow_cancelled=self._end_live2d_speech,
            typing_interval_ms=self.subtitle_typing_interval_ms,
            segment_pause_ms=self.reply_segment_pause_ms,
        )
        self.speech_timer = self.subtitle_controller.speech_timer
        if not self.startup_initializing:
            QTimer.singleShot(0, self._warm_up_current_tts)

        bubble_header = QHBoxLayout()
        bubble_header.setContentsMargins(0, 0, 0, 0)
        bubble_header.addWidget(self.name_label)
        bubble_header.addStretch(1)

        bubble_text_layout = QVBoxLayout()
        bubble_text_layout.setContentsMargins(0, 0, 0, 0)
        bubble_text_layout.setSpacing(6)
        bubble_text_layout.addLayout(bubble_header)
        bubble_text_layout.addWidget(self.speech_label, 1)
        bubble_text_layout.addWidget(self.tts_error_label)

        history_button_layout = QVBoxLayout()
        history_button_layout.setContentsMargins(2, 3, 2, 3)
        history_button_layout.setSpacing(4)
        history_button_layout.addWidget(self.reply_history_previous_button)
        history_button_layout.addWidget(self.reply_history_next_button)
        self.reply_history_panel.setLayout(history_button_layout)

        bubble_body_layout = QHBoxLayout()
        bubble_body_layout.setContentsMargins(0, 0, 0, 0)
        bubble_body_layout.setSpacing(10)
        bubble_body_layout.addLayout(bubble_text_layout, 1)
        bubble_body_layout.addWidget(self.reply_history_panel, 0, Qt.AlignmentFlag.AlignVCenter)

        bubble_layout = QVBoxLayout()
        bubble_layout.setContentsMargins(22, 12, 18, 14)
        bubble_layout.setSpacing(0)
        bubble_layout.addLayout(bubble_body_layout, 1)
        self.bubble.setLayout(bubble_layout)

        self.input_backdrop = FrostedGlassFrame(self)
        self._refresh_input_backdrop_sources()

        self.input_bar = QFrame(self)
        self.input_bar.setObjectName("inputBar")

        self.input_edit = QLineEdit(self.input_bar)
        self.input_edit.setObjectName("petInput")
        self.input_edit.setPlaceholderText(f"和{self.character_profile.display_name}说点什么...")
        self.input_edit.setFixedHeight(INPUT_CONTROL_HEIGHT)
        self.input_edit.installEventFilter(self)
        self.input_edit.returnPressed.connect(self._handle_return_pressed)

        self.screenshot_button = QPushButton("截图", self.input_bar)
        self.screenshot_button.setObjectName("screenshotButton")
        self.screenshot_button.setFixedHeight(INPUT_CONTROL_HEIGHT)
        self.screenshot_button.setProperty("screenshotAttached", False)
        self.screenshot_button.setToolTip("框选截图并附加到下一条消息；右键清除")
        self.screenshot_button.installEventFilter(self)
        self.screenshot_button.clicked.connect(self._handle_screenshot_button_clicked)

        self.voice_button = QPushButton("语音", self.input_bar)
        self.voice_button.setObjectName("voiceButton")
        self.voice_button.setFixedHeight(INPUT_CONTROL_HEIGHT)
        self.voice_button.setProperty("recording", False)
        self.voice_button.setToolTip(
            "点击开始录音，再次点击结束并识别（建议至少说 1～2 秒）"
        )
        self.voice_button.clicked.connect(self._handle_voice_button_clicked)
        if not self.stt_settings.enabled:
            self.voice_button.setEnabled(False)
            self.voice_button.setToolTip("语音输入已在 data/config/system_config.yaml 中关闭")

        self.tool_confirmation_panel = ToolConfirmationPanel(
            self.confirm_pending_action,
            self.cancel_pending_action,
            self.input_bar,
        )
        self.confirm_action_button = self.tool_confirmation_panel.confirm_button
        self.cancel_action_button = self.tool_confirmation_panel.cancel_button

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(6)
        input_layout.addWidget(self.input_edit, 1)
        input_layout.addWidget(self.tool_confirmation_panel)
        input_layout.addWidget(self.voice_button)
        input_layout.addWidget(self.screenshot_button)
        self.input_bar.setLayout(input_layout)

        if self.music_plugin_enabled:
            self.music_lyrics_overlay = MusicLyricsOverlay(
                self,
                lyric_sync_offset_seconds=self.lyric_sync_offset_seconds,
                music_source=self.music_default_source,
            )
        self._ensure_music_sing_along_controller()

        self._apply_ui_theme(self.ui_theme)
        self._apply_fonts()
        self._load_reply_history_from_store()
        self._update_reply_history_buttons()
        self._install_portrait_drag_filters()
        for drag_widget in (self.bubble, self.name_label, self.speech_label):
            drag_widget.installEventFilter(self)

        self.portrait_controller.apply_current()
        if self._using_live2d:
            self._init_live2d_hover_ui()
            if self.stt_settings.enabled and hasattr(self, "voice_button"):
                self.voice_button.setToolTip(
                    "点击开始/结束录音；或长按安安说话，松手结束并识别"
                )
        else:
            self._sync_stage_height_for_layout()
            if (self.width(), self.height()) != self.stage_size:
                self.resize(*self.stage_size)
            self._layout_stage()
        self._create_tray_icon()
        self._move_to_default_position()
        if getattr(self, "startup_initializing", False):
            self._apply_startup_initializing_state()

        application = QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.close_external_tools)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._layout_stage()
        if self._is_ui_locked():
            apply_locked_window_region(self, True)

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        if self._is_ui_locked():
            apply_locked_window_region(self, True)

    def eventFilter(self, watched, event) -> bool:  # type: ignore[no-untyped-def]
        if isinstance(event, QMouseEvent) and self._using_live2d:
            input_overlay = self._live2d_input_overlay()
            live2d_widget = self._live2d_stage_widget()
            if watched is input_overlay or watched is live2d_widget:
                return False
        if self._live2d_hover_ui and event.type() in (
            QEvent.Type.Enter,
            QEvent.Type.Leave,
        ):
            if watched in self._ui_hover_targets():
                if event.type() == QEvent.Type.Enter:
                    self._enter_ui_hover_zone()
                else:
                    self._leave_ui_hover_zone()
                return False
        if watched is self.input_edit:
            if event.type() == QEvent.Type.KeyPress:
                self._log_input_key_event(event)
            return super().eventFilter(watched, event)
        if watched is self.screenshot_button and isinstance(event, QMouseEvent):
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.RightButton
            ):
                self._clear_manual_screen_observation()
                return True
            return super().eventFilter(watched, event)
        if isinstance(event, QMouseEvent) and self._is_drag_exempt_widget(watched):
            return super().eventFilter(watched, event)
        if isinstance(event, QMouseEvent):
            if event.type() == QEvent.Type.MouseButtonPress:
                return self._handle_mouse_press(event)
            if event.type() == QEvent.Type.MouseMove:
                return self._handle_mouse_move(event)
            if event.type() == QEvent.Type.MouseButtonRelease:
                return self._handle_mouse_release(event)
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._handle_mouse_press(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._handle_mouse_move(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._handle_mouse_release(event)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.close_external_tools()
        self._stop_napcat_bridge()
        super().closeEvent(event)

    @Slot()
    def close_external_tools(self) -> None:
        self.close_tts_tools()
        self.close_mcp_tools()
        self.close_plugins()
        self._stop_napcat_bridge()

    def _is_drag_exempt_widget(self, watched: QObject) -> bool:
        """输入栏按钮不走窗口拖动逻辑，否则 clicked 信号会被吞掉。"""
        exempt_widgets = (
            getattr(self, "voice_button", None),
            getattr(self, "screenshot_button", None),
            getattr(self, "input_edit", None),
            getattr(self, "confirm_action_button", None),
            getattr(self, "cancel_action_button", None),
            getattr(self, "reply_history_previous_button", None),
            getattr(self, "reply_history_next_button", None),
            getattr(self, "tool_confirmation_panel", None),
        )
        if watched in exempt_widgets:
            return True
        tool_panel = getattr(self, "tool_confirmation_panel", None)
        if tool_panel is not None and isinstance(watched, QWidget) and watched.parent() is tool_panel:
            return True
        return False

    @Slot()
    def close_tts_tools(self) -> None:
        providers = [self.tts_provider, *self.retired_tts_providers]
        self.retired_tts_providers = []
        seen: set[int] = set()
        for provider in providers:
            provider_id = id(provider)
            if provider_id in seen:
                continue
            seen.add(provider_id)
            close = getattr(provider, "close", None)
            if not callable(close):
                continue
            try:
                close()
            except Exception as exc:  # noqa: BLE001
                debug_log(
                    "TTS",
                    "关闭 TTS Provider 失败",
                    {"provider": type(provider).__name__, "error": str(exc)},
                )

    @Slot()
    def close_mcp_tools(self) -> None:
        if self.mcp_tool_provider is None:
            return
        self.mcp_tool_provider.close()
        self.mcp_tool_provider = None

    @Slot()
    def close_plugins(self) -> None:
        self.plugin_manager.shutdown_all()

    def _handle_mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._acquire_ui_controls("drag")
            event.accept()
            return True
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.position().toPoint())
            event.accept()
            return True
        return False

    def _handle_mouse_move(self, event: QMouseEvent) -> bool:
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
            return True
        return False

    def _handle_mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = None
            self._release_ui_controls("drag")
            event.accept()
            return True
        return False

    def _live2d_stage_widget(self) -> QWidget | None:
        if not self._using_live2d:
            return None
        controller = self.portrait_controller
        if not isinstance(controller, Live2DPortraitController):
            return None
        return controller.live2d_widget

    def _live2d_input_overlay(self) -> QWidget | None:
        if not self._using_live2d:
            return None
        controller = self.portrait_controller
        if not isinstance(controller, Live2DPortraitController):
            return None
        return controller.input_overlay

    def _handle_live2d_portrait_mouse(self, event: QMouseEvent) -> bool:
        event_type = event.type()
        if event_type == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                self._show_context_menu(event.position().toPoint())
                event.accept()
                return True
            if event.button() == Qt.MouseButton.LeftButton:
                return self._handle_mouse_press(event)
            return False
        if event_type == QEvent.Type.MouseMove:
            return self._handle_mouse_move(event)
        if (
            event_type == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            return self._handle_mouse_release(event)
        return False

    def _trigger_live2d_tap(self, local_pos: QPointF) -> None:
        controller = self.portrait_controller
        if isinstance(controller, Live2DPortraitController):
            controller.trigger_tap(local_pos.x(), local_pos.y())

    def _apply_reply_segment(self, segment: ChatSegment) -> None:
        controller = self.portrait_controller
        if isinstance(controller, Live2DPortraitController):
            controller.begin_speech_segment()
            controller.attach_speech_audio(None)
        self.portrait_controller.apply_for_segment(segment)
        self._sync_reply_history_index_for_segment(segment)

    def _end_live2d_speech(self) -> None:
        controller = self.portrait_controller
        if isinstance(controller, Live2DPortraitController):
            controller.end_speech()

    def _finish_reply_interaction(self) -> None:
        self._pending_napcat_voice_message = None
        self._end_live2d_speech()
        self._end_interaction("reply_completed")

    def _on_reply_segment_completed(self, segment: ChatSegment) -> None:
        self._forward_segment_voice_to_qq(segment)
        self._record_assistant_segment_note(segment)
        self._archive_segment_audio_to_history(segment)

    def _record_assistant_segment_note(self, segment: ChatSegment) -> None:
        text = segment.display_text(self.subtitle_language).strip()
        if not text:
            return
        notes_dir = self.base_dir / "data" / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        note_path = notes_dir / f"{self.character_profile.id}-台词.txt"
        tone = (segment.tone or "中性").strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        block = f"\n[{timestamp}] （{tone}）\n{text}\n"
        try:
            with note_path.open("a", encoding="utf-8") as handle:
                handle.write(block)
        except OSError as exc:
            debug_log("PetWindow", "台词笔记写入失败", {"path": str(note_path), "error": str(exc)})

    def _archive_segment_audio_to_history(self, segment: ChatSegment) -> None:
        audio_path = self._active_segment_audio_path
        if not audio_path:
            return
        source = Path(audio_path)
        self._active_segment_audio_path = None
        if not source.exists():
            return
        try:
            relative_path = archive_chat_audio(
                source,
                self.base_dir,
                self.character_profile.id,
            )
            attached = self.history_store.attach_audio_to_latest_matching_assistant(
                segment.text,
                segment.translation,
                segment.tone,
                segment.portrait,
                relative_path,
            )
            debug_log(
                "History",
                "归档分段语音",
                {
                    "attached": attached,
                    "audio_path": relative_path,
                    "text": segment.text,
                },
            )
            history_window = getattr(self, "history_window", None)
            if (
                attached
                and history_window is not None
                and history_window.isVisible()
            ):
                history_window.refresh()
        except OSError as exc:
            print(f"[History] 语音归档失败：{exc}")
            debug_log(
                "History",
                "语音归档失败",
                {"audio_path": audio_path, "error": str(exc)},
            )

    def _remember_reply_history_segments(self, segments: list[ChatSegment]) -> None:
        clean_segments = [segment for segment in segments if segment.text.strip()]
        if not clean_segments:
            return
        self.reply_history_segments.extend(clean_segments)
        if self.reply_history_index is None:
            self.reply_history_index = len(self.reply_history_segments) - 1
        self._update_reply_history_buttons()

    def _load_reply_history_from_store(self) -> None:
        try:
            entries = self.history_store.load()
        except OSError as exc:
            print(f"[History] 回溯历史读取失败：{exc}")
            debug_log("History", "回溯历史读取失败", {"error": str(exc)})
            entries = []
        self.reply_history_segments = _reply_history_segments_from_entries(entries)
        self.reply_history_index = (
            len(self.reply_history_segments) - 1
            if self.reply_history_segments
            else None
        )
        self.reply_history_review_active = False
        self._update_reply_history_buttons()

    def _sync_reply_history_index_for_segment(self, segment: ChatSegment) -> None:
        for index in range(len(self.reply_history_segments) - 1, -1, -1):
            if self.reply_history_segments[index] is segment:
                self.reply_history_index = index
                self.reply_history_review_active = False
                self._update_reply_history_buttons()
                return
        for index in range(len(self.reply_history_segments) - 1, -1, -1):
            if self.reply_history_segments[index] == segment:
                self.reply_history_index = index
                self.reply_history_review_active = False
                self._update_reply_history_buttons()
                return

    @Slot()
    def _show_previous_reply_history(self) -> None:
        index = self._normalized_reply_history_index()
        if index is None:
            return
        self._show_reply_history_at(index - 1)

    @Slot()
    def _show_next_reply_history(self) -> None:
        index = self._normalized_reply_history_index()
        if index is None:
            return
        self._show_reply_history_at(index + 1)

    def _show_reply_history_at(self, index: int) -> None:
        if not self._can_review_reply_history():
            return
        if index < 0 or index >= len(self.reply_history_segments):
            return

        segment = self.reply_history_segments[index]
        self.reply_history_index = index
        self.reply_history_review_active = True
        self.portrait_controller.apply_for_segment(segment)
        self.subtitle_controller.show_text_immediately(segment.display_text(self.subtitle_language))
        self._log_interaction_stage(
            "reply_history_reviewed",
            {"index": index, "history_count": len(self.reply_history_segments)},
        )
        self._update_reply_history_buttons()

    def _exit_reply_history_review(self, *, update_buttons: bool = True) -> None:
        self.reply_history_review_active = False
        if update_buttons:
            self._update_reply_history_buttons()

    def _refresh_reply_history_review_text(self) -> bool:
        if not self.reply_history_review_active:
            return False
        index = self._normalized_reply_history_index()
        if index is None:
            return False
        segment = self.reply_history_segments[index]
        self.subtitle_controller.show_text_immediately(segment.display_text(self.subtitle_language))
        return True

    def _normalized_reply_history_index(self) -> int | None:
        segments = getattr(self, "reply_history_segments", [])
        if not segments:
            if hasattr(self, "reply_history_index"):
                self.reply_history_index = None
            return None
        if getattr(self, "reply_history_index", None) is None:
            self.reply_history_index = len(segments) - 1
        else:
            self.reply_history_index = max(
                0,
                min(self.reply_history_index, len(segments) - 1),
            )
        return self.reply_history_index

    def _can_review_reply_history(self) -> bool:
        if len(getattr(self, "reply_history_segments", [])) < 2:
            return False
        if getattr(self, "worker_thread", None) is not None:
            return False
        subtitle_controller = getattr(self, "subtitle_controller", None)
        if (
            subtitle_controller is not None
            and hasattr(subtitle_controller, "is_reply_sequence_active")
            and subtitle_controller.is_reply_sequence_active()
        ):
            return False
        return True

    def _update_reply_history_buttons(self) -> None:
        previous_button = getattr(self, "reply_history_previous_button", None)
        next_button = getattr(self, "reply_history_next_button", None)
        if previous_button is None or next_button is None:
            return

        index = self._normalized_reply_history_index()
        can_review = self._can_review_reply_history()
        previous_button.setEnabled(can_review and index is not None and index > 0)
        next_button.setEnabled(
            can_review
            and index is not None
            and index < len(getattr(self, "reply_history_segments", [])) - 1
        )

    def _raise_foreground_controls(self) -> None:
        self.bubble.raise_()
        if self.music_lyrics_overlay is not None and self.music_plugin_enabled:
            self.music_lyrics_overlay.raise_()
        self.input_backdrop.raise_()
        self.input_bar.raise_()

    def _resolve_tray_icon(self) -> QIcon:
        icon = load_tray_icon(self.base_dir)
        if icon is not None:
            return icon
        pixmap = self.portrait_controller.pixmap
        return QIcon(pixmap) if not pixmap.isNull() else QIcon()

    def _apply_tray_icon(self) -> None:
        if hasattr(self, "tray_icon"):
            self.tray_icon.setIcon(self._resolve_tray_icon())

    def _apply_fonts(self) -> None:
        text_font = _rounded_chinese_font(13, QFont.Weight.Bold)
        name_font = _rounded_japanese_font(10, QFont.Weight.Bold)
        button_font = _rounded_chinese_font(11, QFont.Weight.ExtraBold)

        self.name_label.setFont(name_font)
        self._apply_speech_font()
        self.input_edit.setFont(text_font)
        self.screenshot_button.setFont(button_font)
        self.voice_button.setFont(button_font)

    def _apply_ui_theme(self, ui_theme: str) -> None:
        self.ui_theme = ui_theme
        self.setStyleSheet(build_pet_window_stylesheet(ui_theme))
        if self.history_window is not None:
            self.history_window.set_ui_theme(ui_theme)

    def _apply_speech_font(self) -> None:
        if self.subtitle_language == SUBTITLE_LANGUAGE_ZH:
            self.speech_label.setFont(_rounded_chinese_font(13, QFont.Weight.Medium))
            return
        self.speech_label.setFont(_rounded_japanese_font(13, QFont.Weight.Medium))

    def _init_live2d_hover_ui(self) -> None:
        self._live2d_hover_ui = bool(self.hover_only_ui_enabled)
        if not self._live2d_hover_ui:
            self.bubble.show()
            self.input_bar.show()
            self.input_backdrop.show()
            self._layout_stage()
            return
        self._ui_controls_holds = set()
        self._ui_hover_count = 0
        self._ui_controls_visible_applied = False
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        if (self.width(), self.height()) != self.stage_size:
            self.resize(*self.stage_size)
        self.bubble.hide()
        self.input_bar.hide()
        self.input_backdrop.hide()
        for widget in self._ui_hover_targets():
            widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            widget.installEventFilter(self)
        self._layout_stage()

    def _ui_hover_targets(self) -> tuple[QWidget, ...]:
        targets: list[QWidget] = [self]
        if isinstance(self.portrait_controller, Live2DPortraitController):
            targets.append(self.portrait_controller.input_overlay)
        if self._ui_controls_visible():
            targets.extend(
                [
                    self.bubble,
                    self.name_label,
                    self.speech_label,
                    self.reply_history_panel,
                    self.input_bar,
                    self.input_edit,
                    self.voice_button,
                    self.screenshot_button,
                ]
            )
        return tuple(targets)

    def _ui_controls_visible(self) -> bool:
        return bool(self._ui_controls_holds)

    def _is_ui_locked(self) -> bool:
        return bool(getattr(self, "ui_locked", False))

    def _set_ui_locked(self, locked: bool) -> None:
        locked = bool(locked)
        if self._is_ui_locked() == locked:
            return
        self.ui_locked = locked
        self._ui_hover_leave_timer.stop()
        self._ui_hover_count = 0
        self._ui_controls_holds.clear()
        if locked:
            self.bubble.hide()
            self.input_bar.hide()
            self.input_backdrop.hide()
        elif self._live2d_hover_ui:
            self._apply_ui_controls_visibility(force=True)
        else:
            self.bubble.show()
            self.input_bar.show()
            self.input_backdrop.show()
        self._layout_stage()
        self._apply_mouse_passthrough(locked)
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())

    def _apply_mouse_passthrough(self, locked: bool) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        apply_locked_mouse_transparency(self, locked)
        apply_locked_window_region(self, locked)
        if locked:
            QTimer.singleShot(0, lambda: apply_locked_window_region(self, True))
            QTimer.singleShot(100, lambda: apply_locked_window_region(self, True))

    def _toggle_ui_locked(self, checked: bool) -> None:
        self._set_ui_locked(checked)

    def _acquire_ui_controls(self, token: str) -> None:
        if self._is_ui_locked() or not self._live2d_hover_ui:
            return
        self._ui_hover_leave_timer.stop()
        if token not in self._ui_controls_holds:
            self._ui_controls_holds.add(token)
            self._apply_ui_controls_visibility()

    def _release_ui_controls(self, token: str) -> None:
        if not self._live2d_hover_ui:
            return
        if token not in self._ui_controls_holds:
            return
        self._ui_controls_holds.discard(token)
        self._apply_ui_controls_visibility()

    def _enter_ui_hover_zone(self) -> None:
        if self._is_ui_locked():
            return
        self._ui_hover_leave_timer.stop()
        self._ui_hover_count += 1
        if self._ui_hover_count == 1:
            self._acquire_ui_controls("hover")

    def _leave_ui_hover_zone(self) -> None:
        self._ui_hover_count = max(0, self._ui_hover_count - 1)
        if self._ui_hover_count == 0:
            self._ui_hover_leave_timer.start(450)

    def _finalize_ui_hover_release(self) -> None:
        self._ui_hover_count = 0
        self._release_ui_controls("hover")

    def _apply_ui_controls_visibility(self, *, force: bool = False) -> None:
        if not self._live2d_hover_ui:
            return
        if self._is_ui_locked():
            self._ui_controls_visible_applied = False
            self.bubble.hide()
            self.input_bar.hide()
            self.input_backdrop.hide()
            self._layout_stage()
            return
        visible = self._ui_controls_visible()
        if not force and visible == self._ui_controls_visible_applied:
            return
        self._ui_controls_visible_applied = visible
        self.portrait_controller.portrait_stage_widget.show()
        if visible:
            self.bubble.show()
            self.input_bar.show()
            self.input_backdrop.show()
        else:
            self.bubble.hide()
            self.input_bar.hide()
            self.input_backdrop.hide()
        if visible:
            for widget in (
                self.input_bar,
                self.input_edit,
                self.voice_button,
                self.screenshot_button,
            ):
                widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
                widget.installEventFilter(self)
        self._update_proactive_care_hint()
        self._layout_stage()

    def _layout_music_lyrics_overlay(
        self,
        *,
        portrait_x: int,
        portrait_y: int,
        portrait_width: int,
        portrait_height: int,
    ) -> None:
        overlay = self.music_lyrics_overlay
        if overlay is None or not self.music_plugin_enabled:
            if overlay is not None:
                overlay.hide()
            return
        overlay_width = max(120, portrait_width - 24)
        overlay_height = LYRICS_OVERLAY_HEIGHT
        overlay_x = portrait_x + (portrait_width - overlay_width) // 2
        overlay_y = portrait_y + portrait_height - overlay_height - LYRICS_OVERLAY_BOTTOM_INSET
        overlay.setGeometry(QRect(overlay_x, overlay_y, overlay_width, overlay_height))
        overlay.raise_()

    def _layout_stage(self) -> None:
        width = self.width()
        height = self.height()
        controls_visible = not self._live2d_hover_ui or self._ui_controls_visible()

        portrait_width, portrait_height = self.portrait_controller.portrait_stage_size
        portrait_y = max(0, height - portrait_height - STAGE_BOTTOM_INSET)
        portrait_x = (width - portrait_width) // 2
        self._portrait_hit_rect = QRect(portrait_x, portrait_y, portrait_width, portrait_height)
        if isinstance(self.portrait_controller, Live2DPortraitController):
            live2d_controller = self.portrait_controller
            live2d_controller.live2d_widget.move(portrait_x, portrait_y)
            live2d_controller.input_overlay.move(portrait_x, portrait_y)
            live2d_controller.input_overlay.setFixedSize(portrait_width, portrait_height)
            live2d_controller.live2d_widget.lower()
            live2d_controller.input_overlay.raise_()
        else:
            portrait_widget = self.portrait_controller.portrait_stage_widget
            portrait_widget.move(portrait_x, portrait_y)
            transition_width = self.portrait_transition_label.width()
            transition_height = self.portrait_transition_label.height()
            self.portrait_transition_label.move(
                (width - transition_width) // 2,
                max(0, height - transition_height - STAGE_BOTTOM_INSET),
            )
            portrait_widget.raise_()

        self._layout_music_lyrics_overlay(
            portrait_x=portrait_x,
            portrait_y=portrait_y,
            portrait_width=portrait_width,
            portrait_height=portrait_height,
        )
        if isinstance(self.portrait_controller, Live2DPortraitController):
            ctrl = self.portrait_controller
            ctrl.live2d_widget.lower()
            ctrl.input_overlay.raise_()

        if not controls_visible:
            return

        bubble_width = _bubble_layout_width(width, self.panel_width_percent)
        bubble_x = (width - bubble_width) // 2
        bubble_y = (
            height
            - BUBBLE_HEIGHT
            - INPUT_BAR_HEIGHT
            - INPUT_ABOVE_BUBBLE_GAP
            - BUBBLE_TOP_GAP
        )
        self.bubble.setGeometry(QRect(bubble_x, bubble_y, bubble_width, BUBBLE_HEIGHT))
        self.bubble.raise_()

        input_y = bubble_y + BUBBLE_HEIGHT + INPUT_ABOVE_BUBBLE_GAP
        self.input_bar.setGeometry(QRect(bubble_x, input_y, bubble_width, INPUT_BAR_HEIGHT))
        self._update_input_backdrop_geometry()
        self.input_bar.raise_()

    def _update_input_backdrop_geometry(self) -> None:
        self.input_bar.layout().activate()
        input_top_left = self.input_edit.mapTo(self, QPoint(0, 0))
        self.input_backdrop.setGeometry(QRect(input_top_left, self.input_edit.size()))
        self.input_backdrop.raise_()
        self.input_backdrop.update()

    def _create_tray_icon(self) -> None:
        self.tray_icon = QSystemTrayIcon(self._resolve_tray_icon(), self)
        self.tray_icon.setToolTip(self.character_profile.display_name)
        self.tray_icon.setContextMenu(self._build_menu())
        self.tray_icon.activated.connect(self._handle_tray_activated)
        self.tray_icon.show()

    def _build_menu(self) -> QMenu:
        menu = build_pet_tray_menu(
            self,
            chinese_subtitles_checked=self.subtitle_language == SUBTITLE_LANGUAGE_ZH,
            free_access_checked=self.free_access_enabled,
            ui_locked_checked=self.ui_locked,
            interactions_enabled=not getattr(self, "startup_initializing", False),
            on_hide=self.hide,
            on_toggle_chinese_subtitles=self._toggle_chinese_subtitles,
            on_toggle_free_access=self._toggle_free_access,
            on_toggle_ui_locked=self._toggle_ui_locked,
            on_show_history=self.show_history,
            on_show_settings=self.show_settings,
            on_show_napcat_console=self.show_napcat_console,
            on_restart=self._confirm_restart_application,
        )
        if self._using_live2d:
            self._append_live2d_expression_menu(menu)
        return menu

    def _append_live2d_expression_menu(self, menu: QMenu) -> None:
        quit_action: QAction | None = None
        for action in menu.actions():
            if action.text() == "退出":
                quit_action = action
                break

        expression_menu = QMenu("选择表情", menu)
        controller = self.portrait_controller
        if not isinstance(controller, Live2DPortraitController):
            placeholder = QAction("（非 Live2D 模式）", menu)
            placeholder.setEnabled(False)
            expression_menu.addAction(placeholder)
        else:
            widget = controller.live2d_widget
            expression_ids = widget.list_expression_ids()
            current = controller.current_expression
            ready = widget.is_ready()
            if not expression_ids:
                placeholder = QAction("（未找到表情文件 *.exp3.json）", menu)
                placeholder.setEnabled(False)
                expression_menu.addAction(placeholder)
            else:
                if not ready:
                    status = QAction("（Live2D 加载中，可先选表情）", menu)
                    status.setEnabled(False)
                    expression_menu.addAction(status)
                    expression_menu.addSeparator()
                for expression_id in expression_ids:
                    action = QAction(expression_id, menu)
                    action.setCheckable(True)
                    action.setChecked(expression_id == current)
                    action.triggered.connect(
                        lambda _checked=False, eid=expression_id: self._select_live2d_expression(eid)
                    )
                    expression_menu.addAction(action)

        if quit_action is not None:
            menu.insertSeparator(quit_action)
            menu.insertMenu(quit_action, expression_menu)
        else:
            menu.addSeparator()
            menu.addMenu(expression_menu)

    def _select_live2d_expression(self, expression_id: str) -> None:
        controller = self.portrait_controller
        if not isinstance(controller, Live2DPortraitController):
            return
        if not controller.apply_expression(expression_id):
            QMessageBox.warning(
                self,
                "表情切换失败",
                f"未找到表情「{expression_id}」，请检查模型目录中的 .exp3.json 文件。",
            )
            return
        debug_log("Live2D", "菜单切换表情", {"expression": expression_id})

    @Slot()
    def _confirm_restart_application(self) -> None:
        answer = QMessageBox.question(
            self,
            "重启 Mutsuki",
            "将重新启动 Mutsuki（未保存的设置请先保存）。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        from app.ui.restart import request_app_restart

        request_app_restart(parent=self, base_dir=self.base_dir)

    def _show_context_menu(self, position: QPoint) -> None:
        _ = position
        self._build_menu().exec(QCursor.pos())

    def _handle_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def _move_to_default_position(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.right() - self.width() - 40
        y = geometry.bottom() - self.height() - 20
        self.move(max(geometry.left(), x), max(geometry.top(), y))

    def _begin_interaction(self, source: str) -> None:
        self.interaction_sequence += 1
        now = time.perf_counter()
        self.active_interaction_id = f"interaction-{self.interaction_sequence}"
        self.active_interaction_started_at = now
        self.active_interaction_last_at = now
        debug_log(
            "Latency",
            "输入事件开始",
            {
                "interaction_id": self.active_interaction_id,
                "source": source,
                "input_chars": len(self.input_edit.text()),
                "worker_busy": self.worker_thread is not None,
            },
        )

    def _log_input_key_event(self, event: object) -> None:
        self._mark_user_activity()
        key_event = event if isinstance(event, QKeyEvent) else None
        debug_log(
            "Input",
            "输入框按键事件",
            {
                "key": int(key_event.key()) if key_event is not None else "",
                "text": key_event.text() if key_event is not None else "",
                "modifiers": str(key_event.modifiers()) if key_event is not None else "",
                "input_chars": len(self.input_edit.text()),
                "worker_busy": self.worker_thread is not None,
            },
        )

    def _log_interaction_stage(self, stage: str, data: dict[str, Any] | None = None) -> None:
        if not self.active_interaction_id or self.active_interaction_started_at is None:
            return
        now = time.perf_counter()
        previous = self.active_interaction_last_at or self.active_interaction_started_at
        self.active_interaction_last_at = now
        payload: dict[str, Any] = {
            "interaction_id": self.active_interaction_id,
            "stage": stage,
            "elapsed_ms": int((now - self.active_interaction_started_at) * 1000),
            "delta_ms": int((now - previous) * 1000),
        }
        if data:
            payload.update(data)
        debug_log("Latency", "交互阶段", payload)

    def _end_interaction(self, outcome: str) -> None:
        self._log_interaction_stage("interaction_finished", {"outcome": outcome})
        self.active_interaction_id = ""
        self.active_interaction_started_at = None
        self.active_interaction_last_at = None
        self._update_reply_history_buttons()
        # 每完成一轮对话（含完整回复）累计一次，驱动自动记忆整理触发
        if outcome == "reply_completed":
            self._finish_active_reminder_delivery()
            self._record_completed_memory_turn()

    def _mark_user_activity(self) -> None:
        self.last_user_activity_at = time.perf_counter()
        self._update_proactive_care_hint()

    @Slot()
    def _handle_return_pressed(self) -> None:
        if getattr(self, "startup_initializing", False):
            return
        self._begin_interaction("return_pressed")
        self.send_message("return_pressed")

    def _voice_input_available(self) -> bool:
        return self._voice_unavailable_reason() is None

    def _voice_unavailable_reason(self) -> str | None:
        if not self.stt_settings.enabled:
            return "语音输入已在设置中关闭。"
        if getattr(self, "startup_initializing", False):
            return "应用仍在初始化，请稍候再试。"
        if self._voice_transcribe_thread is not None:
            return "正在识别上一条语音，请稍候。"
        if self.worker_thread is not None:
            return "正在处理上一条消息，请稍后再用语音输入。"
        return None

    @Slot()
    def _on_live2d_long_press_start(self) -> None:
        self._mark_user_activity()
        if not self._voice_input_available():
            return
        if self._voice_recording or self._voice_rec_starting:
            return
        self._voice_from_long_press = True
        self._start_voice_recording()

    def _on_live2d_long_press_end(self) -> None:
        if not self._voice_from_long_press:
            return
        self._voice_from_long_press = False
        if self._voice_recording:
            self._stop_voice_recording()
            return
        if self._voice_rec_starting:
            self._voice_long_press_cancel_pending = True

    def _handle_voice_button_clicked(self) -> None:
        self._mark_user_activity()
        if not self._voice_input_available():
            reason = self._voice_unavailable_reason()
            if reason:
                self.set_speech(reason)
            return
        if self._voice_recording:
            self._stop_voice_recording()
            return
        if self._voice_rec_starting or self._voice_transcribe_thread is not None:
            return
        self._start_voice_recording()

    def _start_voice_recording(self) -> None:
        self._voice_rec_starting = True
        self._update_voice_button()
        worker = StartRecordingWorker(self)
        self._voice_rec_worker = worker
        worker.finished.connect(self._on_voice_recording_started)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._clear_voice_rec_thread)
        worker.start()

    @Slot(bool, str)
    def _on_voice_recording_started(self, ok: bool, message: str) -> None:
        self._voice_rec_starting = False
        if self._voice_long_press_cancel_pending:
            self._voice_long_press_cancel_pending = False
            if ok:
                self._voice_recording = True
                self._update_voice_button()
                self._stop_voice_recording()
            else:
                self._update_voice_button()
            return
        if not ok:
            if self._voice_recording:
                try:
                    audio_io.stop_recording()
                except audio_io.AudioIOError:
                    pass
                self._voice_recording = False
            self._update_voice_button()
            QMessageBox.warning(self, "录音失败", message or "无法打开麦克风")
            return
        self._voice_recording = True
        self._update_voice_button()
        self.set_speech("录音中…")

    def _stop_voice_recording(self) -> None:
        if not self._voice_recording:
            return
        self._voice_from_long_press = False
        self._voice_recording = False
        self._update_voice_button()
        self.set_speech("正在识别…")
        worker = StopRecordTranscribeWorker(self.stt_settings, self)
        self._voice_transcribe_worker = worker
        self._voice_transcribe_thread = worker
        worker.status.connect(self.set_speech)
        worker.finished.connect(self._on_voice_transcribe_finished)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._clear_voice_transcribe_thread)
        worker.start()
        self._set_busy(True)

    @Slot(object)
    def _on_voice_transcribe_finished(self, result: VoiceTranscribeResult) -> None:
        self._set_busy(self.worker_thread is not None)
        if not result.success:
            self.subtitle_controller.cancel_reply_flow(self.character_profile.initial_message)
            QMessageBox.warning(self, "语音识别失败", result.error_message or "识别失败")
            return
        self.input_edit.setText(result.text)
        self.input_edit.setFocus()
        self.set_speech(self.character_profile.initial_message)
        self._begin_interaction("voice_input")
        self.send_message("voice_input")

    def _update_voice_button(self) -> None:
        if not hasattr(self, "voice_button"):
            return
        recording = self._voice_recording or self._voice_rec_starting
        self.voice_button.setText("录音中" if recording else "语音")
        self.voice_button.setProperty("recording", recording)
        self.voice_button.style().unpolish(self.voice_button)
        self.voice_button.style().polish(self.voice_button)
        self.voice_button.update()

    def _clear_voice_rec_thread(self) -> None:
        self._voice_rec_worker = None

    def _clear_voice_transcribe_thread(self) -> None:
        self._voice_transcribe_thread = None
        self._voice_transcribe_worker = None
        self._set_busy(self.worker_thread is not None)

    @Slot()
    def _handle_screenshot_button_clicked(self) -> None:
        self._mark_user_activity()
        if getattr(self, "startup_initializing", False):
            return
        if self.worker_thread is not None:
            return
        if not self.screen_observation_enabled:
            QMessageBox.information(self, "截图已关闭", "请先在设置中开启屏幕观察权限。")
            return

        debug_log("PetWindow", "开始手动框选截图")
        QTimer.singleShot(120, self._show_manual_screenshot_overlay)

    def _show_manual_screenshot_overlay(self) -> None:
        try:
            desktop_pixmap, virtual_geometry = self._capture_virtual_desktop_pixmap()
        except RuntimeError as exc:
            QMessageBox.warning(self, "截图失败", str(exc))
            debug_log("PetWindow", "手动框选截图启动失败", {"error": str(exc)})
            return

        overlay = ManualScreenshotOverlay(desktop_pixmap, virtual_geometry)
        overlay.selected.connect(self._handle_manual_screenshot_selected)
        overlay.cancelled.connect(self._handle_manual_screenshot_cancelled)
        overlay.destroyed.connect(self._clear_manual_screenshot_overlay_ref)
        self.manual_screenshot_overlay = overlay
        overlay.show()
        overlay.raise_()
        overlay.activateWindow()

    def _capture_virtual_desktop_pixmap(self) -> tuple[QPixmap, QRect]:
        return capture_virtual_desktop_pixmap()

    @Slot(object)
    def _handle_manual_screenshot_selected(self, pixmap: QPixmap) -> None:
        self.show()
        self.raise_()
        try:
            observation = build_screen_observation_from_pixmap(pixmap)
        except RuntimeError as exc:
            QMessageBox.warning(self, "截图失败", str(exc))
            debug_log("PetWindow", "手动框选截图编码失败", {"error": str(exc)})
            return

        self.pending_manual_screen_observation = observation
        self._update_manual_screenshot_button()
        debug_log(
            "PetWindow",
            "手动框选截图已附加到下一条消息",
            {
                "width": observation.width,
                "height": observation.height,
                "captured_at": observation.captured_at,
                "screen_name": observation.screen_name,
                "image": observation.data_url,
            },
        )

    @Slot()
    def _handle_manual_screenshot_cancelled(self) -> None:
        self.show()
        self.raise_()
        debug_log("PetWindow", "手动框选截图已取消")

    @Slot()
    def _clear_manual_screenshot_overlay_ref(self) -> None:
        self.manual_screenshot_overlay = None

    def _clear_manual_screen_observation(self) -> None:
        if self.pending_manual_screen_observation is None:
            return
        self.pending_manual_screen_observation = None
        self._update_manual_screenshot_button()
        debug_log("PetWindow", "待发送手动截图已清除")

    def _update_manual_screenshot_button(self) -> None:
        attached = self.pending_manual_screen_observation is not None
        self.screenshot_button.setText("截图✓" if attached else "截图")
        self.screenshot_button.setProperty("screenshotAttached", attached)
        self.screenshot_button.style().unpolish(self.screenshot_button)
        self.screenshot_button.style().polish(self.screenshot_button)
        self.screenshot_button.update()

    @Slot()
    def send_message(self, source: str = "direct_call") -> None:
        if getattr(self, "startup_initializing", False):
            return
        text = self.input_edit.text().strip()
        manual_observation = self.pending_manual_screen_observation
        self._mark_user_activity()
        if not self.active_interaction_id:
            self._begin_interaction(source)
        self._log_interaction_stage(
            "send_message_enter",
            {
                "source": source,
                "text": text,
                "has_manual_screenshot": manual_observation is not None,
                "worker_busy": self.worker_thread is not None,
            },
        )
        if (not text and manual_observation is None) or self.worker_thread is not None:
            debug_log(
                "PetWindow",
                "发送消息被忽略",
                {
                    "has_text": bool(text),
                    "has_manual_screenshot": manual_observation is not None,
                    "worker_busy": self.worker_thread is not None,
                },
            )
            self._log_interaction_stage(
                "send_message_ignored",
                {
                    "has_text": bool(text),
                    "has_manual_screenshot": manual_observation is not None,
                    "worker_busy": self.worker_thread is not None,
                },
            )
            self._end_interaction("ignored")
            return
        if manual_observation is not None and not self.screen_observation_enabled:
            QMessageBox.information(self, "截图已关闭", "屏幕观察权限已关闭，本次截图不会发送。")
            self._clear_manual_screen_observation()
            self._end_interaction("ignored")
            return

        if not text and manual_observation is not None:
            text = MANUAL_SCREENSHOT_DEFAULT_TEXT

        outbound_target: NapCatInboundMessage | None = None
        outbound_directive = parse_outbound_directive(text) if text else None
        if outbound_directive is not None:
            bridge = getattr(self, "napcat_bridge", None)
            if bridge is None:
                QMessageBox.information(
                    self,
                    "QQ",
                    "QQ 接入未启用，无法使用 @收件人 发送。",
                )
                self._end_interaction("ignored")
                return
            outbound_target = bridge.resolve_outbound_recipient(outbound_directive.recipient)
            if outbound_target is None:
                known_names = bridge.known_contact_names()
                hint = "、".join(known_names[:5]) if known_names else "暂无，可先让对方发一条消息"
                QMessageBox.warning(
                    self,
                    "QQ",
                    f"找不到收件人「{outbound_directive.recipient}」。\n"
                    f"可用昵称：{hint}\n"
                    "也可使用 @QQ号、@private:QQ号 或 @group:群号。",
                )
                self._end_interaction("ignored")
                return
            text = outbound_directive.text
            self._outbound_napcat_target = outbound_target
            self.subtitle_controller.show_text_immediately(
                format_outbound_pet_display(outbound_target, text)
            )

        self._set_pending_tool_action(None)
        exit_reply_history_review = getattr(self, "_exit_reply_history_review", None)
        if exit_reply_history_review is not None:
            exit_reply_history_review()
        self.input_edit.clear()
        self._log_interaction_stage("input_cleared")
        self.subtitle_controller.cancel_reply_flow("......")
        self._log_interaction_stage("placeholder_reply_shown")

        visual_observation_jobs: list[VisualObservationJob] = []
        if manual_observation is not None:
            visual_id = generate_visual_observation_id()
            request_user_message = build_screen_observation_user_message(text, manual_observation)
            recorded_user_text = append_manual_observation_marker(text, manual_observation, visual_id)
            visual_observation_jobs.append(
                VisualObservationJob(
                    id=visual_id,
                    source="manual_screenshot",
                    user_text=text,
                    observation=manual_observation,
                )
            )
        else:
            request_user_message: dict[str, Any] = {"role": "user", "content": text}
            recorded_user_text = text
            if outbound_target is not None:
                recorded_user_text = format_outbound_pet_display(outbound_target, text)

        if outbound_target is not None:
            bridge = getattr(self, "napcat_bridge", None)
            if bridge is None:
                self._outbound_napcat_target = None
                self._end_interaction("ignored")
                return
            request_messages = bridge.record_outbound_user_message(outbound_target, text)
        else:
            request_messages = _add_visual_context_to_messages(
                [*self.messages, request_user_message],
                user_text=text,
                store=getattr(self, "visual_observation_store", None),
                has_current_image=manual_observation is not None,
            )
            request_messages = trim_messages_for_model(request_messages)
        debug_log(
            "PetWindow",
            "用户消息入队",
            {
                "text": text,
                "has_manual_screenshot": manual_observation is not None,
                "history_messages": len(self.messages),
                "request_messages": summarize_messages(request_messages),
            },
        )
        self._log_interaction_stage(
            "request_messages_ready",
            {
                "history_messages": len(self.messages),
                "request_message_count": len(request_messages),
                "has_manual_screenshot": manual_observation is not None,
            },
        )
        self._record_user_message(recorded_user_text)
        self._clear_proactive_screen_context_batch("sent_user_message")
        if manual_observation is not None:
            self.pending_manual_screen_observation = None
            self._update_manual_screenshot_button()
        if visual_observation_jobs:
            self.pending_visual_observation_jobs = [
                *getattr(self, "pending_visual_observation_jobs", []),
                *visual_observation_jobs,
            ]
        self._log_interaction_stage("user_message_recorded")
        self._start_chat_worker(request_messages)

    def _start_chat_worker(self, request_messages: list[dict[str, Any]]) -> None:
        visual_observation_jobs = getattr(self, "pending_visual_observation_jobs", [])
        self.pending_visual_observation_jobs = []
        self._set_busy(True)
        self._log_interaction_stage("ui_busy_enabled")
        debug_log(
            "PetWindow",
            "启动聊天 Worker",
            {
                "message_count": len(request_messages),
                "messages": summarize_messages(request_messages),
            },
        )
        self.worker_thread = QThread(self)
        self.worker = ChatWorker(
            self.agent_runtime,
            request_messages,
            visual_observation_store=getattr(self, "visual_observation_store", None),
            visual_observation_jobs=visual_observation_jobs,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._handle_progress_reply)
        self.worker.finished.connect(self._handle_reply)
        self.worker.failed.connect(self._handle_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()
        self._log_interaction_stage("chat_worker_started")

    @Slot(object)
    def _handle_progress_reply(self, progress: AgentProgress) -> None:
        reply = progress.reply
        if not reply.text.strip():
            return
        self._log_interaction_stage(
            "agent_progress_received",
            {
                "stage": progress.stage,
                "segments": len(reply.segments),
                "metadata": progress.metadata,
            },
        )
        debug_log(
            "PetWindow",
            "收到 Agent 中间回复",
            {
                "stage": progress.stage,
                "segments": len(reply.segments),
                "metadata": progress.metadata,
            },
        )
        self.messages.append({"role": "assistant", "content": reply.text})
        self._record_assistant_reply_history(reply)
        if (
            reply.segments
            and reply.segments[0].text.strip()
            and not self.subtitle_controller.is_reply_sequence_active()
        ):
            self.voice_playback_controller.prepare_first_segment(reply.segments[0])

    @Slot(object)
    def _handle_reply(self, result: AgentResult) -> None:
        self._log_interaction_stage(
            "agent_result_received",
            {
                "segments": len(result.reply.segments),
                "actions": [action.type for action in result.actions],
            },
        )
        debug_log(
            "PetWindow",
            "收到 Agent 回复",
            {
                "segments": len(result.reply.segments),
                "actions": [action.type for action in result.actions],
            },
        )
        if self._queue_screen_observation_followup(result):
            self._log_interaction_stage("screen_observation_followup_queued")
            return
        reply = result.reply
        pending_napcat = self._pending_napcat_message
        outbound_napcat = self._outbound_napcat_target
        self._pending_napcat_message = None
        self._outbound_napcat_target = None
        self.messages.append({"role": "assistant", "content": reply.text})
        self._record_assistant_reply_history(reply, _debug=result._debug)
        self._log_interaction_stage("assistant_message_recorded")
        self._show_reply_segments(reply.segments)
        napcat_target = pending_napcat or outbound_napcat
        if napcat_target is not None:
            self._deliver_napcat_reply(napcat_target, result)
        self._apply_pending_action_from_result(result)

    def _queue_screen_observation_followup(self, result: AgentResult) -> bool:
        if not any(action.type == SCREEN_OBSERVATION_REQUEST_ACTION for action in result.actions):
            return False
        if (
            not self.screen_observation_enabled
            or not self.model_vision_enabled
            or not self.autonomous_screen_observation_enabled
        ):
            self._log_interaction_stage(
                "screen_observation_disabled",
                {
                    "screen_observation_enabled": self.screen_observation_enabled,
                    "model_vision_enabled": self.model_vision_enabled,
                    "autonomous_screen_observation_enabled": self.autonomous_screen_observation_enabled,
                },
            )
            debug_log(
                "PetWindow",
                "屏幕观察请求被禁用",
                {
                    "screen_observation_enabled": self.screen_observation_enabled,
                    "model_vision_enabled": self.model_vision_enabled,
                    "autonomous_screen_observation_enabled": self.autonomous_screen_observation_enabled,
                },
            )
            self._consume_agent_result(_build_screen_observation_disabled_result())
            return True
        user_message_index = _last_user_message_index(self.messages)
        if user_message_index is None:
            self._log_interaction_stage("screen_observation_missing_user_message")
            debug_log("PetWindow", "屏幕观察缺少可关联用户消息")
            self._consume_agent_result(_build_screen_observation_failed_result("缺少可关联的用户消息。"))
            return True

        text = str(self.messages[user_message_index].get("content", ""))
        self.screen_observation_followup_in_progress = True
        try:
            observation = capture_screen_observation(self)
        except RuntimeError as exc:
            self.screen_observation_followup_in_progress = False
            self._log_interaction_stage("screen_observation_failed", {"error": str(exc)})
            debug_log("PetWindow", "屏幕观察失败", {"error": str(exc)})
            self._consume_agent_result(_build_screen_observation_failed_result(str(exc)))
            return True

        visual_id = generate_visual_observation_id()
        observed_message = build_screen_observation_user_message(text, observation)
        self.messages[user_message_index] = {
            "role": "user",
            "content": append_observation_marker(text, observation, visual_id),
        }
        self._record_history("system", append_observation_marker("", observation, visual_id).strip())
        self.pending_visual_observation_jobs = [
            *getattr(self, "pending_visual_observation_jobs", []),
            VisualObservationJob(
                id=visual_id,
                source="autonomous_screen",
                user_text=text,
                observation=observation,
            ),
        ]
        # 截图消息包含 base64，必须作为本次 follow-up 的最后一条消息保留。
        # 中间进度回复已经展示给用户，不再放入这次入模上下文，避免字符裁剪丢掉截图。
        self.pending_screen_observation_messages = trim_messages_for_model(
            [*self.messages[:user_message_index], observed_message]
        )
        self.screen_observation_followup_in_progress = False
        debug_log(
            "PetWindow",
            "屏幕观察 follow-up 已排队",
            {
                "original_text": text,
                "width": observation.width,
                "height": observation.height,
                "captured_at": observation.captured_at,
                "screen_name": observation.screen_name,
                "image": observation.data_url,
                "message_count": len(self.pending_screen_observation_messages),
            },
        )
        self._log_interaction_stage(
            "screen_observation_captured",
            {
                "width": observation.width,
                "height": observation.height,
                "screen_name": observation.screen_name,
            },
        )
        return True

    def _queue_event_screen_observation_followup(
        self,
        result: AgentResult,
        event: AgentEvent | None,
        reminder_id: str | None,
    ) -> bool:
        screen_action = _first_screen_observation_request(result)
        if screen_action is None:
            return False
        if event is None or event.type != "proactive_check":
            self._consume_agent_result(_build_screen_observation_failed_result("缺少可关联的主动事件。"))
            return True
        if not self._proactive_screen_context_allowed():
            self._log_interaction_stage(
                "event_screen_observation_disabled",
                {
                    "proactive_screen_context_enabled": (
                        self.proactive_care_settings.screen_context_enabled
                    ),
                },
            )
            self._consume_agent_result(_build_screen_observation_disabled_result())
            return True
        if isinstance(event.payload.get("screen_context"), dict) or isinstance(
            event.payload.get("screen_contexts"),
            list,
        ):
            self._consume_agent_result(_build_screen_observation_failed_result("本轮主动事件已经包含屏幕截图。"))
            return True

        reason = str(screen_action.payload.get("reason", "")).strip()
        self.screen_observation_followup_in_progress = True
        try:
            observation = capture_screen_observation(self)
        except RuntimeError as exc:
            self.screen_observation_followup_in_progress = False
            self._log_interaction_stage("event_screen_observation_failed", {"error": str(exc)})
            debug_log("PetWindow", "主动事件屏幕观察失败", {"error": str(exc)})
            self._consume_agent_result(_build_screen_observation_failed_result(str(exc)))
            return True

        payload = dict(event.payload)
        payload["screen_context"] = {
            "data_url": observation.data_url,
            "width": observation.width,
            "height": observation.height,
            "captured_at": observation.captured_at,
            "screen_name": observation.screen_name,
        }
        payload["screen_observation_requested_by_model"] = True
        payload["screen_observation_reason"] = reason
        self.pending_screen_observation_event = AgentEvent(type=event.type, payload=payload)
        self.pending_screen_observation_event_reminder_id = reminder_id
        self.screen_observation_followup_in_progress = False
        visual_id = generate_visual_observation_id()
        self.pending_event_visual_observation_jobs = [
            *getattr(self, "pending_event_visual_observation_jobs", []),
            VisualObservationJob(
                id=visual_id,
                source="autonomous_screen",
                user_text=reason,
                observation=observation,
            ),
        ]
        self._record_history("system", append_observation_marker("", observation, visual_id).strip())
        debug_log(
            "PetWindow",
            "主动事件屏幕观察 follow-up 已排队",
            {
                "event_type": event.type,
                "reason": reason,
                "width": observation.width,
                "height": observation.height,
                "captured_at": observation.captured_at,
                "screen_name": observation.screen_name,
                "image": observation.data_url,
            },
        )
        self._log_interaction_stage(
            "event_screen_observation_captured",
            {
                "width": observation.width,
                "height": observation.height,
                "screen_name": observation.screen_name,
            },
        )
        return True

    def _record_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self._record_history("user", text)

    @Slot()
    def confirm_pending_action(self) -> None:
        if self.pending_tool_action is None or self.worker_thread is not None:
            return
        self._mark_user_activity()
        self._begin_interaction("confirm_action_clicked")
        action = self.pending_tool_action
        self._log_interaction_stage("confirm_action", action.to_dict())
        self._set_pending_tool_action(None)
        self._clear_queued_reply_segments_for_action_resolution()
        self._run_action_worker(confirmed_action=action)

    @Slot()
    def cancel_pending_action(self) -> None:
        if self.pending_tool_action is None or self.worker_thread is not None:
            return
        self._mark_user_activity()
        self._begin_interaction("cancel_action_clicked")
        action = self.pending_tool_action
        self._log_interaction_stage("cancel_action", action.to_dict())
        self._set_pending_tool_action(None)
        self._clear_queued_reply_segments_for_action_resolution()
        self._run_action_worker(cancelled_action=action)

    def _run_action_worker(
        self,
        confirmed_action: PendingToolAction | None = None,
        cancelled_action: PendingToolAction | None = None,
    ) -> None:
        self._set_busy(True)
        self._log_interaction_stage(
            "action_worker_start",
            {
                "confirmed": confirmed_action.tool_name if confirmed_action is not None else "",
                "cancelled": cancelled_action.tool_name if cancelled_action is not None else "",
            },
        )
        self.worker_thread = QThread(self)
        self.worker = ChatWorker(
            self.agent_runtime,
            confirmed_action=confirmed_action,
            cancelled_action=cancelled_action,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._handle_progress_reply)
        self.worker.finished.connect(self._handle_action_reply)
        self.worker.failed.connect(self._handle_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()
        self._log_interaction_stage("action_worker_started")

    @Slot(object)
    def _handle_action_reply(self, result: AgentResult) -> None:
        self._log_interaction_stage(
            "action_result_received",
            {
                "segments": len(result.reply.segments),
                "actions": [action.type for action in result.actions],
            },
        )
        self._consume_agent_result(result)

    def _consume_agent_result(self, result: AgentResult, record_history: bool = True) -> None:
        reply = result.reply
        self._log_interaction_stage(
            "consume_agent_result",
            {
                "segments": len(reply.segments),
                "record_history": record_history,
            },
        )
        if record_history:
            self.messages.append({"role": "assistant", "content": reply.text})
            self._record_assistant_reply_history(reply, _debug=result._debug)
        self._show_reply_segments(reply.segments)
        self._apply_pending_action_from_result(result)

    def _apply_pending_action_from_result(self, result: AgentResult) -> None:
        for action in result.actions:
            if action.type != "pending_action":
                continue
            try:
                self._set_pending_tool_action(PendingToolAction.from_dict(action.payload))
            except ValueError as exc:
                print(f"[Tool] 待确认动作无效：{exc}")
            return
        self._set_pending_tool_action(None)

    def _set_pending_tool_action(self, action: PendingToolAction | None) -> None:
        self.pending_tool_action = action
        has_action = action is not None
        self.tool_confirmation_panel.set_action(action)
        self._update_input_backdrop_geometry()
        panel_state = self.tool_confirmation_panel.state_snapshot()
        debug_log(
            "PetWindow",
            "待确认动作 UI 状态已更新",
            {
                "has_action": has_action,
                "tool_name": action.tool_name if action is not None else "",
                **panel_state,
            },
        )

    def _clear_queued_reply_segments_for_action_resolution(self) -> None:
        self.subtitle_controller.clear_queued_reply_segments_for_action_resolution()

    @Slot()
    def _on_proactive_care_timer(self) -> None:
        self._update_proactive_care_hint()
        self._check_proactive_care()

    def _check_proactive_care(self) -> None:
        if getattr(self, "startup_initializing", False):
            return
        if not self._can_run_proactive_care():
            return

        now = time.perf_counter()
        if self._should_capture_proactive_screen_context(now):
            self._capture_proactive_screen_context(now)
        if not self._should_send_proactive_care_batch(now):
            return

        event = self._build_proactive_care_event(now)
        self.pending_event_visual_observation_jobs = [
            *getattr(self, "pending_event_visual_observation_jobs", []),
            *_build_proactive_visual_observation_jobs(event),
        ]
        self.last_proactive_care_at = now
        if self._proactive_screen_context_allowed() and self.proactive_screen_contexts:
            self._record_history("system", PROACTIVE_SCREEN_CONTEXT_HISTORY_MARKER)
        else:
            self._record_history("system", PROACTIVE_TOPIC_HISTORY_MARKER)
        self._clear_proactive_screen_context_batch("sent")
        self._run_event_worker(event)
        self._update_proactive_care_hint()

    def _default_input_placeholder(self) -> str:
        base = f"和{self.character_profile.display_name}说点什么..."
        if getattr(self, "napcat_bridge", None) is not None:
            return f"{base} 用 @昵称 或 @QQ号 发给QQ"
        return base

    def _proactive_care_countdown_seconds(self) -> int | None:
        return compute_proactive_care_countdown_seconds(
            settings=self.proactive_care_settings,
            now=time.perf_counter(),
            last_user_activity_at=self.last_user_activity_at,
            last_proactive_care_at=self.last_proactive_care_at,
            screen_context_allowed=self._proactive_screen_context_allowed(),
            screen_context_count=len(self.proactive_screen_contexts),
            screen_context_batch_started_at=self.proactive_screen_context_batch_started_at,
            last_proactive_screen_context_at=self.last_proactive_screen_context_at,
        )

    def _update_proactive_care_hint(self) -> None:
        countdown = self._proactive_care_countdown_seconds()
        display_name = self.character_profile.display_name
        if countdown is None or getattr(self, "startup_initializing", False):
            if hasattr(self, "tray_icon"):
                self.tray_icon.setToolTip(display_name)
            if hasattr(self, "input_edit"):
                self.input_edit.setPlaceholderText(self._default_input_placeholder())
            return

        hint = format_proactive_care_countdown_hint(countdown)
        if hasattr(self, "tray_icon"):
            self.tray_icon.setToolTip(f"{display_name}\n主动搭话：{hint}")
        if hasattr(self, "input_edit") and not self.input_edit.text().strip():
            self.input_edit.setPlaceholderText(f"{hint}…")

    def _can_run_proactive_care(self) -> bool:
        if not self._proactive_care_enabled():
            return False
        if (
            self.worker_thread is not None
            or self.active_reminder_id is not None
            or self.active_event_type
            or self.pending_tool_action is not None
            or self.pending_screen_observation_messages is not None
            or self.screen_observation_followup_in_progress
        ):
            return False
        if self.input_edit.text().strip() or self.speech_timer.isActive():
            return False
        subtitle_controller = getattr(self, "subtitle_controller", None)
        if subtitle_controller is not None and subtitle_controller.is_reply_sequence_active():
            return False
        if subtitle_controller is None and getattr(self, "current_segment_sequence_id", None) is not None and (
            not getattr(self, "current_segment_speech_done", True)
            or not getattr(self, "current_segment_tts_done", True)
        ):
            return False
        return True

    def _should_capture_proactive_screen_context(self, now: float) -> bool:
        check_interval_seconds = self.proactive_care_settings.check_interval_minutes * 60
        seconds_since_pet_interaction = now - self.last_user_activity_at
        if (
            seconds_since_pet_interaction + PROACTIVE_TIMER_DUE_GRACE_SECONDS
            < check_interval_seconds
        ):
            return False
        if self.last_proactive_screen_context_at is None:
            return True
        return (
            now - self.last_proactive_screen_context_at + PROACTIVE_TIMER_DUE_GRACE_SECONDS
            >= check_interval_seconds
        )

    def _capture_proactive_screen_context(self, now: float) -> None:
        self.last_proactive_screen_context_at = now
        try:
            observation = capture_screen_observation(self)
        except RuntimeError as exc:
            debug_log("ProactiveCare", "主动屏幕上下文获取失败", {"error": str(exc)})
            return

        context = {
            "data_url": observation.data_url,
            "width": observation.width,
            "height": observation.height,
            "captured_at": observation.captured_at,
            "screen_name": observation.screen_name,
        }
        if not self.proactive_screen_contexts:
            self.proactive_screen_context_batch_started_at = now
        self.proactive_screen_contexts.append(context)
        batch_limit = self.proactive_care_settings.normalized().screen_context_batch_limit
        while len(self.proactive_screen_contexts) > batch_limit:
            self.proactive_screen_contexts.pop(0)
            self.proactive_screen_context_dropped_count += 1
        debug_log(
            "ProactiveCare",
            "主动屏幕上下文已缓存",
            {
                "width": observation.width,
                "height": observation.height,
                "captured_at": observation.captured_at,
                "screen_name": observation.screen_name,
                "batch_count": len(self.proactive_screen_contexts),
                "dropped_count": self.proactive_screen_context_dropped_count,
                "image": observation.data_url,
            },
        )

    def _should_send_proactive_care_batch(self, now: float) -> bool:
        settings = self.proactive_care_settings.normalized()
        cooldown_seconds = settings.cooldown_minutes * 60
        check_interval_seconds = settings.check_interval_minutes * 60
        if (
            self.last_proactive_care_at is not None
            and now - self.last_proactive_care_at + PROACTIVE_TIMER_DUE_GRACE_SECONDS
            < cooldown_seconds
        ):
            return False
        if (
            now - self.last_user_activity_at + PROACTIVE_TIMER_DUE_GRACE_SECONDS
            < check_interval_seconds
        ):
            return False

        if self._proactive_screen_context_allowed():
            if not self.proactive_screen_contexts:
                return False
            if self.proactive_screen_context_batch_started_at is None:
                return False
            return (
                now - self.proactive_screen_context_batch_started_at
                >= cooldown_seconds
            )
        return True

    def _build_proactive_care_event(self, now: float | None = None) -> AgentEvent:
        now = time.perf_counter() if now is None else now
        screen_contexts = [dict(context) for context in self.proactive_screen_contexts]
        payload: dict[str, Any] = {
            "triggered_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "seconds_since_pet_interaction": int(now - self.last_user_activity_at),
            "check_interval_minutes": self.proactive_care_settings.check_interval_minutes,
            "cooldown_minutes": self.proactive_care_settings.cooldown_minutes,
            "screen_context_allowed": self._proactive_screen_context_allowed(),
            "screen_context_count": len(screen_contexts),
            "screen_context_dropped_count": self.proactive_screen_context_dropped_count,
        }
        recent_conversation = _build_proactive_recent_conversation_for_window(self)
        if recent_conversation:
            payload["recent_conversation"] = recent_conversation
            payload["recent_conversation_summary_hint"] = (
                PROACTIVE_RECENT_CONVERSATION_SUMMARY_HINT
            )
        if screen_contexts:
            payload["screen_contexts"] = screen_contexts
            payload["screen_context_window_started_at"] = screen_contexts[0].get("captured_at", "")
            payload["screen_context_window_ended_at"] = screen_contexts[-1].get("captured_at", "")
            debug_log(
                "ProactiveCare",
                "主动屏幕上下文批次已附加",
                {
                    "batch_count": len(screen_contexts),
                    "dropped_count": self.proactive_screen_context_dropped_count,
                    "started_at": payload["screen_context_window_started_at"],
                    "ended_at": payload["screen_context_window_ended_at"],
                },
            )
        return AgentEvent(type="proactive_check", payload=payload)

    def _proactive_care_enabled(self) -> bool:
        return self.proactive_care_settings.normalized().allows_proactive_topics()

    def _proactive_screen_context_allowed(self) -> bool:
        return self.proactive_care_settings.normalized().allows_screen_context()

    def _sync_proactive_care_timer(self) -> None:
        if self._proactive_care_enabled():
            if not self.proactive_care_timer.isActive():
                self.proactive_care_timer.start()
            self._update_proactive_care_hint()
        else:
            self.proactive_care_timer.stop()
            self._clear_proactive_screen_context_batch("disabled")
            self._update_proactive_care_hint()

    def _clear_proactive_screen_context_batch(self, reason: str) -> None:
        had_batch = bool(self.proactive_screen_contexts)
        self.proactive_screen_contexts = []
        self.proactive_screen_context_batch_started_at = None
        self.last_proactive_screen_context_at = None
        self.proactive_screen_context_dropped_count = 0
        if had_batch:
            debug_log("ProactiveCare", "主动屏幕上下文批次已清空", {"reason": reason})

    def _run_event_worker(self, event: AgentEvent, reminder_id: str | None = None) -> None:
        if getattr(self, "startup_initializing", False):
            return
        if self.worker_thread is not None or self.active_reminder_id is not None or self.active_event_type:
            return

        self._begin_interaction(event.type)
        self._log_interaction_stage(
            "event_worker_start",
            {
                "reminder_id": reminder_id,
                "event": {"type": event.type, "payload": event.payload},
            },
        )
        self.active_event = event
        self.active_event_type = event.type
        self.active_reminder_id = reminder_id
        self.active_reminder_text = str(event.payload.get("text", ""))
        self._set_busy(True)
        self.worker_thread = QThread(self)
        self.worker = EventWorker(
            self.agent_runtime,
            event,
        )
        self.worker.visual_observation_store = getattr(self, "visual_observation_store", None)
        self.worker.visual_observation_jobs = getattr(self, "pending_event_visual_observation_jobs", [])
        self.pending_event_visual_observation_jobs = []
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._handle_progress_reply)
        self.worker.finished.connect(self._handle_event_reply)
        self.worker.failed.connect(self._handle_event_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()
        self._log_interaction_stage("event_worker_started")

    @Slot(object)
    def _handle_event_reply(self, result: AgentResult) -> None:
        self._log_interaction_stage(
            "event_result_received",
            {"event_type": self.active_event_type, "segments": len(result.reply.segments)},
        )
        event = self.active_event
        reminder_id = self.active_reminder_id
        if self._queue_event_screen_observation_followup(result, event, reminder_id):
            self._clear_active_event()
            return
        self._clear_active_event()
        if not result.reply.text.strip() and not result.reply.translation.strip() and not result.actions:
            self._log_interaction_stage("event_silent", {"event_type": event.type if event else ""})
            self._end_interaction("event_silent")
            return
        self._consume_agent_result(result)
        if reminder_id is not None:
            self._mark_reminder_completed(reminder_id)

    @Slot(str)
    def _handle_event_error(self, message: str) -> None:
        event_type = self.active_event_type
        self._log_interaction_stage("event_error", {"event_type": event_type, "message": message})
        reminder_id = self.active_reminder_id
        reminder_text = self.active_reminder_text
        self._clear_active_event()
        print(f"[Event] 主动事件生成失败：{message}")
        if event_type == "reminder_due":
            result = AgentResult(
                reply=ChatReply(
                    [
                        ChatSegment(
                            text=f"時間だよ。{reminder_text}",
                            tone="请求",
                            translation=f"到时间了：{reminder_text}",
                            portrait="伸手命令",
                        )
                    ]
                )
            )
            self._consume_agent_result(result)
        elif event_type == "proactive_check":
            result = AgentResult(
                reply=ChatReply(
                    [
                        ChatSegment(
                            text="少し休んでもいいんじゃない？無理しすぎないでよね。",
                            tone="请求",
                            translation="稍微休息一下也可以吧？别太勉强自己。",
                            portrait="伸手命令",
                        )
                    ]
                )
            )
            self._consume_agent_result(result)
        self._end_interaction("error")
        if reminder_id is not None:
            self._mark_reminder_completed(reminder_id)

    def _clear_active_event(self) -> None:
        self.active_event = None
        self.active_event_type = ""
        self.active_reminder_id = None
        self.active_reminder_text = ""

    def _mark_reminder_completed(self, reminder_id: str) -> None:
        try:
            self.reminder_store.mark_completed(reminder_id)
        except ValueError as exc:
            print(f"[Reminder] 标记完成失败：{exc}")

    @Slot(str)
    def _handle_error(self, message: str) -> None:
        self._log_interaction_stage("worker_error", {"message": message})
        pending_napcat = self._pending_napcat_message
        outbound_napcat = self._outbound_napcat_target
        napcat_target = pending_napcat or outbound_napcat
        if napcat_target is not None:
            bridge = getattr(self, "napcat_bridge", None)
            if bridge is not None:
                bridge.deliver_error(napcat_target, message)
            self._pending_napcat_message = None
            self._outbound_napcat_target = None
            self._pending_napcat_voice_message = None
            self._record_history("error", message)
            self.subtitle_controller.cancel_reply_flow(f"QQ 处理失败：{message}")
            self._end_interaction("error")
            return
        if self.messages and self.messages[-1]["role"] == "user":
            self.messages.pop()
        self._record_history("error", message)
        self.subtitle_controller.cancel_reply_flow("……通信に失敗した。設定を確認して。")
        QMessageBox.warning(self, "请求失败", message)
        self._end_interaction("error")

    @Slot()
    def _cleanup_worker(self) -> None:
        self._log_interaction_stage(
            "cleanup_worker_enter",
            {
                "has_pending_screen_observation": self.pending_screen_observation_messages is not None,
                "has_pending_screen_observation_event": self.pending_screen_observation_event is not None,
                "screen_observation_followup_in_progress": self.screen_observation_followup_in_progress,
            },
        )
        if self.worker is not None:
            self.worker.deleteLater()
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None
        if self.screen_observation_followup_in_progress:
            self._log_interaction_stage("screen_observation_cleanup_deferred")
            QTimer.singleShot(0, self._cleanup_worker)
            return
        if self.pending_screen_observation_messages is not None:
            request_messages = self.pending_screen_observation_messages
            self.pending_screen_observation_messages = None
            self._log_interaction_stage(
                "screen_observation_worker_restart",
                {"message_count": len(request_messages)},
            )
            self._start_chat_worker(request_messages)
            return
        if self.pending_screen_observation_event is not None:
            event = self.pending_screen_observation_event
            reminder_id = self.pending_screen_observation_event_reminder_id
            self.pending_screen_observation_event = None
            self.pending_screen_observation_event_reminder_id = None
            self._log_interaction_stage(
                "event_screen_observation_worker_restart",
                {"event_type": event.type},
            )
            self._run_event_worker(event, reminder_id)
            return
        self._set_busy(False)
        self._log_interaction_stage("ui_busy_disabled")
        self._maybe_start_auto_memory_curation()

    def _record_completed_memory_turn(self) -> None:
        if not self.memory_curation_settings.enabled:
            return
        pending_turns = self.memory_curation_state.increment_pending_turns()
        debug_log("Memory", "自动记忆轮次已累计", {"pending_turns": pending_turns})
        if pending_turns >= self.memory_curation_settings.trigger_turns:
            QTimer.singleShot(0, self._maybe_start_auto_memory_curation)

    def _maybe_start_auto_memory_curation(self) -> None:
        if getattr(self, "startup_initializing", False):
            return
        if not self.memory_curation_settings.enabled:
            return
        if self.memory_curation_state.pending_turns() < self.memory_curation_settings.trigger_turns:
            return
        if not self._memory_curation_can_start():
            return
        entries = self.memory_curation_state.unprocessed_entries(self.history_store.load())
        if not entries:
            return
        self._start_memory_curation(
            entries,
            mode="auto",
            target_history_count=len(self.history_store.load()),
            consumed_turns=self.memory_curation_state.pending_turns(),
        )

    def _maybe_start_memory_backfill(self) -> None:
        if getattr(self, "startup_initializing", False):
            return
        if not self.memory_curation_settings.enabled:
            return
        state = self.memory_curation_state.snapshot()
        if state.get("backfill_completed"):
            return
        if not self._memory_curation_can_start():
            QTimer.singleShot(1000, self._maybe_start_memory_backfill)
            return
        entries = self.history_store.load()
        if not entries:
            self.memory_curation_state.mark_processed(0, backfill_completed=True)
            return
        limited_entries = entries[-self.memory_curation_settings.backfill_limit :]
        self._start_memory_curation(
            limited_entries,
            mode="backfill",
            target_history_count=len(entries),
            consumed_turns=0,
        )

    def _memory_curation_can_start(self) -> bool:
        return (
            self.worker_thread is None
            and self.memory_curation_thread is None
            and self.pending_tool_action is None
            and self.pending_screen_observation_messages is None
            and self.pending_screen_observation_event is None
            and not self.screen_observation_followup_in_progress
        )

    def _start_memory_curation(
        self,
        entries: list[ChatHistoryEntry],
        *,
        mode: str,
        target_history_count: int,
        consumed_turns: int,
    ) -> None:
        if not entries or self.memory_curation_thread is not None:
            return
        debug_log(
            "Memory",
            "启动记忆整理",
            {
                "mode": mode,
                "entry_count": len(entries),
                "target_history_count": target_history_count,
                "consumed_turns": consumed_turns,
            },
        )
        self.memory_curation_mode = mode
        self.memory_curation_target_history_count = target_history_count
        self.memory_curation_consumed_turns = consumed_turns
        self.memory_curation_thread = QThread(self)
        self.memory_curation_worker = MemoryCurationWorker(self.memory_curator, entries)
        self.memory_curation_worker.moveToThread(self.memory_curation_thread)
        self.memory_curation_thread.started.connect(self.memory_curation_worker.run)
        self.memory_curation_worker.finished.connect(self._handle_memory_curation_finished)
        self.memory_curation_worker.failed.connect(self._handle_memory_curation_failed)
        self.memory_curation_worker.finished.connect(self.memory_curation_thread.quit)
        self.memory_curation_worker.failed.connect(self.memory_curation_thread.quit)
        self.memory_curation_thread.finished.connect(self._cleanup_memory_curation_worker)
        self.memory_curation_thread.start()

    @Slot(object)
    def _handle_memory_curation_finished(self, result: MemoryCurationResult) -> None:
        mode = self.memory_curation_mode
        debug_log(
            "Memory",
            "记忆整理完成",
            {
                "mode": mode,
                "result": result,
                "target_history_count": self.memory_curation_target_history_count,
                "consumed_turns": self.memory_curation_consumed_turns,
            },
        )
        if mode == "history_clear":
            if result.processed_entries > 0 and result.returned == 0:
                QMessageBox.warning(
                    self,
                    "整理失败",
                    "记忆整理没有写入任何结果，已保留聊天历史。请检查日志后再重试。",
                )
                return
            try:
                self.history_store.clear()
                self.memory_curation_state.mark_history_cleared()
            except OSError as exc:
                QMessageBox.warning(self, "清空失败", f"记忆已整理，但清空历史失败：{exc}")
            else:
                if self.history_window is not None:
                    self.history_window.refresh()
                QMessageBox.information(self, "整理完成", result.summary())
            return

        self.memory_curation_state.mark_processed(
            self.memory_curation_target_history_count,
            consumed_turns=self.memory_curation_consumed_turns,
            backfill_completed=True if mode == "backfill" else None,
        )

    @Slot(str)
    def _handle_memory_curation_failed(self, message: str) -> None:
        debug_log(
            "Memory",
            "记忆整理失败",
            {
                "mode": self.memory_curation_mode,
                "error": message,
            },
        )
        if self.memory_curation_mode == "history_clear":
            QMessageBox.warning(self, "整理失败", f"历史没有清空，原因：{message}")

    @Slot()
    def _cleanup_memory_curation_worker(self) -> None:
        if self.memory_curation_worker is not None:
            self.memory_curation_worker.deleteLater()
        if self.memory_curation_thread is not None:
            self.memory_curation_thread.deleteLater()
        self.memory_curation_worker = None
        self.memory_curation_thread = None
        self.memory_curation_mode = ""
        self.memory_curation_target_history_count = 0
        self.memory_curation_consumed_turns = 0
        if self.history_window is not None:
            self.history_window.set_memory_save_busy(False)
        QTimer.singleShot(0, self._maybe_start_auto_memory_curation)

    @Slot(object)
    def apply_deferred_services(self, services: "DeferredStartupServices") -> None:
        """后台启动服务就绪后注入同一个真实主窗口。"""

        self._move_tts_provider_to_ui_thread(services.tts_provider)
        if self.mcp_tool_provider is not None and self.mcp_tool_provider is not services.mcp_tool_provider:
            self.mcp_tool_provider.close()
        if self.plugin_manager is not services.plugin_manager:
            self.plugin_manager.shutdown_all()

        self._disconnect_tts_error_signal(self.tts_provider)
        self._disconnect_live2d_tts_signals(self.tts_provider)
        self._retire_tts_provider(self.tts_provider)
        self.tts_provider = services.tts_provider
        self.voice_playback_controller.set_provider(services.tts_provider)
        self._connect_tts_error_signal(services.tts_provider)
        self._connect_live2d_tts_signals(services.tts_provider)
        self._warm_up_tts(services.tts_provider)
        self.tool_registry = services.tool_registry
        self.free_access_enabled = self.tool_registry.free_access_enabled
        self.agent_runtime.tools = services.tool_registry
        self.mcp_tool_provider = services.mcp_tool_provider
        self.plugin_manager = services.plugin_manager
        self.mcp_settings = services.mcp_settings

        self.startup_initializing = False
        self.subtitle_controller.cancel_reply_flow(self.character_profile.initial_message)
        self._set_busy(False)
        self.reminder_timer.start()
        self._sync_proactive_care_timer()
        self._start_napcat_bridge_if_enabled()
        QTimer.singleShot(0, self._maybe_start_memory_backfill)
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())
        debug_log(
            "Startup",
            "后台启动服务已注入窗口",
            {
                "tool_count": len(self.tool_registry.all()),
                "mcp_enabled": self.mcp_tool_provider is not None,
                "tts_provider": type(self.tts_provider).__name__,
                "error_count": len(services.errors),
            },
        )
        self.stt_settings = self.settings_service.load_stt_settings()
        if hasattr(self, "voice_button"):
            self.voice_button.setEnabled(self.stt_settings.enabled)
        for error in services.errors:
            print(f"[Startup] {error}")
            if error.startswith("TTS"):
                self._show_tts_error(error)
            elif error.startswith("语音识别"):
                QMessageBox.warning(self, "语音识别", error)

    @Slot(str)
    def handle_deferred_startup_failed(self, error: str) -> None:
        self.startup_initializing = False
        self.subtitle_controller.cancel_reply_flow(f"初始化失败：{error}")
        self._set_busy(False)
        self._sync_proactive_care_timer()
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())
        debug_log("Startup", "后台启动服务失败", {"error": error})
        print(f"[Startup] 后台初始化失败：{error}")

    @Slot(object, object)
    def _on_napcat_chat_requested(
        self,
        message: NapCatInboundMessage,
        request_messages: list[dict[str, Any]],
    ) -> None:
        bridge = getattr(self, "napcat_bridge", None)
        if bridge is None:
            return
        if self.worker_thread is not None:
            napcat_log("忙碌回复", {"session": message.session_id, "reason": "Worker 已占用"})
            bridge.send_busy_reply(message)
            return
        self._pending_napcat_message = message
        display_text = format_inbound_pet_display(message)
        self.subtitle_controller.show_text_immediately(display_text)
        self._record_history("user", f"[{message.sender_name}] {message.text}")
        debug_log(
            "PetWindow",
            "处理 QQ 聊天请求",
            {
                "session_id": message.session_id,
                "message_count": len(request_messages),
            },
        )
        self._start_chat_worker(request_messages)

    def _deliver_napcat_reply(self, message: NapCatInboundMessage, result: AgentResult) -> None:
        bridge = getattr(self, "napcat_bridge", None)
        if bridge is None:
            return
        napcat_settings = self.settings_service.load_napcat_settings()
        prefer_translation = self.subtitle_language == SUBTITLE_LANGUAGE_ZH
        reply_text = format_agent_reply_text(
            result.reply.segments,
            prefer_translation=prefer_translation,
        )
        send_text = napcat_settings.reply_sends_text()
        send_voice = napcat_settings.reply_sends_voice() and bool(result.reply.segments)
        if send_text:
            bridge.deliver_reply(message, reply_text, send_text=True)
        elif send_voice:
            bridge.note_assistant_reply(message, reply_text)
            bridge.release_session(message.session_id)
            napcat_log(
                "已排队 QQ 语音",
                {"session": message.session_id, "sender": message.sender_name},
            )
        else:
            bridge.deliver_reply(message, reply_text, send_text=True)
        if send_voice:
            self._pending_napcat_voice_message = message

    def _forward_segment_voice_to_qq(self, segment: ChatSegment) -> None:
        message = self._pending_napcat_voice_message
        if message is None:
            return
        if not self.settings_service.load_napcat_settings().reply_sends_voice():
            return
        bridge = getattr(self, "napcat_bridge", None)
        if bridge is None:
            return
        text = segment.text.strip()
        if not text or should_skip_tts_text(
            text,
            str(getattr(getattr(self.tts_provider, "settings", None), "text_lang", "ja")),
        ):
            napcat_log("跳过 QQ 语音", {"session": message.session_id, "text": text, "reason": "无可朗读文本"})
            return
        audio_path = self._resolve_qq_voice_audio_path(segment)
        if audio_path is None:
            napcat_log("跳过 QQ 语音", {"session": message.session_id, "text": text, "reason": "无可用音频"})
            return
        try:
            export_path = export_qq_voice_audio(audio_path, self.base_dir)
        except OSError as exc:
            napcat_log("QQ 语音导出失败", {"session": message.session_id, "error": str(exc)})
            debug_log("NapCat", "QQ 语音导出失败", {"error": str(exc), "source": str(audio_path)})
            return
        bridge.send_voice_record(message, export_path)

    def _resolve_qq_voice_audio_path(self, segment: ChatSegment) -> Path | None:
        active_path = self._active_segment_audio_path
        if active_path:
            source = Path(active_path)
            if source.exists():
                return source
        synthesize = getattr(self.tts_provider, "synthesize_to_path", None)
        if not callable(synthesize):
            return None
        tone = segment.tone.strip() or None
        try:
            return synthesize(segment.text, tone)
        except Exception as exc:  # noqa: BLE001
            debug_log(
                "NapCat",
                "QQ 语音合成异常",
                {"text": segment.text, "error": str(exc)},
            )
            return None

    def _is_napcat_host_busy(self) -> bool:
        if getattr(self, "startup_initializing", False):
            return True
        return self.worker_thread is not None

    def _start_napcat_bridge_if_enabled(self) -> None:
        self._stop_napcat_bridge()
        settings = self.settings_service.load_napcat_settings()
        if not settings.enabled:
            return
        bridge: NapCatBridge | None = None
        try:
            bridge = NapCatBridge(
                settings,
                is_busy=self._is_napcat_host_busy,
                parent=self,
            )
            bridge.chat_requested.connect(self._on_napcat_chat_requested)
            bridge.connection_changed.connect(self._handle_napcat_connection_changed)
            if bridge.start():
                self.napcat_bridge = bridge
                if hasattr(self, "input_edit"):
                    self.input_edit.setPlaceholderText(self._default_input_placeholder())
                for index, url in enumerate(settings.websocket_url_hint_lines()):
                    label = "请在 NapCat 填写" if index == 0 else "同机可试"
                    napcat_log(f"{label}：{url}")
                return
            error = bridge.last_error or "未知错误"
            bridge.deleteLater()
            napcat_log("启动失败", {"error": error})
            QMessageBox.warning(
                self,
                "NapCat",
                f"QQ 接入未启动：{error}\n\n"
                "请确认 6199 端口未被 AstrBot/其他桌宠占用，关闭冲突程序后重试。",
            )
        except Exception as exc:  # noqa: BLE001
            if bridge is not None:
                bridge.deleteLater()
            self.napcat_bridge = None
            napcat_log("启动失败", {"error": str(exc)})
            debug_log("NapCat", "桥接启动失败", {"error": str(exc)})

    @Slot(int)
    def _handle_napcat_connection_changed(self, client_count: int) -> None:
        if hasattr(self, "input_edit"):
            self.input_edit.setPlaceholderText(self._default_input_placeholder())
        if client_count > 0:
            napcat_log(f"NapCat 已连接（{client_count} 个客户端）")
            if hasattr(self, "tray_icon"):
                self.tray_icon.showMessage(
                    "NapCat",
                    f"QQ 已连接（{client_count}）",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
        else:
            napcat_log("NapCat 已断开，等待重新连接…")
            if hasattr(self, "tray_icon"):
                self.tray_icon.showMessage(
                    "NapCat",
                    "QQ 已断开，等待 NapCat 重连…",
                    QSystemTrayIcon.MessageIcon.Warning,
                    4000,
                )
        console = getattr(self, "_napcat_console_window", None)
        if isinstance(console, NapCatConsoleWindow):
            console.refresh_connection_status()

    def show_napcat_console(self) -> None:
        console = getattr(self, "_napcat_console_window", None)
        if not isinstance(console, NapCatConsoleWindow):
            console = NapCatConsoleWindow(
                client_count_provider=self._napcat_client_count,
                bridge_running_provider=self._napcat_bridge_running,
                parent=self,
            )
            self._napcat_console_window = console
        console.refresh_connection_status()
        console.show()
        console.raise_()
        console.activateWindow()

    def _napcat_client_count(self) -> int:
        bridge = getattr(self, "napcat_bridge", None)
        if bridge is None:
            return 0
        return int(getattr(bridge, "client_count", 0) or 0)

    def _napcat_bridge_running(self) -> bool:
        return getattr(self, "napcat_bridge", None) is not None

    def _stop_napcat_bridge(self) -> None:
        bridge = getattr(self, "napcat_bridge", None)
        if bridge is None:
            return
        bridge.stop()
        bridge.deleteLater()
        self.napcat_bridge = None

    def _move_tts_provider_to_ui_thread(self, provider: TTSProvider) -> None:
        if not isinstance(provider, QObject):
            return
        application = QApplication.instance()
        if application is None:
            return
        if provider.thread() == application.thread():
            return
        provider.moveToThread(application.thread())

    def _connect_tts_error_signal(self, provider: TTSProvider) -> None:
        error_signal = getattr(provider, "error_occurred", None)
        connect = getattr(error_signal, "connect", None)
        if not callable(connect):
            return
        try:
            connect(self._show_tts_error)
        except (TypeError, RuntimeError) as exc:
            debug_log("TTS", "连接 TTS 错误提示信号失败", {"error": str(exc)})

    def _disconnect_tts_error_signal(self, provider: TTSProvider) -> None:
        error_signal = getattr(provider, "error_occurred", None)
        disconnect = getattr(error_signal, "disconnect", None)
        if not callable(disconnect):
            return
        try:
            disconnect(self._show_tts_error)
        except (TypeError, RuntimeError):
            pass

    def _connect_live2d_tts_signals(self, provider: TTSProvider) -> None:
        if not self._using_live2d or not isinstance(self.portrait_controller, Live2DPortraitController):
            return
        started = getattr(provider, "playback_started", None)
        ended = getattr(provider, "playback_ended", None)
        for signal, slot in (
            (started, self._on_tts_playback_started),
            (ended, self._on_tts_playback_ended),
        ):
            connect = getattr(signal, "connect", None)
            if not callable(connect):
                return
            try:
                connect(slot)
            except (TypeError, RuntimeError) as exc:
                debug_log("Live2D", "连接 TTS 口型信号失败", {"error": str(exc)})
                return

    def _disconnect_live2d_tts_signals(self, provider: TTSProvider) -> None:
        started = getattr(provider, "playback_started", None)
        ended = getattr(provider, "playback_ended", None)
        for signal, slot in (
            (started, self._on_tts_playback_started),
            (ended, self._on_tts_playback_ended),
        ):
            disconnect = getattr(signal, "disconnect", None)
            if not callable(disconnect):
                continue
            try:
                disconnect(slot)
            except (TypeError, RuntimeError):
                pass

    @Slot(str)
    def _on_tts_playback_started(self, audio_path: str) -> None:
        self._active_segment_audio_path = audio_path
        if not isinstance(self.portrait_controller, Live2DPortraitController):
            return
        self.portrait_controller.attach_speech_audio(audio_path)

    @Slot()
    def _on_tts_playback_ended(self) -> None:
        if not isinstance(self.portrait_controller, Live2DPortraitController):
            return
        self.portrait_controller.detach_speech_audio()

    def _warm_up_current_tts(self) -> None:
        self._warm_up_tts(self.tts_provider)

    def _warm_up_tts(self, provider: TTSProvider) -> None:
        self._warm_up_tts_playback(provider)
        self._warm_up_tts_synthesis(provider)

    def _warm_up_tts_playback(self, provider: TTSProvider) -> None:
        warm_up = getattr(provider, "warm_up_playback", None)
        if not callable(warm_up):
            return
        try:
            warm_up()
        except Exception as exc:  # noqa: BLE001
            debug_log(
                "TTS",
                "播放器预热请求失败",
                {
                    "provider": type(provider).__name__,
                    "error": str(exc),
                },
            )

    def _warm_up_tts_synthesis(self, provider: TTSProvider) -> None:
        warm_up = getattr(provider, "warm_up_synthesis", None)
        if not callable(warm_up):
            return
        try:
            warm_up()
        except Exception as exc:  # noqa: BLE001
            debug_log(
                "TTS",
                "合成预热请求失败",
                {
                    "provider": type(provider).__name__,
                    "error": str(exc),
                },
            )

    def _apply_startup_initializing_state(self) -> None:
        self.input_edit.setPlaceholderText(STARTUP_INITIALIZING_TEXT)
        self._set_busy(True)
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())

    def _set_busy(self, busy: bool) -> None:
        startup_initializing = getattr(self, "startup_initializing", False)
        controls_enabled = not busy and not startup_initializing
        self.input_edit.setEnabled(controls_enabled)
        self.screenshot_button.setEnabled(controls_enabled)
        voice_enabled = (
            controls_enabled
            and self.stt_settings.enabled
            and not self._voice_rec_starting
            and self._voice_transcribe_thread is None
        )
        if hasattr(self, "voice_button"):
            self.voice_button.setEnabled(voice_enabled)
        tool_confirmation_panel = getattr(self, "tool_confirmation_panel", None)
        if tool_confirmation_panel is not None:
            tool_confirmation_panel.set_busy(busy or startup_initializing)
        else:
            self.confirm_action_button.setEnabled(controls_enabled)
            self.cancel_action_button.setEnabled(controls_enabled)
        if hasattr(self, "input_edit") and not self.input_edit.text().strip():
            if startup_initializing:
                pass
            elif busy:
                self.input_edit.setPlaceholderText("等待回复中…")
            else:
                self._update_proactive_care_hint()
        self._log_interaction_stage("set_busy", {"busy": busy})
        update_reply_history_buttons = getattr(self, "_update_reply_history_buttons", None)
        if update_reply_history_buttons is not None:
            update_reply_history_buttons()

    @Slot(str)
    def set_speech(self, text: str) -> None:
        self.subtitle_controller.set_speech(text)

    @Slot(str)
    def _show_tts_error(self, message: str) -> None:
        message = str(message).strip()
        if not message:
            return
        text = f"TTS 异常：{_compact_tts_error(message)}"
        self.tts_error_label.setText(text)
        self.tts_error_label.setToolTip(message)
        self.tts_error_label.setVisible(True)
        self.tts_error_timer.start(TTS_ERROR_DISPLAY_MS)
        self._log_interaction_stage("tts_error_visible", {"message": message})
        debug_log("TTS", "TTS 错误已显示到界面", {"message": message})

    @Slot()
    def _hide_tts_error(self) -> None:
        self.tts_error_label.clear()
        self.tts_error_label.setToolTip("")
        self.tts_error_label.setVisible(False)

    def toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    def _resolve_history_audio_path(self, entry: ChatHistoryEntry) -> Path | None:
        audio_path = entry.audio_path.strip()
        if not audio_path:
            return None
        resolved = Path(audio_path)
        if not resolved.is_absolute():
            resolved = self.base_dir / resolved
        return resolved if resolved.exists() else None

    def _play_history_entry_audio(self, entry: ChatHistoryEntry) -> None:
        if self.worker_thread is not None:
            QMessageBox.information(self, "播放不可用", "当前正在处理回复，请稍后再试。")
            return
        if self.subtitle_controller.is_reply_sequence_active():
            QMessageBox.information(self, "播放不可用", "当前正在播报回复，请稍后再试。")
            return

        archived_audio = self._resolve_history_audio_path(entry)
        if archived_audio is not None:
            if self.history_audio_player.play(archived_audio):
                return
            QMessageBox.warning(self, "播放失败", "历史语音文件无法播放，将尝试重新合成。")

        text = _history_entry_tts_text(entry)
        if not text:
            QMessageBox.information(self, "无法播放", "这条记录没有可朗读的内容。")
            return
        tone = entry.tone.strip() or None
        try:
            self.tts_provider.speak(text, tone)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "播放失败", f"语音合成失败：{exc}")

    @Slot()
    def show_history(self) -> None:
        if self.history_window is None:
            self.history_window = HistoryWindow(
                self.history_store,
                self.subtitle_language,
                self._save_history_to_memory_and_clear,
                self._play_history_entry_audio,
                self,
                ui_theme=self.ui_theme,
            )
        self.history_window.set_play_audio_handler(self._play_history_entry_audio)
        self.history_window.set_ui_theme(self.ui_theme)
        self.history_window.set_subtitle_language(self.subtitle_language)
        self.history_window.refresh()
        self.history_window.show()
        self.history_window.raise_()
        self.history_window.activateWindow()

    def _save_history_to_memory_and_clear(self) -> None:
        if self.memory_curation_thread is not None:
            QMessageBox.information(self, "整理中", "记忆整理已经在进行中，请稍后再试。")
            if self.history_window is not None:
                self.history_window.set_memory_save_busy(False)
            return
        if self.worker_thread is not None:
            QMessageBox.information(self, "正在回复", "当前聊天还没处理完，稍后再整理历史。")
            if self.history_window is not None:
                self.history_window.set_memory_save_busy(False)
            return
        entries = self.history_store.load()
        if not entries:
            if self.history_window is not None:
                self.history_window.set_memory_save_busy(False)
                self.history_window.refresh()
            return
        self._start_memory_curation(
            entries,
            mode="history_clear",
            target_history_count=len(entries),
            consumed_turns=self.memory_curation_state.pending_turns(),
        )

    @Slot()
    def show_settings(self) -> None:
        if getattr(self, "startup_initializing", False):
            return
        try:
            tts_settings = self.settings_service.load_tts_settings(
                validate_enabled=False,
                character_profile=self.character_profile,
            )
        except (OSError, TTSConfigError) as exc:
            QMessageBox.warning(self, "配置读取失败", f"TTS 配置读取失败，将使用默认值打开设置：{exc}")
            tts_settings = self._default_tts_settings()

        dialog = SettingsDialog(
            self.api_client.settings,
            tts_settings,
            self.base_dir,
            self.character_registry,
            self.character_profile,
            self.proactive_care_settings,
            self.mcp_settings,
            self.debug_log_settings,
            self.memory_store,
            self.plugin_manager.tools_tabs,
            parent=self,
            portrait_scale_percent=self.portrait_scale_percent,
            subtitle_typing_interval_ms=self.subtitle_typing_interval_ms,
            reply_segment_pause_ms=self.reply_segment_pause_ms,
            stt_settings=self.stt_settings,
            pet_ui_settings=self.settings_service.load_pet_ui_settings(),
            screen_observation_settings=self.settings_service.load_screen_observation_settings(),
            reminder_settings=self.reminder_settings,
            memory_curation_settings=self.memory_curation_settings,
            napcat_settings=self.settings_service.load_napcat_settings(),
            on_open_napcat_console=self.show_napcat_console,
            subtitle_language=self.subtitle_language,
            free_access_enabled=self.free_access_enabled,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        result_subtitle_typing_interval_ms = getattr(
            dialog,
            "result_subtitle_typing_interval_ms",
            self.subtitle_typing_interval_ms,
        )
        result_reply_segment_pause_ms = getattr(
            dialog,
            "result_reply_segment_pause_ms",
            self.reply_segment_pause_ms,
        )
        if (
            dialog.result_api_settings is None
            or dialog.result_tts_settings is None
            or dialog.result_character_id is None
            or dialog.result_proactive_care_settings is None
            or dialog.result_mcp_settings is None
            or dialog.result_debug_log_settings is None
            or dialog.result_portrait_scale_percent is None
            or result_subtitle_typing_interval_ms is None
            or result_reply_segment_pause_ms is None
            or dialog.result_stt_settings is None
            or dialog.result_pet_ui_settings is None
            or dialog.result_screen_observation_settings is None
            or dialog.result_reminder_settings is None
            or dialog.result_memory_curation_settings is None
        ):
            return
        (
            result_subtitle_typing_interval_ms,
            result_reply_segment_pause_ms,
        ) = normalize_subtitle_display_speed(
            result_subtitle_typing_interval_ms,
            result_reply_segment_pause_ms,
        )

        dialog_character_registry = getattr(dialog, "character_registry", None) or self.character_registry
        try:
            selected_profile = dialog_character_registry.get(dialog.result_character_id)
        except CharacterConfigError as exc:
            QMessageBox.critical(self, "角色配置无效", str(exc))
            return

        api_changed = dialog.result_api_settings != self.api_client.settings
        try:
            if api_changed:
                self.settings_service.save_api_settings(dialog.result_api_settings)
            self.settings_service.save_tts_settings(dialog.result_tts_settings)
            self.character_registry = dialog_character_registry
            self.settings_service.save_current_character_id(
                self.character_registry,
                selected_profile.id,
            )
            self.settings_service.save_proactive_care_settings(
                dialog.result_proactive_care_settings
            )
            self.settings_service.save_mcp_runtime_settings(dialog.result_mcp_settings)
            self.settings_service.save_debug_log_settings(dialog.result_debug_log_settings)
            self.settings_service.save_stt_settings(dialog.result_stt_settings)
            self.settings_service.save_pet_ui_settings(dialog.result_pet_ui_settings)
            self.settings_service.save_screen_observation_settings(
                dialog.result_screen_observation_settings
            )
            self.settings_service.save_reminder_settings(dialog.result_reminder_settings)
            self.settings_service.save_memory_curation_settings(
                dialog.result_memory_curation_settings
            )
            if dialog.result_napcat_settings is not None:
                self.settings_service.save_napcat_settings(dialog.result_napcat_settings)
            self._save_system_config_values(
                "ui",
                {
                    "portrait_scale_percent": dialog.result_portrait_scale_percent,
                    "subtitle_typing_interval_ms": result_subtitle_typing_interval_ms,
                    "reply_segment_pause_ms": result_reply_segment_pause_ms,
                    "hover_only_ui": dialog.result_pet_ui_settings.hover_only_ui,
                    "subtitle_language": dialog.result_pet_ui_settings.subtitle_language,
                    "free_access_enabled": dialog.result_pet_ui_settings.free_access_enabled,
                    "music_plugin_enabled": dialog.result_pet_ui_settings.music_plugin_enabled,
                    "music_default_source": dialog.result_pet_ui_settings.music_default_source,
                    "lyric_sync_offset_seconds": (
                        dialog.result_pet_ui_settings.lyric_sync_offset_seconds
                    ),
                    "music_sing_along_enabled": (
                        dialog.result_pet_ui_settings.music_sing_along_enabled
                    ),
                    "ui_theme": dialog.result_pet_ui_settings.ui_theme,
                    "desktop_pet_rules_enabled": (
                        dialog.result_pet_ui_settings.desktop_pet_rules_enabled
                    ),
                },
            )
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", f"无法保存设置：{exc}")
            return

        new_tts_provider = self._create_tts_provider_from_settings(dialog.result_tts_settings)
        if new_tts_provider is None:
            self._apply_portrait_scale_percent(dialog.result_portrait_scale_percent)
            self._apply_subtitle_display_speed(
                result_subtitle_typing_interval_ms,
                result_reply_segment_pause_ms,
            )
            self.proactive_care_settings = dialog.result_proactive_care_settings
            self.mcp_settings = dialog.result_mcp_settings
            self._apply_pet_ui_settings(dialog.result_pet_ui_settings)
            self._apply_screen_observation_settings(dialog.result_screen_observation_settings)
            self._apply_reminder_settings(dialog.result_reminder_settings)
            self.memory_curation_settings = dialog.result_memory_curation_settings
            self.debug_log_settings = dialog.result_debug_log_settings
            self.stt_settings = dialog.result_stt_settings
            self._sync_proactive_care_timer()
            self._start_napcat_bridge_if_enabled()
            if hasattr(self, "tray_icon"):
                self.tray_icon.setContextMenu(self._build_menu())
            return

        if api_changed:
            self.api_client.update_settings(dialog.result_api_settings)
            self.memory_store.reload_api_settings(dialog.result_api_settings, wait=False)
        self._apply_portrait_scale_percent(dialog.result_portrait_scale_percent)
        self._apply_subtitle_display_speed(
            result_subtitle_typing_interval_ms,
            result_reply_segment_pause_ms,
        )
        self.proactive_care_settings = dialog.result_proactive_care_settings
        mcp_restart_required = dialog.result_mcp_settings != self.mcp_settings
        self.mcp_settings = dialog.result_mcp_settings
        self._apply_pet_ui_settings(dialog.result_pet_ui_settings)
        self._apply_screen_observation_settings(dialog.result_screen_observation_settings)
        self._apply_reminder_settings(dialog.result_reminder_settings)
        self.memory_curation_settings = dialog.result_memory_curation_settings
        self.debug_log_settings = dialog.result_debug_log_settings
        self.stt_settings = dialog.result_stt_settings
        try:
            audio_io.configure_audio_paths(self.stt_settings, self.base_dir)
            speech_to_text.configure_whisper_cache(self.base_dir, self.stt_settings)
        except OSError as exc:
            print(f"[STT] 应用设置失败: {exc}")
        if hasattr(self, "voice_button"):
            self.voice_button.setEnabled(self.stt_settings.enabled)
            self.voice_button.setToolTip(
                "点击开始录音，再次点击结束并识别为文字"
                if self.stt_settings.enabled
                else "语音输入已在设置中关闭"
            )
        self._sync_proactive_care_timer()
        disconnect_tts_error_signal = getattr(self, "_disconnect_tts_error_signal", None)
        if callable(disconnect_tts_error_signal):
            disconnect_tts_error_signal(self.tts_provider)
        self._disconnect_live2d_tts_signals(self.tts_provider)
        self._retire_tts_provider(self.tts_provider)
        self.tts_provider = new_tts_provider
        self.voice_playback_controller.set_provider(new_tts_provider)
        connect_tts_error_signal = getattr(self, "_connect_tts_error_signal", None)
        if callable(connect_tts_error_signal):
            connect_tts_error_signal(new_tts_provider)
        self._connect_live2d_tts_signals(new_tts_provider)
        self._warm_up_tts(new_tts_provider)
        self._apply_character(selected_profile)
        self._start_napcat_bridge_if_enabled()
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())
        message = "设置已保存，后续聊天和朗读将使用新配置。"
        if api_changed:
            message += "\n\n长期记忆系统正在后台刷新 API 配置。"
        if mcp_restart_required:
            message += "\n\nMCP 工具开关（Windows / Playwright）需要重启 Mutsuki 后才会生效。"
        QMessageBox.information(self, "保存成功", message)

    @Slot(bool)
    def _toggle_chinese_subtitles(self, checked: bool) -> None:
        next_language = SUBTITLE_LANGUAGE_ZH if checked else SUBTITLE_LANGUAGE_JA
        if next_language == self.subtitle_language:
            return

        previous_language = self.subtitle_language
        self.subtitle_language = next_language
        try:
            self._save_system_config_values(
                "ui",
                {"subtitle_language": next_language},
            )
        except OSError as exc:
            self.subtitle_language = previous_language
            self._apply_speech_font()
            QMessageBox.warning(self, "保存失败", f"无法保存字幕设置：{exc}")
            return

        self._apply_speech_font()
        self.subtitle_controller.set_subtitle_language(self.subtitle_language)
        if not self._refresh_reply_history_review_text():
            self.subtitle_controller.restart_current_segment_speech()
        if self.history_window is not None:
            self.history_window.set_subtitle_language(self.subtitle_language)

    @Slot(bool)
    def _toggle_model_vision(self, checked: bool) -> None:
        self._set_model_vision_enabled(checked)

    def _set_model_vision_enabled(self, enabled: bool) -> None:
        enabled = enabled and self.screen_observation_enabled
        self.model_vision_enabled = enabled
        self.agent_runtime.set_model_vision_enabled(enabled)
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())

    @Slot(bool)
    def _toggle_autonomous_screen_observation(self, checked: bool) -> None:
        self.autonomous_screen_observation_enabled = checked and self.screen_observation_enabled
        self.agent_runtime.set_autonomous_screen_observation_enabled(
            self.autonomous_screen_observation_enabled
        )
        try:
            self._save_system_config_values(
                "screen_observation",
                {
                    "autonomous_enabled": self.autonomous_screen_observation_enabled,
                },
            )
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", f"无法保存自主看屏幕设置：{exc}")
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())

    @Slot(bool)
    def _toggle_free_access(self, checked: bool) -> None:
        self.free_access_enabled = checked
        self.tool_registry.set_free_access_enabled(checked)
        self._save_system_config_values("ui", {"free_access_enabled": checked})
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())

    def _create_tts_provider_from_settings(
        self,
        settings: GPTSoVITSTTSSettings,
    ) -> TTSProvider | None:
        if not settings.enabled:
            debug_log("PetWindow", "设置保存后 TTS 保持关闭")
            return NullTTSProvider()
        try:
            provider = GenieTTSProvider(settings) if settings.provider == TTS_PROVIDER_GENIE else GPTSoVITSTTSProvider(settings)
            debug_log(
                "PetWindow",
                "设置保存后 TTS Provider 已创建",
                {
                    "provider": settings.provider,
                    "api_url": settings.api_url,
                    "timeout_seconds": settings.timeout_seconds,
                },
            )
            return provider
        except TTSConfigError as exc:
            debug_log("PetWindow", "TTS 配置无效", {"error": str(exc)})
            QMessageBox.critical(self, "TTS 配置无效", f"无法启用 TTS，当前语音配置保持不变：{exc}")
            return None

    def _retire_tts_provider(self, provider: TTSProvider) -> None:
        close = getattr(provider, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:  # noqa: BLE001
                debug_log(
                    "TTS",
                    "切换配置时关闭旧 TTS Provider 失败",
                    {"provider": type(provider).__name__, "error": str(exc)},
                )
        self.retired_tts_providers.append(provider)

    def _default_tts_settings(self) -> GPTSoVITSTTSSettings:
        if self.character_profile.voice is not None:
            return GPTSoVITSTTSSettings.from_character_profile(
                character_profile=self.character_profile,
                enabled=False,
                api_url="http://127.0.0.1:9880/tts",
                ref_lang=self.character_profile.voice.ref_lang,
                text_lang=self.character_profile.voice.text_lang,
                timeout_seconds=60,
                validate_enabled=False,
            )
        return GPTSoVITSTTSSettings(
            enabled=False,
            api_url="http://127.0.0.1:9880/tts",
            ref_audio_path=self.base_dir / "ref" / "VO01_2210.ogg",
            ref_text_path=self.base_dir / "ref" / "text.txt",
            ref_text="",
            ref_lang="ja",
            text_lang="ja",
            timeout_seconds=60,
        )

    def _record_history(
        self,
        role: str,
        content: str,
        translation: str = "",
        tone: str = "",
        portrait: str = "",
        _debug: dict | None = None,
    ) -> None:
        try:
            self.history_store.append(role, content, translation, tone, portrait, _debug=_debug)
        except OSError as exc:
            print(f"[History] 写入失败：{exc}")
            debug_log(
                "History",
                "写入失败",
                {
                    "role": role,
                    "content": content,
                    "translation": translation,
                    "tone": tone,
                    "portrait": portrait,
                    "error": str(exc),
                },
            )

    def _record_assistant_reply_history(self, reply: ChatReply, _debug: dict | None = None) -> None:
        clean_segments = [segment for segment in reply.segments if segment.text.strip()]
        if not clean_segments:
            return
        for i, segment in enumerate(clean_segments):
            self._record_history(
                "assistant",
                segment.text,
                segment.translation,
                segment.tone,
                segment.portrait,
                _debug=_debug if i == 0 else None,
            )

    @Slot()
    def _check_due_reminders(self) -> None:
        if not self._can_deliver_reminder():
            return
        try:
            due_reminders = self.reminder_store.due_reminders()
        except ValueError as exc:
            print(f"[Reminder] 读取失败：{exc}")
            debug_log("Reminder", "读取失败", {"error": str(exc)})
            return
        if not due_reminders:
            return
        self._deliver_reminder_now(due_reminders[0])

    def _can_deliver_reminder(self) -> bool:
        if getattr(self, "startup_initializing", False):
            return False
        if self.worker_thread is not None or self.active_reminder_id is not None:
            return False
        if self.active_event_type or self.active_interaction_id:
            return False
        if self.pending_tool_action is not None:
            return False
        subtitle_controller = getattr(self, "subtitle_controller", None)
        if subtitle_controller is not None and subtitle_controller.is_reply_sequence_active():
            return False
        return True

    def _deliver_reminder_now(self, reminder: dict[str, Any]) -> None:
        reminder_id = str(reminder.get("id", "")).strip()
        reminder_text = str(reminder.get("text", "")).strip()
        if not reminder_id or not reminder_text:
            debug_log("Reminder", "跳过无效到期提醒", {"reminder": reminder})
            return

        self.active_reminder_id = reminder_id
        self.active_reminder_text = reminder_text
        self._begin_interaction("reminder_due")
        self._acquire_ui_controls("reminder")

        segment = ChatSegment(
            text=f"時間だよ。{reminder_text}",
            tone="提醒",
            translation=f"到时间了：{reminder_text}",
            portrait="提醒",
        )
        debug_log(
            "Reminder",
            "本地播报到期提醒",
            {
                "id": reminder_id,
                "text": reminder_text,
                "trigger_at": reminder.get("trigger_at"),
            },
        )
        self._record_history("assistant", segment.display_text(self.subtitle_language))
        self._remember_reply_history_segments([segment])
        self._show_reply_segments([segment])

    def _finish_active_reminder_delivery(self) -> None:
        reminder_id = self.active_reminder_id
        if not reminder_id:
            return
        self._mark_reminder_completed(reminder_id)
        self._release_ui_controls("reminder")
        self.active_reminder_id = None
        self.active_reminder_text = ""
        debug_log("Reminder", "提醒播报完成", {"id": reminder_id})

    def _show_reply_segments(self, segments: list[ChatSegment]) -> None:
        self._exit_reply_history_review(update_buttons=False)
        self._remember_reply_history_segments(segments)
        self.subtitle_controller.show_segments(segments)

    def _apply_pet_ui_settings(self, settings) -> None:  # noqa: ANN001 — PetUISettings
        normalized = settings.normalized()
        previous_hover = self.hover_only_ui_enabled
        self.hover_only_ui_enabled = normalized.hover_only_ui
        if self._using_live2d and previous_hover != normalized.hover_only_ui:
            self._apply_hover_only_ui_mode(normalized.hover_only_ui)

        if normalized.subtitle_language != self.subtitle_language:
            self.subtitle_language = normalized.subtitle_language
            self._apply_subtitle_language_ui()
            if self.history_window is not None:
                self.history_window.set_subtitle_language(self.subtitle_language)

        if normalized.free_access_enabled != self.free_access_enabled:
            self.free_access_enabled = normalized.free_access_enabled
            self.tool_registry.set_free_access_enabled(self.free_access_enabled)
        self._apply_music_plugin_settings(normalized)
        if normalized.ui_theme != self.ui_theme:
            self._apply_ui_theme(normalized.ui_theme)
        if normalized.desktop_pet_rules_enabled != self.desktop_pet_rules_enabled:
            self.desktop_pet_rules_enabled = normalized.desktop_pet_rules_enabled
            self.system_prompt = load_character_system_prompt(
                self.character_profile,
                append_desktop_pet_rules=self.desktop_pet_rules_enabled,
            )
            self.agent_runtime.update_character(
                self.system_prompt,
                self.character_profile.reply_tones,
                self.character_profile.portrait_choices,
            )
        if (
            normalized.strict_ja_zh_correspondence_enabled
            != self.strict_ja_zh_correspondence_enabled
        ):
            self.strict_ja_zh_correspondence_enabled = (
                normalized.strict_ja_zh_correspondence_enabled
            )
            self.agent_runtime.set_strict_ja_zh_correspondence_enabled(
                self.strict_ja_zh_correspondence_enabled
            )
        if normalized.panel_width_percent != self.panel_width_percent:
            self.panel_width_percent = normalized.panel_width_percent
            self._apply_panel_layout()
        if hasattr(self, "tray_icon"):
            self.tray_icon.setContextMenu(self._build_menu())

    def _apply_hover_only_ui_mode(self, enabled: bool) -> None:
        if not self._using_live2d:
            return
        self._ui_hover_leave_timer.stop()
        self._ui_controls_holds.clear()
        self._ui_hover_count = 0
        self._live2d_hover_ui = enabled
        if enabled:
            self.bubble.hide()
            self.input_bar.hide()
            self.input_backdrop.hide()
            for widget in self._ui_hover_targets():
                widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
                widget.installEventFilter(self)
        else:
            self.bubble.show()
            self.input_bar.show()
            self.input_backdrop.show()
        self._ui_controls_visible_applied = False
        self._layout_stage()
        self._update_proactive_care_hint()

    def _is_music_sing_along_blocked(self) -> bool:
        if getattr(self, "startup_initializing", False):
            return True
        if self.worker_thread is not None:
            return True
        subtitle_controller = getattr(self, "subtitle_controller", None)
        if subtitle_controller is not None and subtitle_controller.is_reply_sequence_active():
            return True
        return getattr(self.tts_provider, "_current_audio", None) is not None

    def _ensure_music_sing_along_controller(self) -> None:
        if not self._using_live2d or not self.music_sing_along_enabled:
            if self._music_sing_along_controller is not None:
                self._music_sing_along_controller.set_enabled(False)
            return
        if self._music_sing_along_controller is None:
            self._music_sing_along_controller = MusicSingAlongController(
                get_portrait=lambda: self.portrait_controller,
                is_blocked=self._is_music_sing_along_blocked,
                music_source=self.music_default_source,
                parent=self,
            )
        else:
            self._music_sing_along_controller.set_music_source(self.music_default_source)
        self._music_sing_along_controller.set_enabled(True)

    def _apply_music_plugin_settings(self, normalized) -> None:  # noqa: ANN001 — PetUISettings
        enabled = bool(normalized.music_plugin_enabled)
        self.music_plugin_enabled = enabled
        self.music_default_source = normalized.music_default_source
        set_preferred_music_source(normalized.music_default_source)
        self.lyric_sync_offset_seconds = normalized.lyric_sync_offset_seconds
        self.music_sing_along_enabled = normalized.music_sing_along_enabled
        if enabled:
            if self.music_lyrics_overlay is None:
                self.music_lyrics_overlay = MusicLyricsOverlay(
                    self,
                    lyric_sync_offset_seconds=self.lyric_sync_offset_seconds,
                    music_source=self.music_default_source,
                )
            else:
                self.music_lyrics_overlay.set_lyric_sync_offset(
                    self.lyric_sync_offset_seconds
                )
        elif self.music_lyrics_overlay is not None:
            self.music_lyrics_overlay.hide()
        self._ensure_music_sing_along_controller()
        self._layout_stage()

    def _apply_screen_observation_settings(self, settings) -> None:  # noqa: ANN001
        normalized = settings.normalized()
        self.screen_observation_enabled = normalized.enabled
        self.autonomous_screen_observation_enabled = normalized.autonomous_enabled
        self.model_vision_enabled = self.screen_observation_enabled
        self.agent_runtime.set_model_vision_enabled(self.model_vision_enabled)
        self.agent_runtime.set_autonomous_screen_observation_enabled(
            self.autonomous_screen_observation_enabled
        )
        if not self.screen_observation_enabled:
            self._clear_manual_screen_observation()
        if hasattr(self, "screenshot_button"):
            self.screenshot_button.setEnabled(self.screen_observation_enabled)

    def _apply_reminder_settings(self, settings) -> None:  # noqa: ANN001
        normalized = settings.normalized()
        self.reminder_settings = normalized
        self.reminder_timer.setInterval(normalized.check_interval_ms)
        if normalized.enabled:
            if not self.reminder_timer.isActive():
                self.reminder_timer.start()
        else:
            self.reminder_timer.stop()

    def _apply_subtitle_language_ui(self) -> None:
        self.subtitle_controller.set_subtitle_language(self.subtitle_language)
        self._apply_fonts()
        if self.history_window is not None:
            self.history_window.set_subtitle_language(self.subtitle_language)

    def _load_subtitle_language(self) -> str:
        return self.settings_service.load_pet_ui_settings().subtitle_language

    def _load_portrait_scale_percent(self) -> int:
        system_values = self._load_system_config_values("ui")
        return normalize_portrait_scale_percent(
            system_values.get("portrait_scale_percent", PORTRAIT_SCALE_DEFAULT_PERCENT)
        )

    def _load_subtitle_display_speed(self) -> tuple[int, int]:
        system_values = self._load_system_config_values("ui")
        return normalize_subtitle_display_speed(
            system_values.get("subtitle_typing_interval_ms", SPEECH_TYPING_INTERVAL_MS),
            system_values.get("reply_segment_pause_ms", REPLY_SEGMENT_PAUSE_MS),
        )

    def _load_screen_observation_enabled(self) -> bool:
        system_values = self._load_system_config_values("screen_observation")
        if "enabled" in system_values:
            enabled = _parse_bool(system_values.get("enabled"), default=True)
            debug_log("PetWindow", "屏幕观察 YAML 配置已加载", {"enabled": enabled})
            return enabled
        return True

    def _load_autonomous_screen_observation_enabled(self) -> bool:
        system_values = self._load_system_config_values("screen_observation")
        if "autonomous_enabled" in system_values:
            enabled = _parse_bool(system_values.get("autonomous_enabled"), default=True)
            enabled = enabled and self.screen_observation_enabled
            debug_log("PetWindow", "自主屏幕观察 YAML 配置已加载", {"enabled": enabled})
            return enabled
        return self.screen_observation_enabled

    def _load_free_access_enabled(self) -> bool:
        return self.settings_service.load_pet_ui_settings().free_access_enabled

    def _load_system_config_values(self, section: str) -> dict[str, Any]:
        return self.settings_service.load_system_values(section)

    def _save_system_config_values(
        self,
        section: str,
        values: dict[str, Any],
    ) -> None:
        self.settings_service.save_system_values(section, values)

    def _should_use_live2d(self, profile: CharacterProfile) -> bool:
        return profile.live2d is not None and is_live2d_available()

    def _build_portrait_controller(self, profile: CharacterProfile):
        if self._should_use_live2d(profile):
            if profile.live2d is None:
                raise CharacterConfigError("角色 Live2D 配置缺失")
            ensure_live2d_init()
            self._using_live2d = True
            self.label.hide()
            self.portrait_transition_label.hide()
            controller = Live2DPortraitController(
                profile=profile,
                live2d_config=profile.live2d,
                parent_widget=self,
                stage_size=self.stage_size,
                relayout=self._layout_stage,
                on_portrait_changed=lambda _pixmap: None,
                portrait_scale_percent=self.portrait_scale_percent,
                parent=self,
            )
            overlay = controller.input_overlay
            overlay.bind_mouse_handler(self._handle_live2d_portrait_mouse)
            overlay.bind_tap_handler(self._trigger_live2d_tap)
            overlay.bind_long_press_handlers(
                self._on_live2d_long_press_start,
                self._on_live2d_long_press_end,
            )
            return controller

        if profile.live2d is not None:
            print(f"[Live2D] {live2d_import_error()}，回退到 PNG 立绘。")
        self._using_live2d = False
        self.label.show()
        return PortraitController(
            profile=profile,
            parent_widget=self,
            main_label=self.label,
            transition_label=self.portrait_transition_label,
            main_opacity_effect=self.portrait_opacity_effect,
            transition_opacity_effect=self.portrait_transition_opacity_effect,
            stage_size=self.stage_size,
            relayout=self._layout_stage,
            raise_foreground=self._raise_foreground_controls,
            on_portrait_changed=lambda _pixmap: None,
            portrait_scale_percent=self.portrait_scale_percent,
            parent=self,
        )

    def _replace_portrait_controller(self, profile: CharacterProfile) -> None:
        old_controller = getattr(self, "portrait_controller", None)
        if old_controller is not None and getattr(self, "_using_live2d", False):
            if isinstance(old_controller, Live2DPortraitController):
                old_controller.dispose()
            for widget in (old_controller.live2d_widget, old_controller.input_overlay):
                widget.removeEventFilter(self)
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.portrait_controller = self._build_portrait_controller(profile)
        self._connect_live2d_tts_signals(self.tts_provider)
        if self._using_live2d:
            self._init_live2d_hover_ui()
        else:
            self._live2d_hover_ui = False
            self.input_bar.show()
            self.input_backdrop.show()
        self._ensure_music_sing_along_controller()
        self._refresh_input_backdrop_sources()
        self._install_portrait_drag_filters()
        subtitle_controller = getattr(self, "subtitle_controller", None)
        if subtitle_controller is not None:
            subtitle_controller.preload_segment = self.portrait_controller.preload_for_segment
        self._apply_speech_font()

    def _refresh_input_backdrop_sources(self) -> None:
        widgets: list[QWidget] = [self.portrait_controller.portrait_stage_widget]
        if not self._using_live2d:
            widgets.append(self.portrait_transition_label)
        self.input_backdrop.set_source_widgets(tuple(widgets))

    def _install_portrait_drag_filters(self) -> None:
        if self._using_live2d and isinstance(self.portrait_controller, Live2DPortraitController):
            self.portrait_controller.input_overlay.installEventFilter(self)
            return
        self.portrait_controller.portrait_stage_widget.installEventFilter(self)
        self.portrait_transition_label.installEventFilter(self)

    def _forward_live2d_mouse_event(self, event: QMouseEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            return self._handle_mouse_press(event)
        if event.type() == QEvent.Type.MouseMove:
            return self._handle_mouse_move(event)
        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._handle_mouse_release(event)
        return False

    def _apply_portrait_scale_percent(self, portrait_scale_percent: int) -> None:
        self.portrait_scale_percent = normalize_portrait_scale_percent(portrait_scale_percent)
        self.portrait_controller.set_portrait_scale_percent(self.portrait_scale_percent)
        self.portrait_controller.apply_current()
        self._apply_panel_layout()

    def _apply_panel_layout(self) -> None:
        self.stage_size = _stage_size_for_layout(
            self.portrait_scale_percent,
            self.panel_width_percent,
        )
        self.portrait_controller.set_stage_size(self.stage_size)
        self._sync_stage_height_for_layout()
        if self._live2d_hover_ui:
            self._apply_ui_controls_visibility(force=True)
        else:
            self._layout_stage()
        if (self.width(), self.height()) != self.stage_size:
            self.resize(*self.stage_size)

    def _sync_stage_height_for_layout(self) -> None:
        if self._live2d_hover_ui:
            return

    def _apply_subtitle_display_speed(
        self,
        subtitle_typing_interval_ms: int,
        reply_segment_pause_ms: int,
    ) -> None:
        (
            self.subtitle_typing_interval_ms,
            self.reply_segment_pause_ms,
        ) = normalize_subtitle_display_speed(
            subtitle_typing_interval_ms,
            reply_segment_pause_ms,
        )
        subtitle_controller = getattr(self, "subtitle_controller", None)
        set_display_speed = getattr(subtitle_controller, "set_display_speed", None)
        if callable(set_display_speed):
            set_display_speed(
                self.subtitle_typing_interval_ms,
                self.reply_segment_pause_ms,
            )

    def _apply_character(self, profile: CharacterProfile) -> None:
        previous_character_id = self.character_profile.id
        self.character_profile = profile
        self.system_prompt = load_character_system_prompt(
            profile,
            append_desktop_pet_rules=self.desktop_pet_rules_enabled,
        )
        self.memory_store.set_scope(profile.id)
        self.agent_runtime.update_character(self.system_prompt, profile.reply_tones, profile.portrait_choices)
        self.setWindowTitle(profile.display_name)
        self.name_label.setText(profile.display_name)
        if self._should_use_live2d(profile) != self._using_live2d:
            self._replace_portrait_controller(profile)
            portrait_pixmap = self.portrait_controller.pixmap
        else:
            portrait_pixmap = self.portrait_controller.set_profile(profile)
        if hasattr(self, "tray_icon"):
            self._apply_tray_icon()

        self.history_store = self._create_history_store(profile)
        self.visual_observation_store = self._create_visual_observation_store(profile)
        if self.history_window is not None:
            self.history_window.set_history_store(self.history_store, profile.display_name)

        self._load_reply_history_from_store()
        if profile.id != previous_character_id:
            self.messages = []
            self.subtitle_controller.cancel_reply_flow(profile.initial_message)
        self._update_proactive_care_hint()

    def _create_history_store(self, profile: CharacterProfile) -> ChatHistoryStore:
        history_path = self.base_dir / "data" / "chat_history" / f"{profile.id}.jsonl"
        self._migrate_legacy_history(profile, history_path)
        return ChatHistoryStore(history_path, profile.display_name)

    def _create_visual_observation_store(self, profile: CharacterProfile) -> VisualObservationStore:
        visual_path = self.base_dir / "data" / "visual_observations" / f"{profile.id}.jsonl"
        return VisualObservationStore(visual_path)

    def _migrate_legacy_history(self, profile: CharacterProfile, history_path: Path) -> None:
        if profile.id != DEFAULT_CHARACTER_ID or history_path.exists():
            return
        legacy_path = self.base_dir / "data" / "chat_history.jsonl"
        if not legacy_path.exists():
            return
        try:
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history_path.write_text(legacy_path.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError as exc:
            print(f"[History] 旧历史迁移失败：{exc}")


def _build_screen_observation_disabled_result() -> AgentResult:
    return AgentResult(
        reply=ChatReply(
            [
                ChatSegment(
                    text="画面を見る設定がオフになっているよ。設定で許可してから、もう一度試して。",
                    tone="请求",
                    translation="获取屏幕信息现在是关闭的。请在设置里允许后再试。",
                    portrait="伸手命令",
                )
            ]
        )
    )


def _build_screen_observation_failed_result(message: str) -> AgentResult:
    return AgentResult(
        reply=ChatReply(
            [
                ChatSegment(
                    text="今は画面を取得できなかったみたい。権限や表示環境を確認して。",
                    tone="困惑",
                    translation=f"这次没能获取屏幕截图：{message}",
                    portrait="张嘴疑问",
                )
            ]
        )
    )


def _first_screen_observation_request(result: AgentResult) -> AgentAction | None:
    for action in result.actions:
        if action.type == SCREEN_OBSERVATION_REQUEST_ACTION:
            return action
    return None


def _add_visual_context_to_messages(
    messages: list[dict[str, Any]],
    *,
    user_text: str,
    store: VisualObservationStore | None,
    has_current_image: bool,
) -> list[dict[str, Any]]:
    if store is None or has_current_image:
        return messages

    if should_inject_visual_context(user_text):
        records = store.recent(limit=3)
    else:
        records = store.recent(limit=1, since_minutes=VISUAL_OBSERVATION_RECENT_MINUTES)
    context_message = build_visual_context_message(user_text, records)
    if context_message is None:
        return messages

    return [*messages[:-1], context_message, messages[-1]]


def _build_proactive_visual_observation_jobs(event: AgentEvent) -> list[VisualObservationJob]:
    screen_contexts = event.payload.get("screen_contexts")
    if not isinstance(screen_contexts, list) or not screen_contexts:
        return []
    return [
        VisualObservationJob(
            id=generate_visual_observation_id(),
            source="proactive_screen_context",
            user_text="主动关怀屏幕上下文批次",
            screen_contexts=[
                dict(context)
                for context in screen_contexts
                if isinstance(context, dict)
            ],
        )
    ]


def _build_proactive_recent_conversation(
    messages: list[dict[str, Any]],
    *,
    limit: int = PROACTIVE_RECENT_CONVERSATION_LIMIT,
    content_limit: int = PROACTIVE_RECENT_CONVERSATION_CONTENT_LIMIT,
) -> list[dict[str, str]]:
    """为主动事件提取近期用户/助手对话，帮助模型理解一段时间内的语境。"""
    recent: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "")).strip()
        if role not in {"user", "assistant"}:
            continue
        content = _proactive_recent_conversation_content(message.get("content"))
        if not content or content == PROACTIVE_SCREEN_CONTEXT_HISTORY_MARKER:
            continue
        recent.append(
            {
                "role": role,
                "content": _truncate_proactive_recent_conversation_content(
                    content,
                    content_limit,
                ),
            }
        )
    return recent[-limit:]


def _build_proactive_recent_conversation_for_window(
    window: Any,
    *,
    limit: int = PROACTIVE_RECENT_CONVERSATION_LIMIT,
    content_limit: int = PROACTIVE_RECENT_CONVERSATION_CONTENT_LIMIT,
) -> list[dict[str, str]]:
    """主动事件优先读取持久化历史，避免重启后丢失近期语境。"""
    history_entries = _load_proactive_history_entries(window)
    if history_entries:
        return _build_proactive_recent_conversation_from_history_entries(
            history_entries,
            subtitle_language=str(getattr(window, "subtitle_language", SUBTITLE_LANGUAGE_ZH)),
            limit=limit,
            content_limit=content_limit,
        )
    return _build_proactive_recent_conversation(
        getattr(window, "messages", []),
        limit=limit,
        content_limit=content_limit,
    )


def _load_proactive_history_entries(window: Any) -> list[ChatHistoryEntry]:
    history_store = getattr(window, "history_store", None)
    if history_store is None or not hasattr(history_store, "load"):
        return []
    try:
        entries = history_store.load()
    except OSError as exc:
        debug_log("ProactiveCare", "读取近期聊天历史失败", {"error": str(exc)})
        return []
    return [entry for entry in entries if isinstance(entry, ChatHistoryEntry)]


def _build_proactive_recent_conversation_from_history_entries(
    entries: list[ChatHistoryEntry],
    *,
    subtitle_language: str,
    limit: int = PROACTIVE_RECENT_CONVERSATION_LIMIT,
    content_limit: int = PROACTIVE_RECENT_CONVERSATION_CONTENT_LIMIT,
) -> list[dict[str, str]]:
    messages: list[dict[str, Any]] = []
    for entry in entries:
        if entry.role not in {"user", "assistant"}:
            continue
        messages.append(
            {
                "role": entry.role,
                "content": entry.display_content(subtitle_language),
            }
        )
    return _build_proactive_recent_conversation(
        messages,
        limit=limit,
        content_limit=content_limit,
    )


def _proactive_recent_conversation_content(content: Any) -> str:
    if isinstance(content, str):
        return " ".join(content.split())
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(" ".join(parts).split())
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return " ".join(text.split())
    return ""


def _truncate_proactive_recent_conversation_content(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    return content[: max(0, limit - 1)].rstrip() + "…"


def _last_user_message_index(messages: list[dict[str, Any]]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].get("role") == "user":
            return index
    return None


def _history_entry_tts_text(entry: ChatHistoryEntry) -> str:
    text = entry.content.strip()
    if not text:
        return ""
    recovered = parse_chat_reply_result(text)
    if not recovered.needs_retry and recovered.reply.text.strip():
        return recovered.reply.text.strip()
    return text


def _reply_history_segments_from_entries(entries: list[ChatHistoryEntry]) -> list[ChatSegment]:
    segments: list[ChatSegment] = []
    for entry in entries:
        if entry.role != "assistant" or not entry.content.strip():
            continue
        recovered = parse_chat_reply_result(entry.content.strip())
        if not recovered.needs_retry and len(recovered.reply.segments) > 1:
            segments.extend(recovered.reply.segments)
            continue
        tone = entry.tone.strip()
        if tone:
            segment = ChatSegment(
                entry.content.strip(),
                tone,
                entry.translation.strip(),
                entry.portrait.strip(),
            )
        else:
            segment = ChatSegment(
                entry.content.strip(),
                translation=entry.translation.strip(),
                portrait=entry.portrait.strip(),
            )
        segments.append(segment)
    return segments


def _compact_tts_error(message: str, limit: int = 160) -> str:
    compacted = " ".join(str(message).split())
    if len(compacted) <= limit:
        return compacted
    return compacted[: max(0, limit - 1)].rstrip() + "…"


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


def _panel_width_scale(panel_width_percent: int) -> float:
    return normalize_panel_width_percent(panel_width_percent) / 100


def _stage_size_for_layout(
    portrait_scale_percent: int,
    panel_width_percent: int,
) -> tuple[int, int]:
    portrait_scale = normalize_portrait_scale_percent(portrait_scale_percent) / 100
    panel_scale = _panel_width_scale(panel_width_percent)
    return (
        max(460, round(DEFAULT_STAGE_WIDTH * portrait_scale * panel_scale)),
        max(380, round(DEFAULT_STAGE_HEIGHT * portrait_scale)),
    )


def _bubble_layout_width(stage_width: int, panel_width_percent: int) -> int:
    panel_scale = _panel_width_scale(panel_width_percent)
    bubble_max = max(240, round(BUBBLE_MAX_WIDTH * panel_scale))
    side_margin = max(40, round(BUBBLE_SIDE_MARGIN * panel_scale))
    return min(bubble_max, stage_width - side_margin)


def _configure_reply_history_panel(panel: QFrame) -> None:
    panel.setObjectName("replyHistoryPanel")
    panel.setFixedSize(REPLY_HISTORY_PANEL_WIDTH, REPLY_HISTORY_PANEL_HEIGHT)


def _configure_reply_history_button(button: QToolButton, *, text: str, tooltip: str) -> None:
    button.setObjectName("replyHistoryButton")
    button.setText(text)
    button.setFixedSize(REPLY_HISTORY_BUTTON_SIZE, REPLY_HISTORY_BUTTON_SIZE)
    button.setToolTip(tooltip)
