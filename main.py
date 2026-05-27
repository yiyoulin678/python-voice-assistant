"""语音 AI 虚拟女友 — 桌面程序入口。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 确保日志、数据目录存在（与 utils.config 一致）
(ROOT / "logs").mkdir(parents=True, exist_ok=True)
(ROOT / "data").mkdir(parents=True, exist_ok=True)


def main() -> int:
    try:
        from ui.qt_fix import fix_qt_plugin_path

        fix_qt_plugin_path()
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("未安装 PyQt5，请执行: pip install PyQt5")
        return 1

    try:
        from utils import logger as _  # noqa: F401 — 初始化 logging
    except Exception:
        pass

    from ui.login_window import LoginWindow

    app = QApplication(sys.argv)
    app.setApplicationName("语音AI虚拟女友")
    app.setStyle("Fusion")
    window = LoginWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
