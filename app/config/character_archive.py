from __future__ import annotations

import json
import re
import shutil
import stat
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from app.config.character_loader import CharacterLive2D, CharacterProfile, CharacterRegistry


ARCHIVE_FORMAT = "sakura.character.archive"
ARCHIVE_VERSION = 1
ARCHIVE_MANIFEST = "manifest.json"
ARCHIVE_CHARACTER_ROOT = PurePosixPath("character")

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_SAFE_CHARACTER_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class CharacterArchiveError(RuntimeError):
    """Mutsuki 角色归档包格式错误或导入导出失败。"""


@dataclass(frozen=True)
class CharacterArchiveImportResult:
    """角色归档导入后的结果。"""

    profile: CharacterProfile
    character_id: str
    display_name: str
    package_dir: Path


def import_character_archive(path: Path, base_dir: Path) -> CharacterArchiveImportResult:
    """导入 Mutsuki 自有 .char 角色归档包。"""

    archive_path = Path(path)
    if not archive_path.exists():
        raise FileNotFoundError(f"角色包不存在：{archive_path}")

    characters_dir = base_dir / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            _validate_zip_members(zf)
            manifest = _read_manifest(zf)
            character_data = _validated_character_data(manifest)

            original_id = _required_character_id(character_data, "character.id")
            display_name = _required_text(character_data, "display_name", "character.display_name")
            target_id = _unique_character_id(original_id, characters_dir)
            target_name = _unique_display_name(display_name, characters_dir)
            target_dir = characters_dir / target_id

            temp_root = characters_dir / f"char_import_{uuid.uuid4().hex}"
            try:
                temp_root.mkdir(parents=True, exist_ok=False)
                extract_dir = temp_root / "extract"
                staging_dir = temp_root / "package"
                zf.extractall(extract_dir)

                source_character_dir = extract_dir / ARCHIVE_CHARACTER_ROOT.as_posix()
                if not source_character_dir.is_dir():
                    raise CharacterArchiveError("角色包缺少 character/ 资源目录。")

                shutil.copytree(source_character_dir, staging_dir)
                normalized_character = _normalized_import_character_data(
                    character_data,
                    character_id=target_id,
                    display_name=target_name,
                    package_dir=staging_dir,
                )
                _write_character_manifest(staging_dir, normalized_character)

                moved = False
                try:
                    staging_dir.rename(target_dir)
                    moved = True
                    profile = CharacterRegistry(base_dir).get(target_id)
                except Exception:
                    if moved and target_dir.exists():
                        shutil.rmtree(target_dir, ignore_errors=True)
                    raise
            finally:
                shutil.rmtree(temp_root, ignore_errors=True)
    except zipfile.BadZipFile as exc:
        raise CharacterArchiveError("不是有效的 Mutsuki .char ZIP 包。") from exc

    return CharacterArchiveImportResult(
        profile=profile,
        character_id=profile.id,
        display_name=profile.display_name,
        package_dir=profile.package_dir,
    )


def export_character_archive(profile: CharacterProfile, output_path: Path) -> None:
    """导出 Mutsuki 角色包为自有 .char 归档。"""

    destination = Path(output_path)
    if destination.suffix.lower() != ".char":
        destination = destination.with_suffix(".char")
    destination.parent.mkdir(parents=True, exist_ok=True)

    package_files = [
        path
        for path in profile.package_dir.rglob("*")
        if path.is_file() and _resolved(path) != _resolved(destination)
    ]
    package_archive_names = {
        _archive_path_for_package_file(profile.package_dir, path).as_posix()
        for path in package_files
    }
    external_paths: dict[Path, PurePosixPath] = {}

    def archive_path_for_resource(path: Path | None, kind: str) -> str | None:
        if path is None:
            return None
        archive_path = _archive_path_for_profile_resource(
            profile.package_dir,
            path,
            kind=kind,
            package_archive_names=package_archive_names,
            external_paths=external_paths,
        )
        return archive_path.as_posix()

    character_manifest: dict[str, Any] = {
        "id": profile.id,
        "display_name": profile.display_name,
        "initial_message": profile.initial_message,
        "card": archive_path_for_resource(profile.card_path, "card"),
        "portrait": {
            "default": archive_path_for_resource(profile.default_portrait_path, "portrait"),
            "expressions": {
                label: archive_path_for_resource(path, "portrait")
                for label, path in profile.expression_portraits.items()
            },
        },
        "reply": {"tones": [*profile.reply_tones]},
    }
    if profile.voice is not None:
        character_manifest["voice"] = {
            "gpt_model": archive_path_for_resource(profile.voice.gpt_model_path, "voice/models"),
            "sovits_model": archive_path_for_resource(profile.voice.sovits_model_path, "voice/models"),
            "tone_refs": archive_path_for_resource(profile.voice.tone_ref_path, "voice/refs"),
            "ref_lang": profile.voice.ref_lang,
            "text_lang": profile.voice.text_lang,
        }
    live2d_manifest = _export_live2d_manifest(
        profile,
        package_archive_names=package_archive_names,
        external_paths=external_paths,
    )
    if live2d_manifest is not None:
        character_manifest["live2d"] = live2d_manifest

    archive_manifest = {
        "format": ARCHIVE_FORMAT,
        "version": ARCHIVE_VERSION,
        "character": character_manifest,
    }

    temp_output = destination.with_name(f".{destination.name}.tmp")
    try:
        with zipfile.ZipFile(temp_output, "w", zipfile.ZIP_DEFLATED) as zf:
            written: set[str] = set()
            for source in package_files:
                _write_zip_file(
                    zf,
                    source,
                    _archive_path_for_package_file(profile.package_dir, source),
                    written,
                )
            for source, archive_path in external_paths.items():
                _write_zip_file(zf, source, archive_path, written)
            zf.writestr(
                ARCHIVE_MANIFEST,
                json.dumps(archive_manifest, ensure_ascii=False, indent=2),
            )
        temp_output.replace(destination)
    finally:
        temp_output.unlink(missing_ok=True)


def _validate_zip_members(zf: zipfile.ZipFile) -> None:
    found_manifest = False
    for info in zf.infolist():
        member = str(info.filename or "").replace("\\", "/").rstrip("/")
        if not member:
            raise CharacterArchiveError("角色包包含空 ZIP 成员名。")
        rel = _safe_archive_path(member, "zip member")
        if _is_zip_symlink(info):
            raise CharacterArchiveError(f"角色包不允许包含符号链接：{member}")
        if rel == PurePosixPath(ARCHIVE_MANIFEST):
            found_manifest = True
            continue
        if rel.parts[0] != ARCHIVE_CHARACTER_ROOT.as_posix():
            raise CharacterArchiveError(f"角色包资源必须位于 character/ 下：{member}")
    if not found_manifest:
        raise CharacterArchiveError("角色包缺少 manifest.json。")


def _read_manifest(zf: zipfile.ZipFile) -> dict[str, Any]:
    try:
        raw = zf.read(ARCHIVE_MANIFEST)
    except KeyError as exc:
        raise CharacterArchiveError("角色包缺少 manifest.json。") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CharacterArchiveError("manifest.json 不是有效的 UTF-8 JSON。") from exc
    if not isinstance(data, dict):
        raise CharacterArchiveError("manifest.json 必须是 JSON 对象。")
    return data


def _validated_character_data(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("format") != ARCHIVE_FORMAT:
        raise CharacterArchiveError("不支持的角色包格式。")
    if manifest.get("version") != ARCHIVE_VERSION:
        raise CharacterArchiveError("不支持的角色包版本。")
    character_data = manifest.get("character")
    if not isinstance(character_data, dict):
        raise CharacterArchiveError("manifest.json 缺少 character 对象。")
    return dict(character_data)


def _normalized_import_character_data(
    character_data: dict[str, Any],
    *,
    character_id: str,
    display_name: str,
    package_dir: Path,
) -> dict[str, Any]:
    card = _package_path_text(_required_archive_resource(character_data, "card", "character.card"))
    portrait_data = _required_mapping(character_data, "portrait", "character.portrait")
    default_portrait = _package_path_text(
        _required_archive_resource(portrait_data, "default", "character.portrait.default")
    )
    expressions = _normalized_expressions(portrait_data.get("expressions", {}))

    normalized: dict[str, Any] = {
        "id": character_id,
        "display_name": display_name,
        "initial_message": _optional_text(character_data, "initial_message", "……起動した。用事があるなら、呼んで。"),
        "card": card,
        "portrait": {
            "default": default_portrait,
            "expressions": expressions,
        },
    }

    reply_data = character_data.get("reply")
    tones = _normalized_reply_tones(reply_data)
    if tones:
        normalized["reply"] = {"tones": tones}

    voice_data = character_data.get("voice")
    if voice_data is not None:
        normalized["voice"] = _normalized_voice(voice_data)

    live2d_data = character_data.get("live2d")
    if live2d_data is not None:
        normalized["live2d"] = _normalized_live2d(live2d_data)

    _validate_referenced_files(package_dir, normalized)
    return normalized


def _normalized_expressions(raw_expressions: Any) -> dict[str, str]:
    if raw_expressions is None:
        return {}
    if not isinstance(raw_expressions, dict):
        raise CharacterArchiveError("character.portrait.expressions 必须是对象。")
    expressions: dict[str, str] = {}
    for label, path_text in raw_expressions.items():
        if not isinstance(label, str) or not label.strip():
            raise CharacterArchiveError("character.portrait.expressions 的标签必须是非空字符串。")
        expressions[label.strip()] = _package_path_text(
            _archive_resource_path(path_text, f"character.portrait.expressions.{label}")
        )
    return expressions


def _normalized_reply_tones(reply_data: Any) -> list[str]:
    if not isinstance(reply_data, dict):
        return []
    raw_tones = reply_data.get("tones")
    if not isinstance(raw_tones, list):
        return []
    return [tone.strip() for tone in raw_tones if isinstance(tone, str) and tone.strip()]


def _normalized_voice(voice_data: Any) -> dict[str, str]:
    if not isinstance(voice_data, dict):
        raise CharacterArchiveError("character.voice 必须是对象。")
    normalized: dict[str, str] = {
        "tone_refs": _package_path_text(
            _required_archive_resource(voice_data, "tone_refs", "character.voice.tone_refs")
        ),
        "ref_lang": _optional_text(voice_data, "ref_lang", "ja"),
        "text_lang": _optional_text(voice_data, "text_lang", "ja"),
    }
    for key in ("gpt_model", "sovits_model"):
        value = voice_data.get(key)
        if isinstance(value, str) and value.strip():
            normalized[key] = _package_path_text(_archive_resource_path(value, f"character.voice.{key}"))
    return normalized


def _validate_referenced_files(package_dir: Path, character_data: dict[str, Any]) -> None:
    paths = [
        ("角色卡", character_data["card"]),
        ("默认立绘", character_data["portrait"]["default"]),
    ]
    for label, path_text in character_data["portrait"].get("expressions", {}).items():
        paths.append((f"{label} 表情立绘", path_text))
    voice_data = character_data.get("voice")
    if isinstance(voice_data, dict):
        paths.append(("语气参考表", voice_data["tone_refs"]))
        for key, label in (("gpt_model", "GPT 模型"), ("sovits_model", "SoVITS 模型")):
            if key in voice_data:
                paths.append((label, voice_data[key]))
    live2d_data = character_data.get("live2d")
    if isinstance(live2d_data, dict) and live2d_data.get("model"):
        model_rel = str(live2d_data["model"])
        paths.append(("Live2D 模型", model_rel))
        idle_motion = live2d_data.get("idle_motion")
        if isinstance(idle_motion, str) and idle_motion.strip():
            model_path = package_dir / _safe_package_path(model_rel, "Live2D 模型")
            idle_rel = (model_path.parent / idle_motion.strip()).relative_to(package_dir)
            paths.append(("Live2D 闲置动作", idle_rel.as_posix()))
    for label, path_text in paths:
        path = package_dir / _safe_package_path(path_text, label)
        if not path.is_file():
            raise CharacterArchiveError(f"{label}不存在：{path}")


def _write_character_manifest(package_dir: Path, character_data: dict[str, Any]) -> None:
    (package_dir / "character.json").write_text(
        json.dumps(character_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _required_mapping(data: dict[str, Any], key: str, field_name: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise CharacterArchiveError(f"{field_name} 必须是对象。")
    return dict(value)


def _required_archive_resource(data: dict[str, Any], key: str, field_name: str) -> PurePosixPath:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CharacterArchiveError(f"{field_name} 必须是非空字符串。")
    return _archive_resource_path(value, field_name)


def _archive_resource_path(value: Any, field_name: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise CharacterArchiveError(f"{field_name} 必须是非空字符串。")
    rel = _safe_archive_path(value.strip(), field_name)
    if rel.parts[0] != ARCHIVE_CHARACTER_ROOT.as_posix() or len(rel.parts) < 2:
        raise CharacterArchiveError(f"{field_name} 必须位于 character/ 下。")
    return rel


def _safe_archive_path(value: str, field_name: str) -> PurePosixPath:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw:
        raise CharacterArchiveError(f"{field_name} 不能为空。")
    if "\x00" in raw or raw.startswith("/") or _WINDOWS_DRIVE_RE.match(raw):
        raise CharacterArchiveError(f"{field_name} 必须是安全的相对路径：{value!r}")
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise CharacterArchiveError(f"{field_name} 包含不安全路径片段：{value!r}")
    return PurePosixPath(*parts)


def _safe_package_path(value: str, field_name: str) -> Path:
    rel = _safe_archive_path(value, field_name)
    if rel.parts and rel.parts[0] == ARCHIVE_CHARACTER_ROOT.as_posix():
        raise CharacterArchiveError(f"{field_name} 应为角色包内相对路径，不应包含 character/ 前缀。")
    return Path(*rel.parts)


def _package_path_text(archive_path: PurePosixPath) -> str:
    if archive_path.parts[0] != ARCHIVE_CHARACTER_ROOT.as_posix() or len(archive_path.parts) < 2:
        raise CharacterArchiveError(f"归档路径必须位于 character/ 下：{archive_path}")
    return PurePosixPath(*archive_path.parts[1:]).as_posix()


def _required_character_id(data: dict[str, Any], field_name: str) -> str:
    value = data.get("id")
    if not isinstance(value, str) or not value.strip():
        raise CharacterArchiveError(f"{field_name} 必须是非空字符串。")
    character_id = value.strip()
    if (
        "\x00" in character_id
        or "/" in character_id
        or "\\" in character_id
        or character_id in (".", "..")
        or _WINDOWS_DRIVE_RE.match(character_id)
        or not _SAFE_CHARACTER_ID_RE.match(character_id)
    ):
        raise CharacterArchiveError(f"{field_name} 只能包含字母、数字、下划线、点和横线。")
    return character_id


def _required_text(data: dict[str, Any], key: str, field_name: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CharacterArchiveError(f"{field_name} 必须是非空字符串。")
    return value.strip()


def _optional_text(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _unique_character_id(character_id: str, characters_dir: Path) -> str:
    used = {path.name for path in characters_dir.iterdir() if path.is_dir()}
    if character_id not in used:
        return character_id
    index = 1
    while f"{character_id}_{index}" in used:
        index += 1
    return f"{character_id}_{index}"


def _unique_display_name(display_name: str, characters_dir: Path) -> str:
    used = _existing_display_names(characters_dir)
    if display_name not in used:
        return display_name
    index = 1
    while f"{display_name}（{index}）" in used:
        index += 1
    return f"{display_name}（{index}）"


def _existing_display_names(characters_dir: Path) -> set[str]:
    names: set[str] = set()
    for manifest_path in characters_dir.glob("*/character.json"):
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict):
            name = raw.get("display_name")
            if isinstance(name, str) and name.strip():
                names.add(name.strip())
    return names


def _archive_path_for_package_file(package_dir: Path, source: Path) -> PurePosixPath:
    rel = _resolved(source).relative_to(_resolved(package_dir))
    archive_path = PurePosixPath(ARCHIVE_CHARACTER_ROOT.as_posix(), *rel.parts)
    _safe_archive_path(archive_path.as_posix(), "archive path")
    return archive_path


def _archive_path_for_profile_resource(
    package_dir: Path,
    source: Path,
    *,
    kind: str,
    package_archive_names: set[str],
    external_paths: dict[Path, PurePosixPath],
) -> PurePosixPath:
    resolved_source = _resolved(source)
    package_root = _resolved(package_dir)
    try:
        resolved_source.relative_to(package_root)
    except ValueError:
        if not resolved_source.is_file():
            raise CharacterArchiveError(f"角色资源不存在：{source}")
        if resolved_source in external_paths:
            return external_paths[resolved_source]
        archive_path = _next_external_archive_path(
            resolved_source.name,
            kind=kind,
            used=package_archive_names | {path.as_posix() for path in external_paths.values()},
        )
        external_paths[resolved_source] = archive_path
        return archive_path
    return _archive_path_for_package_file(package_dir, resolved_source)


def _next_external_archive_path(filename: str, *, kind: str, used: set[str]) -> PurePosixPath:
    safe_name = _safe_filename(filename)
    base = PurePosixPath(ARCHIVE_CHARACTER_ROOT.as_posix(), kind, safe_name)
    if base.as_posix() not in used:
        return base
    stem = Path(safe_name).stem or "resource"
    suffix = Path(safe_name).suffix
    index = 1
    while True:
        candidate = PurePosixPath(
            ARCHIVE_CHARACTER_ROOT.as_posix(),
            kind,
            f"{stem}_{index}{suffix}",
        )
        if candidate.as_posix() not in used:
            return candidate
        index += 1


def _safe_filename(filename: str) -> str:
    raw = str(filename or "").replace("\\", "/").strip()
    if not raw or "/" in raw or raw in (".", "..") or "\x00" in raw or _WINDOWS_DRIVE_RE.match(raw):
        raise CharacterArchiveError(f"资源文件名不安全：{filename!r}")
    return raw


def _write_zip_file(
    zf: zipfile.ZipFile,
    source: Path,
    archive_path: PurePosixPath,
    written: set[str],
) -> None:
    archive_name = archive_path.as_posix()
    _safe_archive_path(archive_name, "archive path")
    if archive_name in written:
        return
    if not source.is_file():
        raise CharacterArchiveError(f"角色资源不存在：{source}")
    zf.write(source, archive_name)
    written.add(archive_name)


def _is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_IFMT(mode) == stat.S_IFLNK


def _resolved(path: Path) -> Path:
    return path.resolve()


def _export_live2d_manifest(
    profile: CharacterProfile,
    *,
    package_archive_names: set[str],
    external_paths: dict[Path, PurePosixPath],
) -> dict[str, Any] | None:
    live2d = profile.live2d
    if live2d is None:
        return None

    model_json = _resolved(live2d.model_json_path)
    if not model_json.is_file():
        raise CharacterArchiveError(f"Live2D 模型不存在：{model_json}")

    model_archive_path = _bundle_live2d_model_tree(
        model_json,
        package_dir=profile.package_dir,
        package_archive_names=package_archive_names,
        external_paths=external_paths,
    )
    return _live2d_settings_to_manifest(live2d, model_archive_path.as_posix())


def _bundle_live2d_model_tree(
    model_json: Path,
    *,
    package_dir: Path,
    package_archive_names: set[str],
    external_paths: dict[Path, PurePosixPath],
) -> PurePosixPath:
    model_dir = _resolved(model_json).parent
    package_root = _resolved(package_dir)
    model_archive_path: PurePosixPath | None = None

    for source in sorted(model_dir.rglob("*")):
        if not source.is_file():
            continue
        rel = source.relative_to(model_dir)
        archive_path = PurePosixPath(ARCHIVE_CHARACTER_ROOT, "live2d", "model", *rel.parts)
        archive_name = archive_path.as_posix()
        if archive_name in package_archive_names:
            if _resolved(source) == _resolved(model_json):
                model_archive_path = archive_path
            continue
        resolved_source = _resolved(source)
        if resolved_source in external_paths:
            if resolved_source == _resolved(model_json):
                model_archive_path = external_paths[resolved_source]
            continue
        try:
            resolved_source.relative_to(package_root)
        except ValueError:
            external_paths[resolved_source] = archive_path
        if resolved_source == _resolved(model_json):
            model_archive_path = archive_path

    if model_archive_path is None:
        raise CharacterArchiveError(f"无法归档 Live2D 模型：{model_json}")
    return model_archive_path


def _live2d_settings_to_manifest(
    live2d: CharacterLive2D,
    model_archive_path: str,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {"model": model_archive_path}
    if live2d.idle_motion_file:
        manifest["idle_motion"] = live2d.idle_motion_file
    if live2d.default_expression:
        manifest["default_expression"] = live2d.default_expression
    if live2d.tone_expressions:
        manifest["tone_expressions"] = dict(live2d.tone_expressions)
    if live2d.expression_presets:
        manifest["expression_presets"] = [
            {
                "label": preset.label,
                "expression": preset.expression,
                **(
                    {"overlays": [*preset.overlays]}
                    if preset.overlays
                    else {}
                ),
            }
            for preset in live2d.expression_presets
        ]
    if live2d.speaking_expression:
        manifest["speaking_expression"] = live2d.speaking_expression
    if live2d.speaking_overlay_expressions:
        manifest["speaking_overlay_expressions"] = [*live2d.speaking_overlay_expressions]
    if live2d.tap_expressions:
        manifest["tap_expressions"] = [*live2d.tap_expressions]
    if live2d.idle_variation_expressions:
        manifest["idle_variation_expressions"] = [*live2d.idle_variation_expressions]
    manifest["idle_variation_min_seconds"] = live2d.idle_variation_min_seconds
    manifest["idle_variation_max_seconds"] = live2d.idle_variation_max_seconds
    manifest["blink_enabled"] = live2d.blink_enabled
    manifest["physics_enabled"] = live2d.physics_enabled
    return manifest


def _normalized_live2d(live2d_data: Any) -> dict[str, Any]:
    if not isinstance(live2d_data, dict):
        raise CharacterArchiveError("character.live2d 必须是对象。")
    if live2d_data.get("enabled") is False:
        raise CharacterArchiveError("character.live2d.enabled=false 的归档包无法导入。")

    normalized: dict[str, Any] = {
        "model": _package_path_text(
            _required_archive_resource(live2d_data, "model", "character.live2d.model")
        ),
    }
    idle_motion = live2d_data.get("idle_motion")
    if isinstance(idle_motion, str) and idle_motion.strip():
        normalized["idle_motion"] = idle_motion.strip()
    default_expression = live2d_data.get("default_expression")
    if isinstance(default_expression, str) and default_expression.strip():
        normalized["default_expression"] = default_expression.strip()
    tone_map = live2d_data.get("tone_expressions")
    if isinstance(tone_map, dict) and tone_map:
        normalized["tone_expressions"] = {
            str(label).strip(): str(expression_id).strip()
            for label, expression_id in tone_map.items()
            if str(label).strip() and str(expression_id).strip()
        }
    speaking_expression = live2d_data.get("speaking_expression")
    if isinstance(speaking_expression, str) and speaking_expression.strip():
        normalized["speaking_expression"] = speaking_expression.strip()
    for field_name, target_key in (
        ("speaking_overlay_expressions", "speaking_overlay_expressions"),
        ("tap_expressions", "tap_expressions"),
        ("idle_variation_expressions", "idle_variation_expressions"),
    ):
        values = _normalized_live2d_expression_list(live2d_data.get(field_name), field_name)
        if values:
            normalized[target_key] = values
    for field_name, target_key in (
        ("idle_variation_min_seconds", "idle_variation_min_seconds"),
        ("idle_variation_max_seconds", "idle_variation_max_seconds"),
    ):
        value = live2d_data.get(field_name)
        if value is not None:
            normalized[target_key] = _positive_float(value, f"character.live2d.{field_name}")
    if "blink_enabled" in live2d_data:
        normalized["blink_enabled"] = _archive_bool(live2d_data.get("blink_enabled"))
    if "physics_enabled" in live2d_data:
        normalized["physics_enabled"] = _archive_bool(live2d_data.get("physics_enabled"))
    return normalized


def _normalized_live2d_expression_list(raw_value: Any, field_name: str) -> list[str]:
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise CharacterArchiveError(f"character.live2d.{field_name} 必须是数组。")
    result: list[str] = []
    for item in raw_value:
        if not isinstance(item, str) or not item.strip():
            raise CharacterArchiveError(f"character.live2d.{field_name} 的元素必须是非空字符串。")
        result.append(item.strip())
    return result


def _positive_float(value: Any, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CharacterArchiveError(f"{field_name} 必须是正数。") from exc
    if parsed <= 0:
        raise CharacterArchiveError(f"{field_name} 必须是正数。")
    return parsed


def _archive_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise CharacterArchiveError("character.live2d 的布尔字段格式无效。")
