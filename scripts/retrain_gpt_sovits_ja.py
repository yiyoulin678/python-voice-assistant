"""日语素材：ASR 重标注 → 格式化 → SoVITS/GPT 训练 → 更新小音配置。"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

GS_ROOT = Path(r"D:\Game\GPT-SoVITS\GPT-SoVITS-v2pro-20250604")
VA_ROOT = Path(__file__).resolve().parents[1]
PY = GS_ROOT / "runtime" / "python.exe"
SLICER = GS_ROOT / "output" / "slicer_opt"
ASR_OUT = GS_ROOT / "output" / "asr_opt_ja"
LIST_RAW = ASR_OUT / "slicer_opt.list"
LIST_CLEAN = ASR_OUT / "slicer_opt_ja_clean.list"
EXP = "NatsumeAnan_ja"
OPT_DIR = GS_ROOT / "logs" / EXP
VERSION = "v2Pro"
LOG = VA_ROOT / "logs" / "retrain_ja.log"


def log(msg: str) -> None:
    line = f"[retrain_ja] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    log("RUN: " + " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd or GS_ROOT), check=True)


def step_asr(force: bool = False) -> None:
    if LIST_RAW.is_file() and not force:
        log(f"跳过 ASR，已存在 {LIST_RAW}")
        return
    ASR_OUT.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(PY),
            "tools/asr/fasterwhisper_asr.py",
            "-i",
            str(SLICER),
            "-o",
            str(ASR_OUT),
            "-l",
            "ja",
            "-s",
            "large-v3",
            "-p",
            "float16",
        ]
    )


def step_clean() -> int:
    lines = LIST_RAW.read_text(encoding="utf-8").strip().splitlines()
    out: list[str] = []
    for line in lines:
        parts = line.split("|")
        if len(parts) < 4:
            continue
        wav, _spk, _lang, text = parts[0], parts[1], parts[2], "|".join(parts[3:])
        text = text.strip()
        if len(text) < 3:
            continue
        wav_path = Path(wav)
        if not wav_path.is_file():
            wav_path = GS_ROOT / wav
        if not wav_path.is_file():
            continue
        try:
            with wave.open(str(wav_path), "rb") as w:
                dur = w.getnframes() / float(w.getframerate())
        except OSError:
            continue
        if dur < 2.0 or dur > 12.0:
            continue
        rel = f"output/slicer_opt/{wav_path.name}"
        out.append(f"{rel}|slicer_opt|JA|{text}")
    LIST_CLEAN.write_text("\n".join(out) + "\n", encoding="utf-8")
    log(f"清洗完成: {len(out)} / {len(lines)} -> {LIST_CLEAN}")
    return len(out)


def _env_base() -> dict[str, str]:
    return {
        "inp_text": str(LIST_CLEAN),
        "inp_wav_dir": str(SLICER),
        "exp_name": EXP,
        "opt_dir": str(OPT_DIR),
        "bert_pretrained_dir": str(GS_ROOT / "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"),
        "cnhubert_base_dir": str(GS_ROOT / "GPT_SoVITS/pretrained_models/chinese-hubert-base"),
        "sv_path": str(GS_ROOT / "GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt"),
        "version": VERSION,
        "is_half": "True",
        "pretrained_s2G": str(GS_ROOT / "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth"),
        "s2config_path": str(GS_ROOT / "GPT_SoVITS/configs/s2v2Pro.json"),
        "i_part": "0",
        "all_parts": "1",
        "_CUDA_VISIBLE_DEVICES": "0",
    }


def step_format() -> None:
    env = os.environ.copy()
    env.update(_env_base())
    OPT_DIR.mkdir(parents=True, exist_ok=True)

    for script in (
        "GPT_SoVITS/prepare_datasets/1-get-text.py",
        "GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py",
        "GPT_SoVITS/prepare_datasets/2-get-sv.py",
        "GPT_SoVITS/prepare_datasets/3-get-semantic.py",
    ):
        log(f"格式化: {script}")
        subprocess.run([str(PY), "-s", script], cwd=str(GS_ROOT), env=env, check=True)

    part = OPT_DIR / "2-name2text-0.txt"
    merged = OPT_DIR / "2-name2text.txt"
    if part.is_file():
        merged.write_text(part.read_text(encoding="utf-8"), encoding="utf-8")
        part.unlink(missing_ok=True)

    sem_parts = [OPT_DIR / "6-name2semantic-0.tsv"]
    sem_merged = OPT_DIR / "6-name2semantic.tsv"
    rows = ["item_name\tsemantic_audio"]
    for p in sem_parts:
        if p.is_file():
            rows.extend(p.read_text(encoding="utf-8").strip().splitlines())
            p.unlink(missing_ok=True)
    sem_merged.write_text("\n".join(rows) + "\n", encoding="utf-8")
    log("格式化完成")


def step_sovits(epochs: int = 8, batch_size: int = 1) -> None:
    cfg_path = GS_ROOT / "GPT_SoVITS/configs/s2v2Pro.json"
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    s2d = str(GS_ROOT / "GPT_SoVITS/pretrained_models/v2Pro/s2Dv2Pro.pth")
    data["train"]["batch_size"] = batch_size
    data["train"]["epochs"] = epochs
    data["train"]["save_every_epoch"] = 4
    data["train"]["fp16_run"] = True
    data["train"]["pretrained_s2G"] = str(GS_ROOT / "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth")
    data["train"]["pretrained_s2D"] = s2d
    data["train"]["gpu_numbers"] = "0"
    data["data"]["exp_dir"] = str(OPT_DIR)
    data["s2_ckpt_dir"] = str(OPT_DIR)
    data["save_weight_dir"] = "SoVITS_weights_v2Pro"
    data["name"] = EXP
    data["version"] = VERSION
    data["model"]["version"] = VERSION
    tmp = GS_ROOT / "TEMP" / "tmp_s2_ja.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    OPT_DIR.mkdir(parents=True, exist_ok=True)
    (OPT_DIR / "logs_s2_v2Pro").mkdir(parents=True, exist_ok=True)
    run([str(PY), "-s", "GPT_SoVITS/s2_train.py", "--config", str(tmp)])


def step_gpt(epochs: int = 15, batch_size: int = 4) -> None:
    import yaml

    cfg_in = GS_ROOT / "GPT_SoVITS/configs/s1longer-v2.yaml"
    data = yaml.safe_load(cfg_in.read_text(encoding="utf-8"))
    data["train"]["batch_size"] = batch_size
    data["train"]["epochs"] = epochs
    data["train"]["save_every_n_epoch"] = 5
    data["train"]["if_save_every_weights"] = True
    data["train"]["if_save_latest"] = True
    data["train"]["half_weights_save_dir"] = "GPT_weights_v2Pro"
    data["train"]["exp_name"] = EXP
    data["pretrained_s1"] = str(GS_ROOT / "GPT_SoVITS/pretrained_models/s1v3.ckpt")
    data["train_semantic_path"] = str(OPT_DIR / "6-name2semantic.tsv")
    data["train_phoneme_path"] = str(OPT_DIR / "2-name2text.txt")
    data["output_dir"] = str(OPT_DIR / "logs_s1_v2Pro")
    tmp = GS_ROOT / "TEMP" / "tmp_s1_ja.yaml"
    tmp.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    (OPT_DIR / "logs_s1_v2Pro").mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["_CUDA_VISIBLE_DEVICES"] = "0"
    env["hz"] = "25hz"
    subprocess.run(
        [str(PY), "-s", "GPT_SoVITS/s1_train.py", "--config_file", str(tmp)],
        cwd=str(GS_ROOT),
        env=env,
        check=True,
    )


def _latest_weight(pattern: str, folder: Path) -> Path | None:
    if not folder.is_dir():
        return None
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def step_update_configs() -> None:
    gpt_dir = GS_ROOT / "GPT_weights_v2Pro"
    sovits_dir = GS_ROOT / "SoVITS_weights_v2Pro"
    gpt = _latest_weight(f"{EXP}*.ckpt", gpt_dir) or _latest_weight(f"{EXP}*.ckpt", gpt_dir)
    sov = _latest_weight(f"{EXP}*.pth", sovits_dir)
    if not gpt:
        gpt = max(gpt_dir.glob(f"{EXP}*.ckpt"), default=None, key=lambda p: p.stat().st_mtime)
    if not sov:
        sov = max(sovits_dir.glob(f"{EXP}*.pth"), default=None, key=lambda p: p.stat().st_mtime)
    if not gpt or not sov:
        raise FileNotFoundError(f"未找到训练权重 {EXP}，请确认训练已完成")

    ref_wav, prompt_text = pick_reference()
    rel_gpt = gpt.relative_to(GS_ROOT).as_posix()
    rel_sov = sov.relative_to(GS_ROOT).as_posix()

    yaml_path = GS_ROOT / "GPT_SoVITS/configs/tts_infer.yaml"
    text = yaml_path.read_text(encoding="utf-8")
    block = (
        "custom:\n"
        f"  bert_base_path: GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large\n"
        f"  cnhuhbert_base_path: GPT_SoVITS/pretrained_models/chinese-hubert-base\n"
        f"  device: cuda\n"
        f"  is_half: true\n"
        f"  t2s_weights_path: {rel_gpt}\n"
        f"  version: v2Pro\n"
        f"  vits_weights_path: {rel_sov}\n"
    )
    text = re.sub(r"custom:\n(?:  .+\n)+", block, text, count=1)
    yaml_path.write_text(text, encoding="utf-8")
    log(f"tts_infer.yaml -> GPT={rel_gpt}, SoVITS={rel_sov}")

    settings_path = VA_ROOT / "config" / "ai_settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    gs = settings.setdefault("gpt_sovits", {})
    gs["prompt_lang"] = "ja"
    gs["text_lang"] = "zh"
    gs["prompt_text"] = prompt_text
    gs["comment_weights"] = f"{gpt.name} + {sov.name} (日语标注重训)"
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ref_dst = VA_ROOT / "resources" / "voice_ref" / "reference.wav"
    ref_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ref_wav, ref_dst)
    log(f"reference.wav <- {ref_wav.name}, prompt={prompt_text[:40]}...")


def pick_reference() -> tuple[Path, str]:
    """选 3~8 秒、文本适中的日语参考片段。"""
    if not LIST_CLEAN.is_file():
        raise FileNotFoundError(LIST_CLEAN)
    best: tuple[float, Path, str] | None = None
    for line in LIST_CLEAN.read_text(encoding="utf-8").splitlines():
        parts = line.split("|")
        if len(parts) < 4:
            continue
        rel, _spk, _lang, text = parts[0], parts[1], parts[2], "|".join(parts[3:])
        text = text.strip()
        wav = GS_ROOT / rel.replace("/", os.sep)
        if not wav.is_file():
            continue
        with wave.open(str(wav), "rb") as w:
            dur = w.getnframes() / float(w.getframerate())
        if dur < 3.0 or dur > 8.0:
            continue
        if len(text) < 8 or len(text) > 60:
            continue
        score = -abs(dur - 5.0) + min(len(text), 40) * 0.05
        if best is None or score > best[0]:
            best = (score, wav, text)
    if best is None:
        line = LIST_CLEAN.read_text(encoding="utf-8").splitlines()[0]
        rel, *_rest, text = line.split("|", 3)
        return GS_ROOT / rel.replace("/", os.sep), text.strip()
    return best[1], best[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step",
        choices=["all", "asr", "clean", "format", "sovits", "gpt", "config"],
        default="all",
    )
    parser.add_argument("--force-asr", action="store_true")
    args = parser.parse_args()

    if not PY.is_file():
        print("未找到 GPT-SoVITS runtime/python.exe", file=sys.stderr)
        return 1

    steps = {
        "asr": lambda: step_asr(args.force_asr),
        "clean": step_clean,
        "format": step_format,
        "sovits": step_sovits,
        "gpt": step_gpt,
        "config": step_update_configs,
    }
    order = ["asr", "clean", "format", "sovits", "gpt", "config"] if args.step == "all" else [args.step]
    for name in order:
        log(f"=== {name} ===")
        steps[name]()
    log("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
