"""项目路径工具。"""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """返回 v2 项目根目录。"""

    return Path(__file__).resolve().parents[3]


def resolve_project_path(*parts: str | Path) -> Path:
    """把相对项目根目录的路径转换成绝对路径。"""

    candidate = Path(parts[0]) if len(parts) == 1 else Path(*parts)
    if candidate.is_absolute():
        return candidate
    return project_root() / candidate


def ensure_output_dir(*parts: str | Path) -> Path:
    """创建并返回 outputs 下的子目录。"""

    path = resolve_project_path("outputs", *parts)
    path.mkdir(parents=True, exist_ok=True)
    return path

