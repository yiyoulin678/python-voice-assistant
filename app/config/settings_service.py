from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from app.agent.memory_curator import MemoryCurationSettings
from app.agent.mcp.settings import MCPRuntimeSettings
from app.config.ai_settings import AiFeatureSettings
from app.config.deskpet_settings import (
    PetUISettings,
    REMINDER_CHECK_INTERVAL_DEFAULT_SECONDS,
    ReminderSettings,
    ScreenObservationSettings,
    SUBTITLE_LANGUAGE_JA,
    SUBTITLE_LANGUAGE_ZH,
)
from app.config.character_loader import DEFAULT_CHARACTER_ID, CharacterProfile, CharacterRegistry
from app.config.yaml_config import load_yaml_mapping, save_yaml_mapping
from app.llm.api_client import ApiSettings
from app.agent.proactive_care import (
    PROACTIVE_DEFAULT_CHECK_INTERVAL_MINUTES,
    PROACTIVE_DEFAULT_COOLDOWN_MINUTES,
    PROACTIVE_DEFAULT_SCREEN_CONTEXT_BATCH_LIMIT,
    ProactiveCareSettings,
)
from app.platforms.napcat.settings import (
    NAPCAT_REPLY_BOTH,
    DEFAULT_NAPCAT_HISTORY_LIMIT,
    DEFAULT_NAPCAT_HOST,
    DEFAULT_NAPCAT_PATH,
    DEFAULT_NAPCAT_PORT,
    NapCatSettings,
)
from app.voice.stt_settings import (
    DEFAULT_WHISPER_LANGUAGE,
    DEFAULT_WHISPER_MODEL_NAME,
    VOICE_CALL_SILENCE_SECONDS,
    STTSettings,
)
from app.voice.tts import (
    DEFAULT_GENIE_TTS_API_URL,
    DEFAULT_GPT_SOVITS_API_URL,
    TTS_PROVIDER_GENIE,
    TTS_PROVIDER_GPT_SOVITS,
    TTS_PROVIDER_NONE,
    GPTSoVITSTTSSettings,
)


API_CONFIG_FILE = "api.yaml"
CHARACTERS_CONFIG_FILE = "characters.yaml"
SYSTEM_CONFIG_FILE = "system_config.yaml"


@dataclass(frozen=True)
class DebugLogSettings:
    """调试日志配置。"""

    enabled: bool = False
    body_enabled: bool = False
    file_enabled: bool = False


@dataclass(frozen=True)
class AppSettingsService:
    """集中管理运行配置；唯一持久化来源是 data/config/*.yaml。"""

    base_dir: Path

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "data" / "config"

    @property
    def api_config_path(self) -> Path:
        return self.config_dir / API_CONFIG_FILE

    @property
    def characters_config_path(self) -> Path:
        return self.config_dir / CHARACTERS_CONFIG_FILE

    @property
    def system_config_path(self) -> Path:
        return self.config_dir / SYSTEM_CONFIG_FILE

    def load_api_settings(self) -> ApiSettings:
        data = self._api_section("llm")
        timeout_seconds = _int_value(
            data.get("timeout_seconds"),
            60,
        )
        return ApiSettings(
            base_url=str(data.get("base_url", "https://api.openai.com/v1")).strip().rstrip("/"),
            api_key=str(data.get("api_key", "")).strip(),
            model=str(data.get("model", "gpt-4.1-mini")).strip(),
            timeout_seconds=timeout_seconds,
        )

    def save_api_settings(self, settings: ApiSettings) -> None:
        data = load_yaml_mapping(self.api_config_path)
        data["llm"] = {
            "base_url": settings.base_url.strip().rstrip("/"),
            "api_key": settings.api_key.strip(),
            "model": settings.model.strip(),
            "timeout_seconds": int(settings.timeout_seconds),
        }
        save_yaml_mapping(self.api_config_path, data)

    def load_tts_settings(
        self,
        *,
        validate_enabled: bool = True,
        character_profile: CharacterProfile | None = None,
    ) -> GPTSoVITSTTSSettings:
        data = self._api_section("tts")
        gpt_sovits = _mapping(data.get("gpt_sovits"))
        genie_tts = _mapping(data.get("genie_tts"))
        provider = str(data.get("provider", "")).strip().lower()
        enabled = _bool_value(data.get("enabled"), False)
        if provider in {"none", "off", "disabled", "不使用"}:
            enabled = False
            provider = TTS_PROVIDER_NONE
        elif provider in {"gpt-sovits", "gpt_sovits", "gptsovits"}:
            enabled = True
            provider = TTS_PROVIDER_GPT_SOVITS
        elif provider in {"genie", "genie-tts", "genie_tts"}:
            enabled = True
            provider = TTS_PROVIDER_GENIE
        else:
            provider = TTS_PROVIDER_GPT_SOVITS if enabled else TTS_PROVIDER_NONE

        provider_data = genie_tts if provider == TTS_PROVIDER_GENIE else gpt_sovits
        default_api_url = DEFAULT_GENIE_TTS_API_URL if provider == TTS_PROVIDER_GENIE else DEFAULT_GPT_SOVITS_API_URL
        api_url = str(provider_data.get("api_url", default_api_url)).strip()
        work_dir = _optional_path(provider_data.get("work_dir"), self.base_dir)
        if provider == TTS_PROVIDER_GPT_SOVITS:
            from app.voice.gpt_sovits_paths import resolve_gpt_sovits_work_dir

            work_dir = resolve_gpt_sovits_work_dir(self.base_dir, work_dir)
        ref_lang = str(provider_data.get("ref_lang", gpt_sovits.get("ref_lang", "ja"))).strip()
        text_lang = str(provider_data.get("text_lang", gpt_sovits.get("text_lang", "ja"))).strip()
        timeout_seconds = _int_value(provider_data.get("timeout_seconds"), 60)
        streaming_enabled = _bool_value(gpt_sovits.get("streaming_enabled"), False)
        onnx_model_dir = _optional_path(genie_tts.get("onnx_model_dir"), self.base_dir)
        if character_profile is not None:
            if provider == TTS_PROVIDER_GENIE and onnx_model_dir is None:
                onnx_model_dir = self.base_dir / "data" / "tts_bundles" / "onnx" / character_profile.id
            if character_profile.voice is not None:
                if character_profile.voice.ref_lang.strip():
                    ref_lang = character_profile.voice.ref_lang.strip()
                if character_profile.voice.text_lang.strip():
                    text_lang = character_profile.voice.text_lang.strip()
            settings = GPTSoVITSTTSSettings.from_character_profile(
                character_profile=character_profile,
                enabled=enabled,
                api_url=api_url,
                ref_lang=ref_lang,
                text_lang=text_lang,
                timeout_seconds=timeout_seconds,
                provider=provider,
                work_dir=work_dir,
                onnx_model_dir=onnx_model_dir,
                validate_enabled=validate_enabled,
            )
        else:
            if provider == TTS_PROVIDER_GENIE and onnx_model_dir is None:
                onnx_model_dir = self.base_dir / "data" / "tts_bundles" / "onnx" / "default"
            settings = GPTSoVITSTTSSettings(
                enabled=enabled,
                api_url=api_url,
                ref_audio_path=self.base_dir / "ref" / "VO01_2210.ogg",
                ref_text_path=self.base_dir / "ref" / "text.txt",
                ref_text="",
                provider=provider,
                work_dir=work_dir,
                character_name="sakura",
                onnx_model_dir=onnx_model_dir,
                ref_lang=ref_lang,
                text_lang=text_lang,
                timeout_seconds=timeout_seconds,
            )
        if provider == TTS_PROVIDER_GPT_SOVITS:
            settings = replace(settings, streaming_enabled=streaming_enabled)
        if settings.enabled and validate_enabled:
            settings.validate()
        return settings

    def save_tts_settings(self, settings: GPTSoVITSTTSSettings) -> None:
        data = load_yaml_mapping(self.api_config_path)
        saved_provider = settings.provider if settings.enabled else TTS_PROVIDER_NONE
        section_provider = settings.provider if settings.provider in {TTS_PROVIDER_GENIE, TTS_PROVIDER_GPT_SOVITS} else TTS_PROVIDER_GPT_SOVITS
        tts_data: dict[str, object] = {
            "provider": saved_provider,
            "enabled": bool(settings.enabled),
        }
        if section_provider == TTS_PROVIDER_GENIE:
            tts_data["genie_tts"] = {
                "api_url": settings.api_url.strip() or DEFAULT_GENIE_TTS_API_URL,
                "work_dir": _path_for_config(settings.work_dir, self.base_dir),
                "onnx_model_dir": _path_for_config(settings.onnx_model_dir, self.base_dir),
                "ref_lang": settings.ref_lang.strip(),
                "text_lang": settings.text_lang.strip(),
                "timeout_seconds": int(settings.timeout_seconds),
            }
        elif section_provider == TTS_PROVIDER_GPT_SOVITS:
            tts_data["gpt_sovits"] = {
                "api_url": settings.api_url.strip(),
                "work_dir": _path_for_config(settings.work_dir, self.base_dir),
                "ref_lang": settings.ref_lang.strip(),
                "text_lang": settings.text_lang.strip(),
                "timeout_seconds": int(settings.timeout_seconds),
                "streaming_enabled": bool(settings.streaming_enabled),
            }
        data["tts"] = tts_data
        save_yaml_mapping(self.api_config_path, data)

    def load_mcp_runtime_settings(self) -> MCPRuntimeSettings:
        mcp = self._system_section("mcp")
        playwright_enabled = False
        mcp_path = self.config_dir / "mcp.yaml"
        if mcp_path.exists():
            servers = _mapping(load_yaml_mapping(mcp_path).get("servers"))
            playwright = _mapping(servers.get("playwright"))
            playwright_enabled = _bool_value(playwright.get("enabled"), False)
        return MCPRuntimeSettings(
            windows_enabled=_bool_value(
                mcp.get("windows_enabled"),
                False,
            ),
            playwright_enabled=playwright_enabled,
        )

    def save_mcp_runtime_settings(self, settings: MCPRuntimeSettings) -> None:
        self.save_system_values(
            "mcp",
            {"windows_enabled": bool(settings.windows_enabled)},
        )
        mcp_path = self.config_dir / "mcp.yaml"
        data = load_yaml_mapping(mcp_path)
        servers = _mapping(data.get("servers"))
        playwright = _mapping(servers.get("playwright"))
        playwright["enabled"] = bool(settings.playwright_enabled)
        servers["playwright"] = playwright
        data["servers"] = servers
        save_yaml_mapping(mcp_path, data)

    def load_pet_ui_settings(self) -> PetUISettings:
        ui = self._system_section("ui")
        language = str(ui.get("subtitle_language", SUBTITLE_LANGUAGE_ZH)).strip().lower()
        if language != SUBTITLE_LANGUAGE_ZH:
            language = SUBTITLE_LANGUAGE_JA
        return PetUISettings(
            hover_only_ui=_bool_value(ui.get("hover_only_ui"), True),
            subtitle_language=language,
            free_access_enabled=_bool_value(ui.get("free_access_enabled"), False),
            music_plugin_enabled=_bool_value(ui.get("music_plugin_enabled"), True),
            music_default_source=str(ui.get("music_default_source", "netease")),
            lyric_sync_offset_seconds=float(ui.get("lyric_sync_offset_seconds", 1.2)),
            ui_theme=str(ui.get("ui_theme", "")),
            desktop_pet_rules_enabled=_bool_value(ui.get("desktop_pet_rules_enabled"), False),
            strict_ja_zh_correspondence_enabled=_bool_value(
                ui.get("strict_ja_zh_correspondence_enabled"),
                False,
            ),
            panel_width_percent=ui.get("panel_width_percent", 100),
        ).normalized()

    def save_pet_ui_settings(self, settings: PetUISettings) -> None:
        normalized = settings.normalized()
        self.save_system_values(
            "ui",
            {
                "hover_only_ui": bool(normalized.hover_only_ui),
                "subtitle_language": normalized.subtitle_language,
                "free_access_enabled": bool(normalized.free_access_enabled),
                "music_plugin_enabled": bool(normalized.music_plugin_enabled),
                "music_default_source": normalized.music_default_source,
                "lyric_sync_offset_seconds": normalized.lyric_sync_offset_seconds,
                "ui_theme": normalized.ui_theme,
                "desktop_pet_rules_enabled": bool(normalized.desktop_pet_rules_enabled),
                "strict_ja_zh_correspondence_enabled": bool(
                    normalized.strict_ja_zh_correspondence_enabled
                ),
                "panel_width_percent": normalized.panel_width_percent,
            },
        )

    def load_screen_observation_settings(self) -> ScreenObservationSettings:
        section = self._system_section("screen_observation")
        enabled = _bool_value(section.get("enabled"), True)
        autonomous = _bool_value(
            section.get("autonomous_enabled"),
            enabled,
        )
        return ScreenObservationSettings(
            enabled=enabled,
            autonomous_enabled=autonomous,
        ).normalized()

    def save_screen_observation_settings(self, settings: ScreenObservationSettings) -> None:
        normalized = settings.normalized()
        self.save_system_values(
            "screen_observation",
            {
                "enabled": bool(normalized.enabled),
                "autonomous_enabled": bool(normalized.autonomous_enabled),
            },
        )

    def load_reminder_settings(self) -> ReminderSettings:
        section = self._system_section("reminders")
        return ReminderSettings(
            enabled=_bool_value(section.get("enabled"), True),
            check_interval_seconds=_int_value(
                section.get("check_interval_seconds"),
                REMINDER_CHECK_INTERVAL_DEFAULT_SECONDS,
            ),
        ).normalized()

    def save_reminder_settings(self, settings: ReminderSettings) -> None:
        normalized = settings.normalized()
        self.save_system_values(
            "reminders",
            {
                "enabled": bool(normalized.enabled),
                "check_interval_seconds": int(normalized.check_interval_seconds),
            },
        )

    def save_memory_curation_settings(self, settings: MemoryCurationSettings) -> None:
        self.save_system_values(
            "memory_curation",
            {
                "enabled": bool(settings.enabled),
                "trigger_turns": int(settings.trigger_turns),
                "backfill_limit": int(settings.backfill_limit),
            },
        )

    def load_ai_feature_settings(self) -> AiFeatureSettings:
        section = self._system_section("ai")
        return AiFeatureSettings(
            auto_session_summary_enabled=_bool_value(
                section.get("auto_session_summary_enabled"),
                True,
            ),
        ).normalized()

    def save_ai_feature_settings(self, settings: AiFeatureSettings) -> None:
        normalized = settings.normalized()
        self.save_system_values(
            "ai",
            {
                "auto_session_summary_enabled": bool(normalized.auto_session_summary_enabled),
            },
        )

    def load_debug_log_settings(self) -> DebugLogSettings:
        debug = self._system_section("debug")
        return DebugLogSettings(
            enabled=_bool_value(debug.get("enabled"), False),
            body_enabled=_bool_value(debug.get("body_enabled"), False),
            file_enabled=_bool_value(debug.get("file_enabled"), False),
        )

    def save_debug_log_settings(self, settings: DebugLogSettings) -> None:
        self.save_system_values(
            "debug",
            {
                "enabled": bool(settings.enabled),
                "body_enabled": bool(settings.body_enabled),
                "file_enabled": bool(settings.file_enabled),
            },
        )

    def load_napcat_settings(self) -> NapCatSettings:
        napcat = self._system_section("napcat")
        return NapCatSettings(
            enabled=_bool_value(napcat.get("enabled"), False),
            host=str(napcat.get("host", DEFAULT_NAPCAT_HOST) or DEFAULT_NAPCAT_HOST),
            port=_int_value(napcat.get("port"), DEFAULT_NAPCAT_PORT),
            path=str(napcat.get("path", DEFAULT_NAPCAT_PATH) or DEFAULT_NAPCAT_PATH),
            connect_host=str(napcat.get("connect_host", "") or ""),
            token=str(napcat.get("token", "") or ""),
            allow_private=_bool_value(napcat.get("allow_private"), True),
            allow_group=_bool_value(napcat.get("allow_group"), False),
            history_limit=_int_value(napcat.get("history_limit"), DEFAULT_NAPCAT_HISTORY_LIMIT),
            busy_reply_text=str(
                napcat.get("busy_reply_text", "") or "稍等一下，我还在回复上一条消息。"
            ),
            reply_mode=str(napcat.get("reply_mode", NAPCAT_REPLY_BOTH) or NAPCAT_REPLY_BOTH),
        ).normalized()

    def save_napcat_settings(self, settings: NapCatSettings) -> None:
        normalized = settings.normalized()
        self.save_system_values(
            "napcat",
            {
                "enabled": bool(normalized.enabled),
                "host": normalized.host,
                "port": int(normalized.port),
                "path": normalized.path,
                "connect_host": normalized.connect_host,
                "token": normalized.token,
                "allow_private": bool(normalized.allow_private),
                "allow_group": bool(normalized.allow_group),
                "history_limit": int(normalized.history_limit),
                "busy_reply_text": normalized.busy_reply_text,
                "reply_mode": normalized.reply_mode,
            },
        )

    def load_proactive_care_settings(self) -> ProactiveCareSettings:
        proactive = self._system_section("proactive_care")
        return ProactiveCareSettings(
            enabled=_bool_value(proactive.get("enabled"), True),
            screen_context_enabled=_bool_value(
                proactive.get("screen_context_enabled"),
                True,
            ),
            check_interval_minutes=_int_value(
                proactive.get("check_interval_minutes"),
                PROACTIVE_DEFAULT_CHECK_INTERVAL_MINUTES,
            ),
            cooldown_minutes=_int_value(
                proactive.get("cooldown_minutes"),
                PROACTIVE_DEFAULT_COOLDOWN_MINUTES,
            ),
            screen_context_batch_limit=_int_value(
                proactive.get("screen_context_batch_limit"),
                PROACTIVE_DEFAULT_SCREEN_CONTEXT_BATCH_LIMIT,
            ),
        )

    def save_proactive_care_settings(self, settings: ProactiveCareSettings) -> None:
        normalized = settings.normalized()
        self.save_system_values(
            "proactive_care",
            {
                "enabled": bool(normalized.enabled),
                "screen_context_enabled": bool(normalized.screen_context_enabled),
                "check_interval_minutes": int(normalized.check_interval_minutes),
                "cooldown_minutes": int(normalized.cooldown_minutes),
                "screen_context_batch_limit": int(normalized.screen_context_batch_limit),
            },
        )

    def load_memory_curation_settings(self):
        from app.agent.memory_curator import MemoryCurationSettings

        memory = self._system_section("memory_curation")
        return MemoryCurationSettings(
            enabled=_bool_value(memory.get("enabled"), True),
            trigger_turns=_int_value(memory.get("trigger_turns"), 8),
            backfill_limit=_int_value(memory.get("backfill_limit"), 200),
        )

    def load_current_character_id(self, character_registry: CharacterRegistry) -> str:
        data = load_yaml_mapping(self.characters_config_path)
        configured = str(data.get("current_character_id", "")).strip()
        if configured in character_registry.profiles:
            return configured
        if DEFAULT_CHARACTER_ID in character_registry.profiles:
            return DEFAULT_CHARACTER_ID
        if character_registry.profiles:
            return next(iter(character_registry.profiles))
        raise ValueError("未找到任何角色包。")

    def save_current_character_id(
        self,
        character_registry: CharacterRegistry,
        character_id: str,
    ) -> None:
        character_registry.get(character_id)
        data = load_yaml_mapping(self.characters_config_path)
        data["current_character_id"] = character_id
        save_yaml_mapping(self.characters_config_path, data)

    def load_stt_settings(self) -> STTSettings:
        data = self._system_section("stt")
        device_raw = data.get("input_device_index")
        input_device_index: int | None = None
        if device_raw is not None and str(device_raw).strip().lower() not in {"", "null", "none"}:
            try:
                input_device_index = int(device_raw)
            except (TypeError, ValueError):
                input_device_index = None
        try:
            silence_seconds = float(data.get("voice_call_silence_seconds", VOICE_CALL_SILENCE_SECONDS))
        except (TypeError, ValueError):
            silence_seconds = VOICE_CALL_SILENCE_SECONDS
        silence_seconds = max(0.35, min(2.0, silence_seconds))
        return STTSettings(
            enabled=_bool_value(data.get("enabled"), True),
            model_name=str(data.get("model_name", DEFAULT_WHISPER_MODEL_NAME)).strip() or DEFAULT_WHISPER_MODEL_NAME,
            language=str(data.get("language", DEFAULT_WHISPER_LANGUAGE)).strip() or DEFAULT_WHISPER_LANGUAGE,
            input_device_index=input_device_index,
            voice_call_enabled=_bool_value(data.get("voice_call_enabled"), True),
            voice_call_silence_seconds=silence_seconds,
            voice_call_interrupt_tts=_bool_value(data.get("voice_call_interrupt_tts"), True),
        )

    def save_stt_settings(self, settings: STTSettings) -> None:
        self.save_system_values(
            "stt",
            {
                "enabled": bool(settings.enabled),
                "model_name": settings.model_name.strip(),
                "language": settings.language.strip(),
                "input_device_index": settings.input_device_index,
                "voice_call_enabled": bool(settings.voice_call_enabled),
                "voice_call_silence_seconds": float(settings.voice_call_silence_seconds),
                "voice_call_interrupt_tts": bool(settings.voice_call_interrupt_tts),
            },
        )

    def load_system_values(self, section: str) -> dict[str, Any]:
        return self._system_section(section)

    def save_system_values(self, section: str, values: dict[str, Any]) -> None:
        data = load_yaml_mapping(self.system_config_path)
        current = _mapping(data.get(section))
        current.update(values)
        data[section] = current
        save_yaml_mapping(self.system_config_path, data)

    def _api_section(self, name: str) -> dict[str, Any]:
        return _mapping(load_yaml_mapping(self.api_config_path).get(name))

    def _system_section(self, name: str) -> dict[str, Any]:
        return _mapping(load_yaml_mapping(self.system_config_path).get(name))


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _optional_path(value: Any, base_dir: Path) -> Path | None:
    if value is None:
        return None
    text = str(value).strip().strip('"').strip("'")
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return base_dir / path


def _path_for_config(path: Path | None, base_dir: Path) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def _int_value(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any, default: bool) -> bool:
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
