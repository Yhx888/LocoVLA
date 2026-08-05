"""课程内容聚合：manifest、Markdown、自测项和章节 DTO。"""

from __future__ import annotations

import hashlib

from upkie_mujoco_course.course.manifest import load_course_manifest
from upkie_mujoco_course.utils.paths import resolve_project_path
from upkie_mujoco_course.web.schemas import ChapterDto, ArtifactDto, RunPreset


def load_chapter_markdown(chapter_id: str) -> str:
    manifest = load_course_manifest()
    by_id = {ch["id"]: ch for ch in manifest["chapters"]}
    if chapter_id not in by_id:
        raise ValueError(f"未知章节: {chapter_id}")
    tutorial_path = resolve_project_path(by_id[chapter_id]["tutorial"])
    if not tutorial_path.exists():
        return f"# {by_id[chapter_id]['title']}\n\n教程文件不存在。"
    return tutorial_path.read_text(encoding="utf-8")


def parse_self_check_items(markdown: str) -> list[dict]:
    items: list[dict] = []
    in_section = False
    for line in markdown.split("\n"):
        if line.startswith("## 自测") or "自测" in line:
            in_section = True
            continue
        if in_section and line.startswith("## ") and "自测" not in line:
            in_section = False
            continue
        if in_section and line.strip().startswith("- ["):
            checked = line.strip().startswith("- [x]") or line.strip().startswith("- [X]")
            text = line.strip()[5:].strip()
            items.append({"text": text, "checked": checked})
    return items


def _compute_self_check_id(chapter_id: str, text: str) -> str:
    hash_hex = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{chapter_id}-{hash_hex}"


def build_chapter_dto(
    chapter_id: str,
    progress: dict,
    results: list[dict],
) -> ChapterDto:
    manifest = load_course_manifest()
    by_id = {ch["id"]: ch for ch in manifest["chapters"]}
    if chapter_id not in by_id:
        raise ValueError(f"未知章节: {chapter_id}")
    ch = by_id[chapter_id]

    content = load_chapter_markdown(chapter_id)
    self_check_raw = parse_self_check_items(content)
    self_check_items = [
        {
            "id": _compute_self_check_id(chapter_id, item["text"]),
            "text": item["text"],
            "checked": item["checked"],
        }
        for item in self_check_raw
    ]

    ch_progress = progress.get("chapters", {}).get(chapter_id, {})
    reading_percent = ch_progress.get("reading_percent", 0)
    reading_complete = ch_progress.get("reading_complete", False)
    self_check_ids = ch_progress.get("self_check_ids", [])

    experiment_accepted = False
    for result in (results or []):
        if str(result.get("chapter_id")) == chapter_id:
            if result.get("acceptance_valid") and result.get("passed"):
                experiment_accepted = True
                break

    completed = bool(
        reading_complete
        and len(self_check_ids) >= len(self_check_items)
        and experiment_accepted
    )

    presets: list[RunPreset] = []
    if ch["status"] == "ready":
        presets.append(RunPreset(
            id="demo",
            label="快速演示",
            mode="demo",
            estimated_seconds=15,
            counts_for_acceptance=False,
            commands=[f"python scripts/course_checkpoint.py --chapter {chapter_id} --smoke"],
        ))
        presets.append(RunPreset(
            id="full",
            label="正式运行",
            mode="full",
            estimated_seconds=120,
            counts_for_acceptance=True,
            commands=[f"python scripts/course_checkpoint.py --chapter {chapter_id}"],
        ))

    artifacts: list[ArtifactDto] = []
    portfolio_dir = resolve_project_path(ch.get("portfolio", f"outputs/portfolio/{chapter_id}"))
    if portfolio_dir.exists():
        for f in sorted(portfolio_dir.rglob("*")):
            if f.is_file():
                relative_path = f.relative_to(resolve_project_path()).as_posix()
                artifacts.append(ArtifactDto(
                    path=relative_path,
                    type="application/octet-stream",
                    size=f.stat().st_size,
                    url=f"/api/artifacts/{relative_path}",
                ))

    return ChapterDto(
        id=ch["id"],
        stage=ch["stage"],
        stage_title=ch["stage_title"],
        title=ch["title"],
        task=ch.get("task", ""),
        status=ch["status"],
        prerequisites=ch.get("prerequisites", []),
        content=content,
        reading_percent=reading_percent,
        reading_complete=reading_complete,
        self_check_ids=self_check_ids,
        self_check_items=self_check_items,
        experiment_accepted=experiment_accepted,
        completed=completed,
        presets=presets,
        checkpoints=ch.get("checkpoints", []),
        artifacts=artifacts,
    )


def build_course_summary(progress: dict, results: list[dict]) -> dict:
    manifest = load_course_manifest()
    by_id = {ch["id"]: ch for ch in manifest["chapters"]}
    progress_chapters = progress.get("chapters", {})

    evidence_ids = {
        str(r["chapter_id"])
        for r in (results or [])
        if r.get("acceptance_valid") and r.get("passed") and r.get("chapter_id") is not None
    }

    stages = []
    for stage in manifest["stages"]:
        ids = [cid for cid, _ in stage["chapters"]]
        stage_ready = sum(
            cid in {ch["id"] for ch in manifest["chapters"] if ch["status"] == "ready"}
            for cid in ids
        )
        stage_completed = sum(cid in evidence_ids for cid in ids)
        chapter_list = []
        for cid, ctitle in stage["chapters"]:
            ch_info = by_id.get(cid, {})
            chapter_list.append({
                "id": cid,
                "title": ctitle,
                "status": ch_info.get("status", "planned"),
                "completed": cid in evidence_ids,
                "reading_complete": progress_chapters.get(cid, {}).get("reading_complete", False),
                "reading_percent": progress_chapters.get(cid, {}).get("reading_percent", 0),
            })
        stages.append({
            "id": stage["id"],
            "title": stage["title"],
            "project": stage.get("project", ""),
            "total": len(ids),
            "ready": stage_ready,
            "completed": stage_completed,
            "chapters": chapter_list,
        })

    next_chapter = next(
        (
            ch
            for ch in manifest["chapters"]
            if ch["status"] == "ready" and ch["id"] not in evidence_ids
        ),
        None,
    )

    return {
        "title": manifest["title"],
        "version": manifest["version"],
        "total_chapters": len(manifest["chapters"]),
        "completed_chapters": len(evidence_ids),
        "next_chapter": next_chapter,
        "stages": stages,
    }
