from __future__ import annotations

import sys
from pathlib import Path


def hide_attached_console() -> None:
    """Windows 下隐藏已附加的控制台窗口（python.exe 启动时）。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
    except Exception:
        return


def gui_python_executable() -> str:
    """优先使用 pythonw.exe，避免 GUI 进程弹出控制台。"""
    executable = Path(sys.executable)
    if executable.name.lower() == "python.exe":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.is_file():
            return str(pythonw)
    return sys.executable
