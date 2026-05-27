import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / "data" / "temp" / "cosyvoice_test.wav"
out.parent.mkdir(parents=True, exist_ok=True)
cmd = [
    sys.executable,
    str(root / "scripts" / "cosyvoice_speak.py"),
    "--text",
    "你好，我是小音。",
    "--ref",
    str(root / "resources" / "voice_ref" / "reference.wav"),
    "--prompt-text",
    "希望你以后能够做的比我还好呦。",
    "--model-dir",
    "pretrained_models/CosyVoice2-0.5B",
    "--cosyvoice-root",
    str(root / "third_party" / "CosyVoice"),
    "--out",
    str(out),
]
raise SystemExit(subprocess.call(cmd))
