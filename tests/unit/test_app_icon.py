from __future__ import annotations

from pathlib import Path

from app.ui.app_icon import load_tray_icon, tray_icon_path


def test_load_tray_icon_missing(tmp_path: Path) -> None:
    assert load_tray_icon(tmp_path) is None
    assert tray_icon_path(tmp_path) == tmp_path / "icon.png"
