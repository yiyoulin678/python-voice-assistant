from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.ui.restart import request_app_restart


def test_request_app_restart_starts_detached_process(tmp_path: Path) -> None:
    main_py = tmp_path / "main.py"
    main_py.write_text("print('ok')\n", encoding="utf-8")
    parent = MagicMock()
    app = MagicMock()
    with patch("app.ui.restart.QProcess.startDetached", return_value=True) as start:
        with patch("app.ui.restart.QApplication.instance", return_value=app):
            assert request_app_restart(parent=parent, base_dir=tmp_path)
    start.assert_called_once()
    parent.close_external_tools.assert_called_once()
    app.quit.assert_called_once()


def test_request_app_restart_fails_when_main_missing(tmp_path: Path) -> None:
    assert not request_app_restart(base_dir=tmp_path)
