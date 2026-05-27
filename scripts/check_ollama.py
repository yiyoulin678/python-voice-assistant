"""检查 Ollama 与 qwen2.5:3b 是否可用。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from ai.llm import ollama_client


def main() -> int:
    print("检查地址:", OLLAMA_BASE_URL)
    print("目标模型:", OLLAMA_MODEL)
    if not ollama_client.is_available():
        print("[X] Ollama 未运行。请先执行: scripts\\start_ollama.bat")
        print(f"    或: third_party\\ollama\\bin\\ollama.exe pull {OLLAMA_MODEL}")
        return 1
    print("[OK] Ollama 服务正常")
    if not ollama_client.ensure_model_pulled():
        print(f"[X] 未找到模型，请执行: ollama pull {OLLAMA_MODEL}")
        return 1
    print("[OK] 模型已安装")
    reply = ollama_client.chat([{"role": "user", "content": "用一句话介绍你自己"}])
    print("测试回复:", reply[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
