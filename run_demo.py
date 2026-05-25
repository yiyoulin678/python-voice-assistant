"""从任意位置启动 CLI：python run_demo.py session --text \"什么是死锁？\""""
import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if __name__ == "__main__":
    sys.argv[0] = str(_ROOT / "ai" / "demo_cli.py")
    runpy.run_module("ai.demo_cli", run_name="__main__")
