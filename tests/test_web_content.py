"""web content 聚合测试。

覆盖：58 个章节均可通过 API 聚合，正文路径在 tutorials/v2/。
"""

import pytest
from pathlib import Path
from upkie_mujoco_course.web.content import (
    load_chapter_markdown,
    parse_self_check_items,
    build_chapter_dto,
    build_course_summary,
)
from upkie_mujoco_course.course.manifest import load_course_manifest


def test_load_chapter_markdown_returns_string():
    from upkie_mujoco_course.utils.paths import resolve_project_path

    tutorial_path = resolve_project_path("tutorials/v2/00/README.md")
    content = load_chapter_markdown("00")
    assert isinstance(content, str)
    assert len(content) > 0

    with open(tutorial_path, "r", encoding="utf-8") as f:
        expected = f.read()
    assert content == expected


def test_chapter_00_has_content():
    content = load_chapter_markdown("00")
    assert "课程导航" in content or "Upkie" in content


def test_all_58_chapters_have_tutorial_files():
    manifest = load_course_manifest()
    from upkie_mujoco_course.utils.paths import resolve_project_path

    missing = []
    for chapter in manifest["chapters"]:
        tutorial_path = resolve_project_path(chapter["tutorial"])
        if not tutorial_path.exists():
            missing.append(chapter["id"])
    assert missing == [], f"缺少教程文件: {missing}"


def test_markdown_path_stays_within_tutorials_v2():
    manifest = load_course_manifest()
    for chapter in manifest["chapters"]:
        tutorial = chapter["tutorial"]
        assert tutorial.startswith("tutorials/v2/"), (
            f"章节 {chapter['id']} 的教程路径不在 tutorials/v2/ 内: {tutorial}"
        )


def test_parse_self_check_items():
    md = """
## 自测

- [ ] 任务一：完成环境搭建
- [ ] 任务二：运行第一个脚本
- [x] 任务三：已完成的任务

### 复盘与面试
- [ ] 面试问题一
"""
    items = parse_self_check_items(md)
    assert len(items) >= 2
    for item in items:
        assert "text" in item
        assert "checked" in item


def test_build_chapter_dto_ready():
    dto = build_chapter_dto("00", {}, [])
    assert dto.id == "00"
    assert dto.status == "ready"
    assert len(dto.content) > 0


def test_build_course_summary_has_58_chapters():
    summary = build_course_summary({}, [])
    assert summary["total_chapters"] == 58
    assert len(summary["stages"]) == 9


def test_build_chapter_dto_planned():
    dto = build_chapter_dto("H02", {}, [])
    assert dto.id == "H02"
    assert dto.status == "planned"


def test_build_chapter_dto_unknown_raises():
    with pytest.raises(ValueError):
        build_chapter_dto("XX", {}, [])
