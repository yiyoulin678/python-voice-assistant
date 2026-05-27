"""CosyVoice 零样本合成（由 ai/tts 子进程调用）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="CosyVoice zero-shot TTS")
    parser.add_argument("--text", required=True)
    parser.add_argument("--ref", required=True, help="参考音频 wav")
    parser.add_argument("--prompt-text", required=True, help="参考音频对应文本")
    parser.add_argument("--model-dir", required=True, help="相对 cosyvoice-root 的模型目录")
    parser.add_argument("--cosyvoice-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.cosyvoice_root).resolve()
    if not root.is_dir():
        print(f"CosyVoice 根目录不存在: {root}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "third_party" / "Matcha-TTS"))

    model_path = root / args.model_dir
    ref_path = Path(args.ref).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import torchaudio
        from cosyvoice.cli.cosyvoice import AutoModel
    except ImportError as exc:
        print(
            "无法导入 CosyVoice。请在 CosyVoice 目录安装依赖:\n"
            "  pip install -r third_party/CosyVoice/requirements.txt\n"
            f"详情: {exc}",
            file=sys.stderr,
        )
        return 1

    if not model_path.is_dir():
        print(f"模型目录不存在: {model_path}", file=sys.stderr)
        return 1
    if not ref_path.is_file():
        print(f"参考音频不存在: {ref_path}", file=sys.stderr)
        return 1

    cosyvoice = AutoModel(model_dir=str(model_path), fp16=False)
    # CPU 上 Qwen 权重常为 bfloat16，与 float32 输入不兼容
    if not __import__("torch").cuda.is_available():
        cosyvoice.model.llm.float()
        cosyvoice.model.flow.float()
        cosyvoice.model.hift.float()

    for _, output in enumerate(
        cosyvoice.inference_zero_shot(args.text, args.prompt_text, str(ref_path))
    ):
        torchaudio.save(str(out_path), output["tts_speech"], cosyvoice.sample_rate)
        break

    if not out_path.is_file() or out_path.stat().st_size == 0:
        print("未生成输出 wav", file=sys.stderr)
        return 1
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
