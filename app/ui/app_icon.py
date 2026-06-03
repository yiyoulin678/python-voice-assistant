from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap


def tray_icon_path(base_dir: Path) -> Path:
    return Path(base_dir) / "icon.png"


def load_tray_icon(base_dir: Path) -> QIcon | None:
    path = tray_icon_path(base_dir)
    if not path.is_file():
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return QIcon(pixmap)
