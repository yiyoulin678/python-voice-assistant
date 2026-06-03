from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from app.voice.stt_settings import STTSettings
from app.voice.tts import TTS_PROVIDER_NONE
from tests.unit.test_tts import _minimal_tts_settings


def test_refresh_stt_input_devices_fills_combo() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qtwidgets = pytest.importorskip("PySide6.QtWidgets")
    if not hasattr(qtwidgets, "QApplication"):
        pytest.skip("当前测试环境只提供了 PySide6 stub。")

    from app.llm.api_client import ApiSettings
    from app.ui.settings_dialog import SettingsDialog
    QApplication = qtwidgets.QApplication
    app = QApplication.instance() or QApplication([])

    fake_devices = [
        {"index": 1, "name": "Mic A", "channels": 1, "is_default": True},
        {"index": 3, "name": "Mic B", "channels": 2, "is_default": False},
    ]

    with patch("app.ui.settings_dialog.audio_io.list_input_devices", return_value=fake_devices):
        with patch("app.ui.settings_dialog.audio_io.configure_audio_paths"):
            dialog = SettingsDialog(
                api_settings=ApiSettings(
                    base_url="https://api.example.com/v1",
                    api_key="key",
                    model="model",
                ),
                tts_settings=replace(
                    _minimal_tts_settings(provider=TTS_PROVIDER_NONE),
                    enabled=False,
                ),
                base_dir=Path("."),
                stt_settings=STTSettings(enabled=True, input_device_index=3),
            )

    combo = dialog.stt_input_device_combo
    assert combo.count() == 3
    assert combo.itemText(0) == "系统默认"
    assert "[1] Mic A ★" in combo.itemText(1)
    assert combo.currentData() == 3

    dialog.deleteLater()
    app.processEvents()


def test_validated_stt_settings_reads_selected_device() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qtwidgets = pytest.importorskip("PySide6.QtWidgets")
    if not hasattr(qtwidgets, "QApplication"):
        pytest.skip("当前测试环境只提供了 PySide6 stub。")

    from app.llm.api_client import ApiSettings
    from app.ui.settings_dialog import SettingsDialog
    QApplication = qtwidgets.QApplication
    app = QApplication.instance() or QApplication([])

    with patch("app.ui.settings_dialog.audio_io.list_input_devices", return_value=[]):
        with patch("app.ui.settings_dialog.audio_io.configure_audio_paths"):
            dialog = SettingsDialog(
                api_settings=ApiSettings(
                    base_url="https://api.example.com/v1",
                    api_key="key",
                    model="model",
                ),
                tts_settings=replace(
                    _minimal_tts_settings(provider=TTS_PROVIDER_NONE),
                    enabled=False,
                ),
                base_dir=Path("."),
            )

    dialog.stt_input_device_combo.setCurrentIndex(0)
    settings = dialog._validated_stt_settings()
    assert settings is not None
    assert settings.input_device_index is None

    dialog.deleteLater()
    app.processEvents()
