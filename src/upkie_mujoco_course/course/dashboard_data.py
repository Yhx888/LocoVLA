"""学习仪表盘的数据聚合。"""

from __future__ import annotations

import json
from pathlib import Path

from upkie_mujoco_course.course.results import assess_experiment_result
from upkie_mujoco_course.course.results import capture_source_state


def is_diagnostic_result(result: dict) -> bool:
    """故障注入结果用于诊断训练，不参与关卡主验收。"""

    return bool(result.get("config", {}).get("inject_fault"))


def load_experiment_results(output_root: str | Path) -> list[dict]:
    """读取统一结果，并把失败检查项整理成仪表盘可直接展示的字段。"""

    loaded: list[dict] = []
    for path in sorted((Path(output_root) / "results").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            continue
        data["result_path"] = str(path)
        checks = data.get("checks", {})
        if isinstance(checks, dict):
            data["failed_checks"] = [name for name, passed in checks.items() if not passed]
        else:
            data["failed_checks"] = []
        loaded.append(data)

    current_source_state = capture_source_state()
    for data in loaded:
        assessment = assess_experiment_result(
            data,
            current_source_state=current_source_state,
        )
        data["contract_status"] = (
            "current" if assessment["status"] == "valid" else assessment["status"]
        )
        data["contract_errors"] = assessment["errors"]
        data["acceptance_valid"] = assessment["valid"] and data.get("passed") is True
    return sorted(loaded, key=lambda item: str(item.get("chapter_id", "")))


def collect_chapter_evidence(
    progress: dict,
    results: list[dict],
    chapter_id: str,
) -> list[str]:
    evidence = list(progress.get("chapters", {}).get(chapter_id, {}).get("evidence", []))
    chapter_results = [
        result
        for result in results
        if str(result.get("chapter_id")) == chapter_id and not is_diagnostic_result(result)
    ]
    if chapter_results:
        current = [
            result
            for result in chapter_results
            if result.get("contract_status") == "current"
            and result.get("acceptance_valid") is True
            and result.get("passed") is True
        ]
        if current:
            latest = current[-1]
            evidence.append(f"自动验收通过：{latest.get('result_path', '未记录结果路径')}")
        else:
            latest = chapter_results[-1]
            status = latest.get("contract_status", "legacy")
            path = latest.get("result_path", "未记录结果路径")
            evidence.append(f"历史/无效证据（{status}，不计完成）：{path}")
    return evidence


def build_dashboard_summary(
    manifest: dict,
    progress: dict,
    results: list[dict] | None = None,
) -> dict:
    """构建仪表盘摘要，明确区分"已开放"和"已有真实证据"。"""
    progress_chapters = progress.get("chapters", {})
    evidence_ids = {
        str(result["chapter_id"])
        for result in (results or [])
        if result.get("acceptance_valid") is True
        and result.get("passed") is True
        and result.get("chapter_id") is not None
        and not is_diagnostic_result(result)
    }
    # 未加载结果目录时保留 progress.json 展示兼容；一旦提供结果，只认当前有效契约。
    completed_ids = set(evidence_ids)
    if results is None:
        completed_ids.update(
            chapter_id
            for chapter_id, status in progress_chapters.items()
            if status.get("completed_checkpoints")
        )
    # 已开放但尚无证据的关卡
    ready_ids = {
        chapter["id"]
        for chapter in manifest["chapters"]
        if chapter["status"] == "ready"
    }
    opened_no_evidence = ready_ids - completed_ids

    stages = []
    for stage in manifest["stages"]:
        ids = [chapter_id for chapter_id, _ in stage["chapters"]]
        stage_ready = sum(chapter_id in ready_ids for chapter_id in ids)
        stage_evidence = sum(chapter_id in completed_ids for chapter_id in ids)
        stages.append(
            {
                "id": stage["id"],
                "title": stage["title"],
                "total": len(ids),
                "ready": stage_ready,
                "completed": stage_evidence,
            }
        )
    next_chapter = next(
        (
            chapter
            for chapter in manifest["chapters"]
            if chapter["status"] == "ready" and chapter["id"] not in completed_ids
        ),
        None,
    )
    return {
        "total_chapters": len(manifest["chapters"]),
        "completed_chapters": len(completed_ids),
        "ready_chapters": len(ready_ids),
        "opened_no_evidence": len(opened_no_evidence),
        "next_chapter": next_chapter,
        "stages": stages,
    }
