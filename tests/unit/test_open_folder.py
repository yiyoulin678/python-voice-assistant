from __future__ import annotations

from pathlib import Path

import pytest

from app.platform.open_folder import open_folder_in_file_manager


def test_open_folder_creates_and_opens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "knowledge"
    opened: list[str] = []

    monkeypatch.setattr(
        "app.platform.open_folder.os.name",
        "nt",
    )
    monkeypatch.setattr(
        "app.platform.open_folder.os.startfile",
        lambda path: opened.append(path),
    )

    result = open_folder_in_file_manager(target, create=True)
    assert result == str(target.resolve())
    assert target.is_dir()
    assert opened == [str(target.resolve())]
