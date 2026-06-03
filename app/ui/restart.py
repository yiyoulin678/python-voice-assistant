"""重启 Mutsuki 桌面进程。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.platform.win_console import gui_python_executable


def request_app_restart(
    parent: QWidget | None = None,
    *,
    base_dir: Path | None = None,
) -> bool:
    """启动新的 main.py 并退出当前进程。"""
    root = (base_dir or Path(__file__).resolve().parents[2]).resolve()
    main_py = root / "main.py"
    if not main_py.is_file():
        if parent is not None:
            QMessageBox.warning(parent, "重启失败", f"找不到入口文件：{main_py}")
        return False

    if parent is not None:
        close_tools = getattr(parent, "close_external_tools", None)
        if callable(close_tools):
            close_tools()

    ok = QProcess.startDetached(gui_python_executable(), [str(main_py)], str(root))
    if not ok:
        if parent is not None:
            QMessageBox.warning(
                parent,
                "重启失败",
                "无法启动新进程，请手动关闭后重新运行 start.bat。",
            )
        return False

    application = QApplication.instance()
    if application is not None:
        application.quit()
    return True
