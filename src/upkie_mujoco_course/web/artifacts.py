"""outputs/ 产物索引、MIME 白名单和路径安全。"""

from __future__ import annotations

import os
import re
from pathlib import Path

from upkie_mujoco_course.utils.paths import resolve_project_path

# Windows 盘符绝对路径，如 C:\ 或 C:/，用于跨平台拒绝（Linux 上 os.path.isabs 认不出）。
_WINDOWS_ABS_RE = re.compile(r"^[a-zA-Z]:[\\/]")

_MIME_WHITELIST: dict[str, str] = {
    ".json": "application/json",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".npz": "application/octet-stream",
    ".pt": "application/octet-stream",
    ".pth": "application/octet-stream",
    ".yml": "application/yaml",
    ".yaml": "application/yaml",
    ".toml": "application/toml",
}


def _normalize_artifact_path(relative_path: str) -> str:
    """将传入路径归一化到 outputs/ 下（统一正/反斜杠，兼容 Windows 与 Linux）。"""
    clean = relative_path.replace("\\", "/").replace("/", os.sep).lstrip(os.sep)
    if clean.lower().startswith(f"outputs{os.sep}"):
        return clean
    return os.path.join("outputs", clean)


def is_safe_artifact_path(relative_path: str) -> bool:
    if not relative_path:
        return False
    # 统一分隔符后判断：兼容 Windows 反斜杠与盘符绝对路径，保证 Linux/CI 上判定一致。
    unified = relative_path.replace("\\", "/")
    if os.path.isabs(relative_path) or unified.startswith("/") or _WINDOWS_ABS_RE.match(relative_path):
        return False
    if any(part == ".." for part in unified.split("/")):
        return False

    normalized = _normalize_artifact_path(relative_path)
    root = resolve_project_path()
    resolved = (root / normalized).resolve()
    outputs_dir = (root / "outputs").resolve()
    try:
        resolved.relative_to(outputs_dir)
    except ValueError:
        return False

    return True


def get_artifact_mime_type(ext: str) -> str | None:
    return _MIME_WHITELIST.get(ext.lower())


def resolve_artifact_path(*parts: str) -> Path | None:
    relative = os.path.join(*parts)
    if not is_safe_artifact_path(relative):
        return None
    root = resolve_project_path()
    normalized = _normalize_artifact_path(relative)
    full = (root / normalized).resolve()
    if not full.exists() or not full.is_file():
        return None
    return full


def list_chapter_artifacts(chapter_id: str) -> list[dict]:
    from upkie_mujoco_course.web.schemas import ArtifactDto

    root = resolve_project_path()
    results_dir = root / "outputs" / "results"

    artifacts: list[dict] = []

    for pattern in [
        f"checkpoint_{chapter_id}_*.json",
        f"foundation_{chapter_id}_*.json",
        f"classical_{chapter_id}_*.json",
        f"estimation_{chapter_id}_*.json",
        f"rl_{chapter_id}_*.json",
        f"vla_{chapter_id}_*.json",
        f"engineering_{chapter_id}_*.json",
        f"hardware_{chapter_id}_*.json",
    ]:
        for f in sorted(results_dir.glob(pattern)):
            rel = f.relative_to(root).as_posix()
            if is_safe_artifact_path(rel):
                artifacts.append(ArtifactDto(
                    path=rel,
                    type=get_artifact_mime_type(f.suffix) or "application/octet-stream",
                    size=f.stat().st_size,
                    modified_at=str(f.stat().st_mtime),
                    url=f"/api/artifacts/{rel}",
                    evidence_valid=True,
                ).model_dump())

    plots_dir = root / "outputs" / "plots"
    for pattern in [
        f"checkpoint_{chapter_id}.png",
        f"foundation_{chapter_id}.png",
        f"classical_{chapter_id}.png",
        f"estimation_{chapter_id}.png",
        f"rl_{chapter_id}.png",
        f"vla_{chapter_id}.png",
        f"engineering_{chapter_id}.png",
        f"hardware_{chapter_id}.png",
    ]:
        for f in sorted(plots_dir.glob(pattern)):
            rel = f.relative_to(root).as_posix()
            if is_safe_artifact_path(rel):
                artifacts.append(ArtifactDto(
                    path=rel,
                    type="image/png",
                    size=f.stat().st_size,
                    modified_at=str(f.stat().st_mtime),
                    url=f"/api/artifacts/{rel}",
                    evidence_valid=True,
                ).model_dump())

    return artifacts
