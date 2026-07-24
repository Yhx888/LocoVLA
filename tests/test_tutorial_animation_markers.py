"""教程正文动画标记的课程契约。"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "configs" / "course" / "manifest.json"
MARKER_RE = re.compile(r"^<!-- upkie-animation:([a-z0-9-]+) -->$")
RICH_CHAPTERS = {f"{index:02d}" for index in range(12, 38)}
RICH_SUFFIXES = {"intuition", "parameter", "comparison", "evidence"}


def _chapter_ids() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [chapter[0] for stage in manifest["stages"] for chapter in stage["chapters"]]


def _markers(chapter_id: str) -> list[str]:
    path = ROOT / "tutorials" / "v2" / chapter_id / "README.md"
    return [
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := MARKER_RE.fullmatch(line))
    ]


def test_all_tutorials_have_the_required_animation_markers() -> None:
    chapter_ids = _chapter_ids()
    assert len(chapter_ids) == 58

    all_markers: list[str] = []
    for chapter_id in chapter_ids:
        markers = _markers(chapter_id)
        expected = (
            {f"{chapter_id}-{suffix}" for suffix in RICH_SUFFIXES}
            if chapter_id in RICH_CHAPTERS
            else {f"{chapter_id.lower()}-core"}
        )
        assert expected <= set(markers), f"章节 {chapter_id} 的动画标记不完整: {markers}"
        minimum = 4 if chapter_id in RICH_CHAPTERS else 1
        assert len(markers) >= minimum, f"章节 {chapter_id} 至少需要 {minimum} 个正文动画"
        all_markers.extend(markers)

    assert len(all_markers) >= 136
    assert len(all_markers) == len(set(all_markers)), "动画标记 ID 必须全局唯一"


def test_animation_markers_are_standalone_markdown_paragraphs() -> None:
    for chapter_id in _chapter_ids():
        path = ROOT / "tutorials" / "v2" / chapter_id / "README.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        in_fence = False

        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if "upkie-animation:" not in line:
                continue

            assert not in_fence, f"{path}:{index + 1} 标记位于代码块中"
            assert MARKER_RE.fullmatch(line), f"{path}:{index + 1} 标记必须独占一行且不得缩进"
            assert index > 0 and not lines[index - 1].strip(), (
                f"{path}:{index + 1} 标记前必须有空行"
            )
            assert index + 1 < len(lines) and not lines[index + 1].strip(), (
                f"{path}:{index + 1} 标记后必须有空行"
            )
