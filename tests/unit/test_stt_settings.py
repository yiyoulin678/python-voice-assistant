from __future__ import annotations

from pathlib import Path

from app.config.settings_service import AppSettingsService
from app.voice.stt_settings import DEFAULT_WHISPER_LANGUAGE, DEFAULT_WHISPER_MODEL_NAME


def test_load_stt_settings_from_system_config(tmp_path: Path) -> None:
    config_dir = tmp_path / "data" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "system_config.yaml").write_text(
        """
stt:
  enabled: true
  model_name: small
  language: ja
  input_device_index: 2
""".strip(),
        encoding="utf-8",
    )
    service = AppSettingsService(base_dir=tmp_path)
    settings = service.load_stt_settings()
    assert settings.enabled is True
    assert settings.model_name == "small"
    assert settings.language == "ja"
    assert settings.input_device_index == 2


def test_load_stt_settings_defaults_when_section_missing(tmp_path: Path) -> None:
    config_dir = tmp_path / "data" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "system_config.yaml").write_text("ui: {}\n", encoding="utf-8")
    service = AppSettingsService(base_dir=tmp_path)
    settings = service.load_stt_settings()
    assert settings.enabled is True
    assert settings.model_name == DEFAULT_WHISPER_MODEL_NAME
    assert settings.language == DEFAULT_WHISPER_LANGUAGE
    assert settings.input_device_index is None


def test_save_stt_settings_round_trip(tmp_path: Path) -> None:
    from app.voice.stt_settings import STTSettings

    config_dir = tmp_path / "data" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "system_config.yaml").write_text("stt:\n  enabled: false\n", encoding="utf-8")
    service = AppSettingsService(base_dir=tmp_path)
    service.save_stt_settings(
        STTSettings(enabled=True, model_name="base", language="zh", input_device_index=None)
    )
    loaded = service.load_stt_settings()
    assert loaded.enabled is True
    assert loaded.model_name == "base"
    assert loaded.language == "zh"
