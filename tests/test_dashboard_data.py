"""测试仪表板数据构建（course.dashboard_data）。

覆盖场景：
- build_dashboard_summary 汇总字段结构
- collect_chapter_evidence 收集各章节证据
- load_experiment_results 加载实验结果
"""
from upkie_mujoco_course.course.dashboard_data import build_dashboard_summary
from upkie_mujoco_course.course.dashboard_data import collect_chapter_evidence
from upkie_mujoco_course.course.dashboard_data import load_experiment_results
from upkie_mujoco_course.course.manifest import load_course_manifest
from pathlib import Path


def test_dashboard_summary_reports_stage_and_next_ready_chapter():
    manifest = load_course_manifest()
    progress = {
        "chapters": {
            "00": {"completed_checkpoints": ["验收"], "evidence": ["通过"]},
        }
    }
    summary = build_dashboard_summary(manifest, progress)
    assert summary["total_chapters"] == 58
    assert summary["completed_chapters"] == 1
    assert summary["next_chapter"]["id"] == "01"
    assert summary["stages"][0]["completed"] == 1


def test_dashboard_summary_counts_passed_results_as_evidence():
    manifest = load_course_manifest()
    results = [
        {"chapter_id": "35", "passed": True},
        {"chapter_id": "36", "passed": True},
        {"chapter_id": "37", "passed": False},
    ]

    summary = build_dashboard_summary(manifest, {"chapters": {}}, results)

    assert summary["completed_chapters"] == 0
    vla_stage = next(stage for stage in summary["stages"] if stage["id"] == "5")
    assert vla_stage["completed"] == 0


def test_chapter_evidence_merges_progress_and_automatic_results():
    progress = {"chapters": {"37": {"evidence": ["口头复盘通过"]}}}
    results = [
        {
            "chapter_id": "37",
            "passed": True,
            "acceptance_valid": True,
            "contract_status": "current",
            "result_path": "outputs/results/checkpoint_37.json",
        },
    ]

    evidence = collect_chapter_evidence(progress, results, "37")

    assert evidence[0] == "口头复盘通过"
    assert "自动验收通过" in evidence[1]
    assert "checkpoint_37.json" in evidence[1]


def test_chapter_evidence_marks_legacy_stale_and_invalid_as_history():
    results = [
        {
            "chapter_id": "37",
            "passed": True,
            "acceptance_valid": False,
            "contract_status": status,
            "result_path": f"outputs/results/{status}.json",
        }
        for status in ("legacy", "stale", "invalid")
    ]

    evidence = collect_chapter_evidence({"chapters": {}}, results, "37")

    assert len(evidence) == 1
    assert "历史/无效证据" in evidence[0]
    assert "自动验收通过" not in evidence[0]


def test_diagnostic_fault_result_does_not_override_primary_acceptance():
    results = [
        {
            "chapter_id": "11",
            "passed": True,
            "acceptance_valid": True,
            "contract_status": "current",
            "config": {"inject_fault": None},
            "result_path": "outputs/results/model_contract_11.json",
        },
        {
            "chapter_id": "11",
            "passed": False,
            "config": {"inject_fault": "wheel_semantics"},
            "result_path": "outputs/results/model_contract_11_wheel_semantics.json",
        },
    ]

    evidence = collect_chapter_evidence({"chapters": {}}, results, "11")

    assert evidence == ["自动验收通过：outputs/results/model_contract_11.json"]


def test_dashboard_sidebar_select_text_has_explicit_dark_color():
    source = Path("dashboard/app.py").read_text(encoding="utf-8")
    assert '[data-testid="stSidebar"] [data-baseweb="select"]' in source
    assert '[data-testid="stSidebar"] input[role="combobox"]' in source
    assert "color:#17201d" in source


def test_dashboard_loads_results_and_exposes_failed_checks(tmp_path):
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    (result_dir / "pass.json").write_text(
        '{"chapter_id":"12","passed":true,"metrics":{"max_pitch":0.1},"checks":{"pitch":true}}',
        encoding="utf-8",
    )
    (result_dir / "fail.json").write_text(
        '{"chapter_id":"24","passed":false,"metrics":{"solve_ms":25},"checks":{"latency":false}}',
        encoding="utf-8",
    )
    results = load_experiment_results(tmp_path)
    assert [item["chapter_id"] for item in results] == ["12", "24"]
    assert results[1]["failed_checks"] == ["latency"]
    assert all(item["contract_status"] == "legacy" for item in results)
    assert all(item["acceptance_valid"] is False for item in results)
