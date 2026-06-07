from __future__ import annotations

import uuid
from pathlib import Path

from app.agent.memory_curator import MemoryCurationSettings
from app.agent.mcp.settings import MCPRuntimeSettings
from app.config.deskpet_settings import (
    PetUISettings,
    ReminderSettings,
    ScreenObservationSettings,
)
from app.config.settings_service import AppSettingsService, DebugLogSettings
from app.config.yaml_config import load_yaml_mapping
from app.llm.api_client import ApiSettings
from app.agent.proactive_care import ProactiveCareSettings
from app.voice.tts import GPTSoVITSTTSSettings


class CharacterRegistryStub:
    profiles = {"sakura": object(), "nanami": object()}

    def get(self, character_id: str) -> object:
        if character_id not in self.profiles:
            raise KeyError(character_id)
        return self.profiles[character_id]


def test_settings_service_loads_yaml_api_config() -> None:
    root = _runtime_root("yaml_api")
    service = AppSettingsService(root)
    service.api_config_path.parent.mkdir(parents=True)
    service.api_config_path.write_text(
        """
llm:
  base_url: https://yaml.example/v1
  api_key: yaml-key
  model: yaml-model
  timeout_seconds: 12
""".lstrip(),
        encoding="utf-8",
    )

    settings = service.load_api_settings()

    assert settings == ApiSettings(
        base_url="https://yaml.example/v1",
        api_key="yaml-key",
        model="yaml-model",
        timeout_seconds=12,
    )


def test_settings_service_saves_runtime_config_to_yaml() -> None:
    root = _runtime_root("yaml_save")
    service = AppSettingsService(root)

    service.save_api_settings(
        ApiSettings(
            base_url="https://api.example/v1",
            api_key="secret",
            model="demo-model",
            timeout_seconds=30,
        )
    )
    service.save_tts_settings(
        GPTSoVITSTTSSettings(
            enabled=True,
            api_url="http://127.0.0.1:9880/tts",
            ref_audio_path=root / "ref.wav",
            ref_text_path=root / "ref.txt",
            ref_text="hello",
            work_dir=root / "data" / "tts_bundles" / "installed" / "gpt_sovits_v2pro",
            ref_lang="ja",
            text_lang="ja",
            timeout_seconds=22,
        )
    )
    service.save_current_character_id(CharacterRegistryStub(), "nanami")  # type: ignore[arg-type]
    service.save_mcp_runtime_settings(MCPRuntimeSettings(windows_enabled=True))
    service.save_debug_log_settings(DebugLogSettings(enabled=True, body_enabled=True, file_enabled=True))
    service.save_proactive_care_settings(
        ProactiveCareSettings(
            enabled=True,
            screen_context_enabled=True,
            check_interval_minutes=5,
            cooldown_minutes=7,
            screen_context_batch_limit=3,
        )
    )

    api = load_yaml_mapping(service.api_config_path)
    characters = load_yaml_mapping(service.characters_config_path)
    system = load_yaml_mapping(service.system_config_path)

    assert api["llm"]["model"] == "demo-model"
    assert api["tts"]["provider"] == "gpt-sovits"
    assert api["tts"]["gpt_sovits"]["work_dir"] == "data/tts_bundles/installed/gpt_sovits_v2pro"
    assert api["tts"]["gpt_sovits"]["timeout_seconds"] == 22
    assert api["tts"]["gpt_sovits"]["streaming_enabled"] is True
    assert characters["current_character_id"] == "nanami"
    assert system["mcp"]["windows_enabled"] is True
    assert system["debug"]["enabled"] is True
    assert system["debug"]["body_enabled"] is True
    assert system["debug"]["file_enabled"] is True
    assert system["proactive_care"]["check_interval_minutes"] == 5


def test_settings_service_loads_tts_work_dir_and_keeps_legacy_blank() -> None:
    root = _runtime_root("yaml_tts_work_dir")
    service = AppSettingsService(root)
    service.api_config_path.parent.mkdir(parents=True)
    service.api_config_path.write_text(
        """
tts:
  provider: gpt-sovits
  enabled: true
  gpt_sovits:
    api_url: http://127.0.0.1:9880/tts
    work_dir: data/tts_bundles/installed/gpt_sovits_v2pro
    ref_lang: ja
    text_lang: ja
""".lstrip(),
        encoding="utf-8",
    )
    work_path = root / "data" / "tts_bundles" / "installed" / "gpt_sovits_v2pro"
    runtime_dir = work_path / "runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "python.exe").write_text("", encoding="utf-8")
    (work_path / "api_v2.py").write_text("", encoding="utf-8")

    settings = service.load_tts_settings(validate_enabled=False)

    assert settings.work_dir == root / "data" / "tts_bundles" / "installed" / "gpt_sovits_v2pro"
    assert settings.streaming_enabled is True

    service.api_config_path.write_text(
        """
tts:
  provider: gpt-sovits
  enabled: true
  gpt_sovits:
    api_url: http://127.0.0.1:9880/tts
""".lstrip(),
        encoding="utf-8",
    )

    legacy_settings = service.load_tts_settings(validate_enabled=False)

    assert legacy_settings.work_dir == root / "data" / "tts_bundles" / "installed" / "gpt_sovits_v2pro"
    assert legacy_settings.streaming_enabled is True


def test_settings_service_migrates_legacy_genie_tts_to_gptsovits() -> None:
    root = _runtime_root("yaml_genie_tts")
    service = AppSettingsService(root)
    service.api_config_path.parent.mkdir(parents=True)
    service.api_config_path.write_text(
        """
tts:
  provider: genie-tts
  enabled: true
  genie_tts:
    api_url: http://127.0.0.1:9881/
    work_dir: data/tts_bundles/installed/genie_tts_server
    onnx_model_dir: data/tts_bundles/onnx/sakura
    timeout_seconds: 33
""".lstrip(),
        encoding="utf-8",
    )

    loaded = service.load_tts_settings(validate_enabled=False)
    service.save_tts_settings(loaded)
    saved = load_yaml_mapping(service.api_config_path)

    assert loaded.provider == "gpt-sovits"
    assert saved["tts"]["provider"] == "gpt-sovits"
    assert "genie_tts" not in saved["tts"]
    assert saved["tts"]["gpt_sovits"]["api_url"] == "http://127.0.0.1:9880/tts"
    assert saved["tts"]["gpt_sovits"]["streaming_enabled"] is True

def test_settings_service_loads_debug_log_settings() -> None:
    root = _runtime_root("yaml_debug")
    service = AppSettingsService(root)
    service.save_system_values("debug", {"enabled": True, "body_enabled": False, "file_enabled": True})

    settings = service.load_debug_log_settings()

    assert settings == DebugLogSettings(enabled=True, body_enabled=False, file_enabled=True)


def test_settings_service_loads_debug_file_disabled_by_default() -> None:
    root = _runtime_root("yaml_debug_legacy")
    service = AppSettingsService(root)
    service.save_system_values("debug", {"enabled": True, "body_enabled": False})

    settings = service.load_debug_log_settings()

    assert settings == DebugLogSettings(enabled=True, body_enabled=False, file_enabled=False)


def test_settings_service_saves_deskpet_and_mcp_playwright_settings() -> None:
    root = _runtime_root("yaml_deskpet")
    service = AppSettingsService(root)
    service.config_dir.mkdir(parents=True)
    service.save_system_values("mcp", {"windows_enabled": False})
    mcp_path = service.config_dir / "mcp.yaml"
    mcp_path.write_text(
        "enabled: true\nservers:\n  playwright:\n    enabled: false\n",
        encoding="utf-8",
    )

    service.save_pet_ui_settings(
        PetUISettings(
            hover_only_ui=False,
            subtitle_language="ja",
            free_access_enabled=True,
            lyric_sync_offset_seconds=2.3,
            panel_width_percent=80,
        )
    )
    service.save_screen_observation_settings(
        ScreenObservationSettings(enabled=False, autonomous_enabled=False)
    )
    service.save_reminder_settings(
        ReminderSettings(enabled=False, check_interval_seconds=30)
    )
    service.save_memory_curation_settings(
        MemoryCurationSettings(enabled=False, trigger_turns=10, backfill_limit=120)
    )
    service.save_mcp_runtime_settings(
        MCPRuntimeSettings(windows_enabled=True, playwright_enabled=True)
    )

    system = load_yaml_mapping(service.system_config_path)
    mcp_data = load_yaml_mapping(mcp_path)

    assert system["ui"]["hover_only_ui"] is False
    assert system["ui"]["subtitle_language"] == "ja"
    assert system["ui"]["free_access_enabled"] is True
    assert system["ui"]["lyric_sync_offset_seconds"] == 2.3
    assert system["ui"]["panel_width_percent"] == 80
    loaded = service.load_pet_ui_settings()
    assert loaded.lyric_sync_offset_seconds == 2.3
    assert system["screen_observation"]["enabled"] is False
    assert system["reminders"]["check_interval_seconds"] == 30
    assert system["memory_curation"]["trigger_turns"] == 10
    assert system["mcp"]["windows_enabled"] is True
    assert mcp_data["servers"]["playwright"]["enabled"] is True

    assert service.load_pet_ui_settings() == PetUISettings(
        hover_only_ui=False,
        subtitle_language="ja",
        free_access_enabled=True,
        lyric_sync_offset_seconds=2.3,
        panel_width_percent=80,
    )
    assert service.load_mcp_runtime_settings() == MCPRuntimeSettings(
        windows_enabled=True,
        playwright_enabled=True,
    )


def _runtime_root(name: str) -> Path:
    root = Path(__file__).resolve().parents[2] / "__pycache__" / "test_runtime" / name / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root
