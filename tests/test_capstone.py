"""第 45 关综合毕业项目测试。

覆盖：
- run_capstone 返回有效报告
- system_score 等于 dimension_scores 的最小值（木桶原理）
- 8 类毕业门槛全部有证据
- 编排入口写出结果契约 engineering_45.json
- portfolio 报告 engineering_45_report.md 存在
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.capstone import compute_system_score, run_capstone  # noqa: E402

ORCHESTRATOR = ROOT / "scripts" / "run_capstone_project.py"

# 8 类毕业门槛名称
EXPECTED_GATES = {
    "code_tests",
    "physical_metrics",
    "robustness",
    "realtime",
    "safety",
    "documentation",
    "design_review",
    "oral_defense",
}


def test_capstone_runs():
    """run_capstone 应返回包含必要字段的有效报告。"""
    report = run_capstone("outputs")

    assert report["schema_version"] == "1.0"
    assert report["chapter_id"] == "45"
    assert "system_score" in report
    assert "project_score" in report
    assert "dimension_scores" in report
    assert "evidence" in report
    assert "passed" in report
    assert "pass_conditions" in report
    # system_score 是浮点数，取值 0.0 或 1.0
    assert report["system_score"] in (0.0, 1.0)
    # pass_conditions 声明 system_score >= 1.0
    assert report["pass_conditions"]["project_score"]["operator"] == ">="
    assert report["pass_conditions"]["project_score"]["value"] == 1.0
    # passed 与 system_score 一致
    assert report["passed"] == (report["project_score"] >= 1.0)
    assert report["course_readiness_passed"] == (report["system_score"] >= 1.0)


def test_system_score_is_min():
    """system_score 应等于 dimension_scores 的最小值（木桶原理）。"""
    report = run_capstone("outputs")
    dim_scores = report["dimension_scores"]
    expected_min = min(dim_scores.values())
    assert report["system_score"] == expected_min

    # 额外验证：compute_system_score 对纯失败证据也返回 0.0
    all_fail_evidence = {gate: {"passed": False, "result": None} for gate in EXPECTED_GATES}
    fail_scores = compute_system_score(all_fail_evidence)
    assert fail_scores["system_score"] == 0.0
    assert all(v == 0.0 for v in fail_scores["dimension_scores"].values())

    # 额外验证：compute_system_score 对全通过证据返回 1.0
    all_pass_evidence = {gate: {"passed": True, "result": {}} for gate in EXPECTED_GATES}
    pass_scores = compute_system_score(all_pass_evidence)
    assert pass_scores["system_score"] == 1.0
    assert all(v == 1.0 for v in pass_scores["dimension_scores"].values())


def test_evidence_completeness():
    """8 类毕业门槛应全部有证据条目（无论通过与否）。"""
    report = run_capstone("outputs")
    evidence = report["evidence"]
    # 8 类门槛全部存在
    assert set(evidence.keys()) == EXPECTED_GATES
    # 每个证据条目包含 chapter / passed / result 字段
    for gate, ev in evidence.items():
        assert "chapter" in ev, f"门槛 {gate} 缺少 chapter 字段"
        assert "passed" in ev, f"门槛 {gate} 缺少 passed 字段"
        assert "result" in ev, f"门槛 {gate} 缺少 result 字段"
        assert isinstance(ev["passed"], bool)
    # dimension_scores 也应覆盖 8 个维度
    assert len(report["dimension_scores"]) == 8


def test_orchestrator_writes_result_contract(tmp_path):
    """编排入口应写出 engineering_45.json 结果契约。"""
    output_root = tmp_path / "outputs"
    proc = subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr

    result_path = output_root / "results" / "engineering_45.json"
    assert result_path.exists(), f"结果契约未生成：{result_path}"

    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["chapter_id"] == "45"
    assert "system_score" in data["metrics"]
    assert "project_score" in data["metrics"]
    assert "pass_conditions" in data
    assert data["pass_conditions"]["project_score"]["operator"] == ">="
    # tmp_path 无 evidence 文件，system_score 应为 0.0
    assert data["metrics"]["system_score"] == 0.0
    assert data["passed"] is False


def test_portfolio_report_exists(tmp_path):
    """编排入口应生成 portfolio/45/engineering_45_report.md。"""
    output_root = tmp_path / "outputs"
    proc = subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr

    portfolio = output_root / "portfolio" / "45" / "engineering_45_report.md"
    assert portfolio.exists(), f"portfolio 报告未生成：{portfolio}"

    content = portfolio.read_text(encoding="utf-8")
    assert "第 45 关综合毕业项目报告" in content
    assert "system_score" in content
    assert "8 维度评分明细" in content
