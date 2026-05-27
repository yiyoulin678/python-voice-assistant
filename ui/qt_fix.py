"""修复 Windows 上 PyQt5 找不到 platforms/qwindows.dll 的问题。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def fix_qt_plugin_path() -> None:
    """必须在 QApplication 创建之前调用。"""
    try:
        import PyQt5
    except ImportError:
        return

    qt5_root = Path(PyQt5.__file__).resolve().parent / "Qt5"
    plugins_dir = qt5_root / "plugins"
    platforms_dir = plugins_dir / "platforms"
    bin_dir = qt5_root / "bin"

    if not platforms_dir.is_dir():
        return

    os.environ["QT_PLUGIN_PATH"] = str(plugins_dir)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_dir)

    if not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "windows"

    bin_str = str(bin_dir)
    path = os.environ.get("PATH", "")
    if bin_dir.is_dir() and bin_str not in path:
        os.environ["PATH"] = bin_str + os.pathsep + path

    # PyQt5 高版本可在导入 QtWidgets 后使用
    try:
        from PyQt5.QtCore import QCoreApplication

        QCoreApplication.addLibraryPath(str(plugins_dir))
    except Exception:
        pass
