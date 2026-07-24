"""checkpoint 工具。"""

from __future__ import annotations

from pathlib import Path


def latest_checkpoint(directory: str | Path) -> Path | None:
    paths = sorted(Path(directory).glob("*.zip"), key=lambda item: item.stat().st_mtime)
    return paths[-1] if paths else None

