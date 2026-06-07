from __future__ import annotations

import os
import webbrowser
from pathlib import Path


def open_folder_in_file_manager(path: Path, *, create: bool = False) -> str:
    """在系统文件管理器中打开文件夹；可选在不存在时先创建。"""
    folder = path.expanduser().resolve()
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    if not folder.exists():
        raise FileNotFoundError(f"文件夹不存在：{folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"不是文件夹：{folder}")

    if os.name == "nt":
        os.startfile(str(folder))  # type: ignore[attr-defined]
    else:
        opened = webbrowser.open(folder.as_uri())
        if not opened:
            raise OSError(f"无法打开文件夹：{folder}")
    return str(folder)
