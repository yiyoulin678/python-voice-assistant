from pathlib import Path

from app.voice.gpt_sovits_paths import is_gpt_sovits_work_dir, resolve_gpt_sovits_work_dir


def test_resolve_prefers_valid_configured_dir(tmp_path: Path) -> None:
    work_dir = tmp_path / "gpt-sovits"
    (work_dir / "runtime").mkdir(parents=True)
    (work_dir / "runtime" / "python.exe").write_text("", encoding="utf-8")
    (work_dir / "api_v2.py").write_text("fake", encoding="utf-8")

    resolved = resolve_gpt_sovits_work_dir(tmp_path, work_dir)
    assert resolved == work_dir.resolve()


def test_resolve_falls_back_to_installed_bundle(tmp_path: Path) -> None:
    installed = tmp_path / "data" / "tts_bundles" / "installed" / "gpt_sovits_v2pro"
    root = installed / "GPT-SoVITS-v2pro-20250604"
    (root / "runtime").mkdir(parents=True)
    (root / "runtime" / "python.exe").write_text("", encoding="utf-8")
    (root / "api_v2.py").write_text("fake", encoding="utf-8")

    missing = tmp_path / "data" / "tts_bundles" / "installed" / "missing"
    resolved = resolve_gpt_sovits_work_dir(tmp_path, missing)
    assert resolved == root.resolve()


def test_is_gpt_sovits_work_dir_requires_api_and_runtime(tmp_path: Path) -> None:
    work_dir = tmp_path / "incomplete"
    work_dir.mkdir()
    (work_dir / "api_v2.py").write_text("fake", encoding="utf-8")
    assert not is_gpt_sovits_work_dir(work_dir)
