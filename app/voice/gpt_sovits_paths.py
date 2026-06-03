from __future__ import annotations

from pathlib import Path

from app.voice.tts_bundle import _resolve_extracted_root


def is_gpt_sovits_work_dir(path: Path) -> bool:
    root = path.resolve()
    return (root / "api_v2.py").is_file() and (root / "runtime" / "python.exe").is_file()


def resolve_gpt_sovits_work_dir(
    base_dir: Path,
    configured: Path | None = None,
) -> Path | None:
    """解析 GPT-SoVITS 整包目录（含 api_v2.py），优先项目内已安装整合包。"""

    if configured is not None and is_gpt_sovits_work_dir(configured):
        return configured.resolve()

    installed_base = base_dir / "data" / "tts_bundles" / "installed"
    if installed_base.is_dir():
        for key_dir in sorted(installed_base.iterdir()):
            if not key_dir.is_dir():
                continue
            try:
                root = _resolve_extracted_root(key_dir)
            except OSError:
                continue
            if is_gpt_sovits_work_dir(root):
                return root

    legacy_candidates = (
        base_dir.parent.parent / "Game" / "GPT-SoVITS" / "GPT-SoVITS-v2pro-20250604",
        Path("D:/Game/GPT-SoVITS/GPT-SoVITS-v2pro-20250604"),
    )
    for legacy in legacy_candidates:
        if is_gpt_sovits_work_dir(legacy):
            return legacy.resolve()

    return None
