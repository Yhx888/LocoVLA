"""第 45 关综合毕业项目测试（端到端验证版）。

覆盖：
- run_end_to_end_validation 返回 6 个步骤
- 任一维度失败令 system_score=0.0
- 所有维度通过令 system_score=1.0
- 端到端验证失败时强制归零对应维度
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.capstone import (  # noqa: E402
    compute_system_score,
    run_capstone,
    run_end_to_end_validation,
)
from upkie_mujoco_course.capstone.runner import END_TO_END_IMPACT  # noqa: E402
from upkie_mujoco_course.capstone import runner as capstone_runner  # noqa: E402
from upkie_mujoco_course.course.results import write_experiment_result  # noqa: E402
import upkie_mujoco_course.engineering as engineering_contract  # noqa: E402

# 6 个端到端验证步骤的键名
EXPECTED_END_TO_END_STEPS = {
    "simulation",
    "control",
    "environment",
    "safety_ros2",
    "log_contract",
    "doc_consistency",
}

# 8 个评分维度
EXPECTED_DIMENSIONS = {
    "code",
    "physics",
    "robustness",
    "realtime",
    "safety",
    "docs",
    "design_review",
    "oral_defense",
}


def test_code_gate_reads_chapter_37_checkpoint_without_graduation_report(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "plot.png").write_bytes(b"plot")
    (artifacts / "log.txt").write_text("log", encoding="utf-8")
    write_experiment_result(
        results / "checkpoint_37.json",
        chapter_id="37",
        seed=37,
        config={},
        metrics={"test_exit_code": 0.0},
        pass_conditions={"test_exit_code": {"operator": "==", "value": 0}},
        plots=["artifacts/plot.png"],
        logs=["artifacts/log.txt"],
        root=tmp_path,
    )

    evidence = capstone_runner.load_gate_evidence(tmp_path, source_root=tmp_path)

    assert evidence["code_tests"]["passed"] is True
    assert evidence["code_tests"]["result"]["chapter_id"] == "37"


def test_capstone_gate_loader_rejects_forged_minimal_result(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "checkpoint_37.json").write_text(
        '{"chapter_id":"37","passed":true}',
        encoding="utf-8",
    )

    evidence = capstone_runner.load_gate_evidence(tmp_path)

    assert evidence["code_tests"]["passed"] is False


def test_realtime_expected_field_count_tracks_shared_log_contract(monkeypatch):
    """runner 的日志字段数应随共享契约变化，而非固定常量。"""
    shared_fields = tuple(getattr(engineering_contract, "REQUIRED_LOG_FIELDS", ()))
    assert shared_fields
    monkeypatch.setattr(
        engineering_contract,
        "REQUIRED_LOG_FIELDS",
        shared_fields + ("future_log_field",),
    )

    result = capstone_runner._e2e_run_realtime({}, [])

    assert result["details"]["expected_field_count"] == len(
        engineering_contract.REQUIRED_LOG_FIELDS
    )


def test_log_contract_validation_tracks_shared_field_count(monkeypatch, tmp_path):
    """快速日志验证应接受符合共享契约字段数的第42章结果。"""
    shared_fields = engineering_contract.REQUIRED_LOG_FIELDS
    monkeypatch.setattr(
        engineering_contract,
        "REQUIRED_LOG_FIELDS",
        shared_fields + ("future_log_field",),
    )
    result_path = tmp_path / "results" / "engineering_42.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "metrics": {
                    "log_field_count": len(engineering_contract.REQUIRED_LOG_FIELDS),
                    "deadline_miss_count": 0,
                    "perf_trace_present": 1,
                }
            }
        ),
        encoding="utf-8",
    )

    result = capstone_runner._validate_log_contract(tmp_path)

    assert result["passed"] is True
    assert result["details"]["expected_log_field_count"] == len(
        engineering_contract.REQUIRED_LOG_FIELDS
    )


def test_end_to_end_validation_returns_six_steps():
    """run_end_to_end_validation 应返回 6 个步骤的验证结果。"""
    result = run_end_to_end_validation("outputs")

    assert isinstance(result, dict)
    assert set(result.keys()) == EXPECTED_END_TO_END_STEPS, (
        f"端到端验证步骤不匹配：期望 {EXPECTED_END_TO_END_STEPS}，实际 {set(result.keys())}"
    )

    # 每个步骤都应包含 passed 和 details 字段
    for step_name, step_result in result.items():
        assert "passed" in step_result, f"步骤 {step_name} 缺少 passed 字段"
        assert "details" in step_result, f"步骤 {step_name} 缺少 details 字段"
        assert isinstance(step_result["passed"], bool), f"步骤 {step_name} 的 passed 不是 bool 类型"
        assert isinstance(step_result["details"], dict), f"步骤 {step_name} 的 details 不是 dict 类型"
        # details 应包含 elapsed_ms
        assert "elapsed_ms" in step_result["details"], (
            f"步骤 {step_name} 的 details 缺少 elapsed_ms 字段"
        )


def test_run_capstone_includes_end_to_end_validation():
    """run_capstone 返回的报告应包含 end_to_end_validation 字段。"""
    report = run_capstone("outputs")

    assert "end_to_end_validation" in report, "报告缺少 end_to_end_validation 字段"
    assert "end_to_end_overrides" in report, "报告缺少 end_to_end_overrides 字段"
    assert "dimension_scores" in report, "报告缺少 dimension_scores 字段"
    assert "system_score" in report, "报告缺少 system_score 字段"

    # 8 个维度全部存在
    assert set(report["dimension_scores"].keys()) == EXPECTED_DIMENSIONS

    # 端到端验证 6 步全部存在
    assert set(report["end_to_end_validation"].keys()) == EXPECTED_END_TO_END_STEPS

    # system_score 必须等于 dimension_scores 的最小值
    dim_scores = report["dimension_scores"]
    expected_min = min(dim_scores.values())
    assert report["system_score"] == expected_min, (
        f"system_score={report['system_score']} 不等于 min(dimension_scores)={expected_min}"
    )

    # system_score 取值 0.0 或 1.0
    assert report["system_score"] in (0.0, 1.0)


def test_any_dimension_failure_zeros_system_score():
    """任一维度失败令 system_score=0.0。

    构造一个 7 维度通过、1 维度失败的场景，验证 system_score=0.0。
    用 compute_system_score 直接验证木桶原理。
    """
    # 构造 7 维度通过 + 1 维度失败（code=0.0）的证据
    evidence = {gate: {"passed": True, "result": {}} for gate in [
        "code_tests",
        "physical_metrics",
        "robustness",
        "realtime",
        "safety",
        "documentation",
        "design_review",
        "oral_defense",
    ]}
    # 令 code_tests 失败 → code 维度 0.0
    evidence["code_tests"] = {"passed": False, "result": None}

    scores = compute_system_score(evidence)
    assert scores["system_score"] == 0.0, (
        f"7 通过 1 失败时 system_score 应为 0.0，实际 {scores['system_score']}"
    )
    assert scores["dimension_scores"]["code"] == 0.0
    # 其他维度仍为 1.0
    for dim in ("physics", "robustness", "realtime", "safety", "docs", "design_review", "oral_defense"):
        assert scores["dimension_scores"][dim] == 1.0


def test_all_dimensions_pass_yields_system_score_one():
    """所有维度通过令 system_score=1.0。

    构造 8 维度全部通过的证据，验证 system_score=1.0。
    """
    evidence = {
        "code_tests": {"passed": True, "result": {}},
        "physical_metrics": {"passed": True, "result": {}},
        "robustness": {"passed": True, "result": {}},
        "realtime": {"passed": True, "result": {}},
        "safety": {"passed": True, "result": {}},
        "documentation": {"passed": True, "result": {}},
        "design_review": {"passed": True, "result": {}},
        "oral_defense": {"passed": True, "result": {}},
    }

    scores = compute_system_score(evidence)
    assert scores["system_score"] == 1.0, (
        f"8 维度全通过时 system_score 应为 1.0，实际 {scores['system_score']}"
    )
    for dim, score in scores["dimension_scores"].items():
        assert score == 1.0, f"维度 {dim} 应为 1.0，实际 {score}"


def test_end_to_end_impact_mapping_complete():
    """END_TO_END_IMPACT 应覆盖 6 个步骤，且每个步骤映射到非空维度列表。"""
    assert set(END_TO_END_IMPACT.keys()) == EXPECTED_END_TO_END_STEPS
    for step, dims in END_TO_END_IMPACT.items():
        assert isinstance(dims, list), f"步骤 {step} 的维度映射不是 list"
        assert len(dims) > 0, f"步骤 {step} 的维度映射为空"
        # 维度名必须是 8 个维度之一
        for dim in dims:
            assert dim in EXPECTED_DIMENSIONS, (
                f"步骤 {step} 映射的维度 {dim} 不在 8 个评分维度中"
            )


def test_capstone_robustness_step_uses_only_prior_project_gates():
    sim_data = {
        "physics": {"time": list(range(1000))},
        "code": {"time": list(range(1000))},
        "safety": {},
        "realtime": {},
    }
    steps = {
        name: {"passed": True}
        for name in ("physics", "code", "safety", "realtime")
    }
    evidence = {
        gate: {"passed": gate not in {"design_review", "oral_defense"}}
        for gate in (
            "code_tests",
            "physical_metrics",
            "robustness",
            "realtime",
            "safety",
            "documentation",
            "design_review",
            "oral_defense",
        )
    }

    result = capstone_runner._e2e_run_robustness(sim_data, steps, evidence, [])

    assert result["passed"] is True
    assert result["details"]["gate_passed_count"] == 6
    assert result["details"]["gate_total_count"] == 6


def test_chapter_45_project_pass_does_not_depend_on_chapters_46_and_47(monkeypatch, tmp_path):
    quick = {
        step: {"passed": True, "details": {"elapsed_ms": 0.0}}
        for step in EXPECTED_END_TO_END_STEPS
    }
    pipeline = {
        step: {"passed": True, "details": {"elapsed_ms": 0.0}}
        for step, _ in capstone_runner.E2E_PIPELINE_STEPS
    }
    pipeline.update({"log_path": "e2e.jsonl", "sim_data_path": "sim.json", "simulation_data": {}})
    evidence = {
        "code_tests": {"passed": True, "result": {}},
        "physical_metrics": {"passed": True, "result": {}},
        "robustness": {"passed": True, "result": {}},
        "realtime": {"passed": True, "result": {}},
        "safety": {"passed": True, "result": {}},
        "documentation": {"passed": True, "result": {}},
        "design_review": {"passed": False, "result": None},
        "oral_defense": {"passed": False, "result": None},
    }
    validation_seeds = []

    def fake_validation(_root, *, seed=0):
        validation_seeds.append(seed)
        return quick

    monkeypatch.setattr(capstone_runner, "run_end_to_end_validation", fake_validation)
    monkeypatch.setattr(capstone_runner, "run_e2e_pipeline", lambda _root: pipeline)
    monkeypatch.setattr(capstone_runner, "load_gate_evidence", lambda _root: evidence)

    report = capstone_runner.run_capstone(tmp_path)

    assert report["project_score"] == 1.0
    assert report["passed"] is True
    assert report["system_score"] == 0.0
    assert report["course_readiness_passed"] is False
    assert validation_seeds == [0]


def test_run_capstone_overrides_propagate():
    """端到端验证失败的步骤应记录在 end_to_end_overrides 中。

    当端到端验证某步失败时，对应维度的 dimension_scores 应被强制归零，
    且 end_to_end_overrides 中应记录该步骤和归零的维度列表。
    """
    report = run_capstone("outputs")
    overrides = report["end_to_end_overrides"]
    dim_scores = report["dimension_scores"]

    # 对每个失败的端到端步骤，验证对应维度确实被归零
    for step, impacted_dims in overrides.items():
        # 该步骤确实失败
        assert not report["end_to_end_validation"][step]["passed"], (
            f"步骤 {step} 在 overrides 中但其端到端验证 passed=True"
        )
        # 影响的维度列表与 END_TO_END_IMPACT 一致
        assert impacted_dims == END_TO_END_IMPACT[step], (
            f"步骤 {step} 的 overrides 维度 {impacted_dims} 与 "
            f"END_TO_END_IMPACT 不一致 {END_TO_END_IMPACT[step]}"
        )
        # 对应维度的分数确实被归零
        for dim in impacted_dims:
            assert dim_scores[dim] == 0.0, (
                f"步骤 {step} 失败应令维度 {dim}=0.0，实际 {dim_scores[dim]}"
            )
