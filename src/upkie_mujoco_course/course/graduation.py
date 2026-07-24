"""毕业项目八类门槛的证据审查。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from upkie_mujoco_course.course.results import assess_experiment_result
from upkie_mujoco_course.course.results import capture_source_state
from upkie_mujoco_course.utils.paths import project_root


_GATE_REQUIREMENTS = {
    "code_tests": ("full_pytest", "全量 pytest 与可复现评估"),
    "physical_metrics": ("18", "物理控制指标"),
    "robustness": ("31", "随机化鲁棒性评估"),
    "realtime": ("42", "实时性与性能分析"),
    "safety": ("43", "部署安全与故障恢复"),
    "documentation": ("44", "系统设计与接口文档"),
    "design_review": ("46", "故障演练与设计评审"),
    "oral_defense": ("47", "代码评审与口头答辩"),
}


def _resolve_evidence_path(path: str | Path, root: str | Path | None) -> Path:
    evidence_path = Path(path)
    if evidence_path.is_absolute():
        return evidence_path
    base = Path(root).resolve() if root is not None else project_root().resolve()
    return base / evidence_path


def _load_valid_result(
    candidate: dict[str, Any],
    source_state: dict[str, Any],
    root: str | Path | None,
) -> dict[str, Any] | None:
    result_path = candidate.get("result_path")
    if not isinstance(result_path, str) or not result_path.strip():
        return None
    path = _resolve_evidence_path(result_path, root)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    assessment = assess_experiment_result(
        data,
        current_source_state=source_state,
        root=root,
    )
    if not assessment["valid"]:
        return None
    data["result_path"] = str(path)
    return data


def _is_full_pytest_result(result: dict[str, Any]) -> bool:
    config = result.get("config")
    metrics = result.get("metrics")
    if not isinstance(config, dict) or not isinstance(metrics, dict):
        return False
    test_count = config.get("test_count")
    if not isinstance(test_count, int) or isinstance(test_count, bool) or test_count <= 0:
        return False
    command = config.get("command")
    if isinstance(command, str):
        command_parts = command.split()
    elif isinstance(command, list) and all(isinstance(item, str) for item in command):
        command_parts = command
    else:
        return False
    normalized_parts = [item.replace("\\", "/").rstrip("/") for item in command_parts]
    return (
        config.get("test_scope") == "full"
        and "pytest" in " ".join(command_parts)
        and "tests" in normalized_parts
        and metrics.get("test_exit_code") == 0
    )


def build_graduation_gate_report(
    results: list[dict[str, Any]],
    *,
    current_source_state: dict[str, Any] | None = None,
    root: str | Path | None = None,
    manual_review_path: str | Path | None = None,
) -> dict[str, Any]:
    """生成课程工程与学习者毕业相互独立的 2.0 门槛报告。"""

    source_state = current_source_state or capture_source_state(root)
    valid_results: dict[str, dict[str, Any]] = {}
    for candidate in results:
        result = _load_valid_result(candidate, source_state, root)
        if result is not None:
            valid_results[str(result["chapter_id"])] = result

    full_pytest = valid_results.get("full_pytest")
    if full_pytest is not None and not _is_full_pytest_result(full_pytest):
        full_pytest = None
    untrusted_review_path = (
        str(_resolve_evidence_path(manual_review_path, root))
        if manual_review_path is not None
        else None
    )

    gates: dict[str, dict[str, Any]] = {}
    for name, (chapter_id, requirement) in _GATE_REQUIREMENTS.items():
        evidence = full_pytest if name == "code_tests" else valid_results.get(chapter_id)
        if name == "oral_defense":
            gates[name] = {
                "passed": False,
                "required_chapter": chapter_id,
                "requirement": requirement,
                "evidence_path": None,
                "course_evidence_path": evidence.get("result_path") if evidence else None,
                "untrusted_local_review_path": untrusted_review_path,
                "missing_reason": "真人毕业必须由仓库外部评审系统判定",
            }
            continue
        missing_reason = None
        if evidence is None:
            missing_reason = (
                "缺少通过统一结果契约校验的全量 pytest 证据"
                if name == "code_tests"
                else f"缺少通过统一结果契约校验的第 {chapter_id} 关证据"
            )
        gates[name] = {
            "passed": evidence is not None,
            "required_chapter": chapter_id,
            "requirement": requirement,
            "evidence_path": evidence.get("result_path") if evidence else None,
            "missing_reason": missing_reason,
        }

    course_build_ready = all(
        gate["passed"] for name, gate in gates.items() if name != "oral_defense"
    ) and "47" in valid_results
    learner_graduated = False
    return {
        "schema_version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "gates": gates,
        "course_build_ready": course_build_ready,
        "learner_graduated": learner_graduated,
        "overall_passed": learner_graduated,
        "manual_review_required": True,
        "external_authority_required": True,
    }


def write_graduation_gate_report(
    output_root: str | Path,
    results: list[dict[str, Any]],
    *,
    manual_review_path: str | Path | None = None,
) -> Path:
    root = Path(output_root)
    output = root / "reports" / "graduation_gates.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            build_graduation_gate_report(results, manual_review_path=manual_review_path),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output
