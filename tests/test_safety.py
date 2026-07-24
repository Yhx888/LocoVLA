"""第 43 关安全状态机故障演练测试。

覆盖：
- 故障演练脚本可运行（退出码 0）
- 全部 5 种故障最终进入 FAULT
- 故障数为 5
- 平均检测延迟 ≤ 200ms
- 非 ARMED 状态制动延迟为 0
- 编排脚本写出结果契约 engineering_43.json
- portfolio 报告 engineering_43_report.md 存在
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FAULT_SCRIPT = ROOT / "scripts" / "tools" / "run_safety_fault_injection.py"
ORCHESTRATOR = ROOT / "scripts" / "run_engineering_lab_43.py"


def _write_colcon_summary(output_root: Path) -> Path:
    path = output_root / "logs" / "engineering_40_colcon_test.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "Summary: 42 tests, 0 errors, 0 failures, 0 skipped\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture(scope="module")
def fault_summary(tmp_path_factory):
    """运行故障演练脚本一次，返回解析后的汇总 JSON。

    使用 module 级 scope 避免重复运行子进程，输出到临时目录不污染仓库。
    """
    out_dir = tmp_path_factory.mktemp("fault_43")
    out_path = out_dir / "engineering_43_fault_injection.json"
    proc = subprocess.run(
        [sys.executable, str(FAULT_SCRIPT), "--output", str(out_path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, f"故障演练脚本退出码非 0：\n{proc.stderr}"
    assert out_path.exists(), f"故障演练 JSON 未生成：{out_path}"
    return json.loads(out_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def orchestrator_output(tmp_path_factory):
    """运行第 43 关编排脚本一次，返回 output_root 路径。"""
    output_root = tmp_path_factory.mktemp("engineering_43")
    _write_colcon_summary(output_root)
    proc = subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--output-root", str(output_root),
            "--source-root", str(output_root),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, f"编排脚本退出码非 0：\n{proc.stderr}"
    return output_root


def test_fault_injection_runs(fault_summary):
    """故障演练脚本应成功运行并产出汇总 JSON。"""
    assert "fault_count" in fault_summary
    assert "faults" in fault_summary


def test_all_faults_safe(fault_summary):
    """所有故障最终应进入 FAULT（safe=True）。"""
    assert fault_summary["all_faults_safe"] is True
    for fault in fault_summary["faults"]:
        assert fault["safe"] is True, f"{fault['fault_name']} 未进入 FAULT"
        assert fault["final_state"] == "FAULT"


def test_fault_count_is_five(fault_summary):
    """应注入 5 种故障。"""
    assert fault_summary["fault_count"] == 5
    assert len(fault_summary["faults"]) == 5


def test_detection_latency_within_200ms(fault_summary):
    """平均检测延迟应 ≤ 200ms。"""
    assert fault_summary["mean_detection_latency_ms"] <= 200


def test_brake_latency_zero(fault_summary):
    """非 ARMED 状态制动延迟应为 0。"""
    for fault in fault_summary["faults"]:
        assert fault["final_state"] != "ARMED"
        assert fault["brake_latency_ms"] == 0.0
    assert fault_summary["mean_brake_latency_ms"] == 0.0


def test_orchestrator_writes_result_contract(orchestrator_output):
    """编排脚本应写出 engineering_43.json 结果契约且 passed=True。"""
    result_path = orchestrator_output / "results" / "engineering_43.json"
    assert result_path.exists(), f"结果契约未生成：{result_path}"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["chapter_id"] == "43"
    assert data["seed"] == 0
    assert data["metrics"]["gtest_count"] == 42.0
    assert data["passed"] is True
    assert data["metrics"]["fault_count"] == 5.0
    assert data["metrics"]["detected_count"] == 5.0
    assert data["metrics"]["all_faults_safe"] == 1.0
    assert data["metrics"]["gtest_failures"] == 0.0
    assert data["plots"]
    for reference in data["plots"]:
        assert (orchestrator_output / reference).is_file(), reference


def test_portfolio_report_exists(orchestrator_output):
    """portfolio 报告 engineering_43_report.md 应存在且非空。"""
    portfolio = orchestrator_output / "portfolio" / "43" / "engineering_43_report.md"
    assert portfolio.exists(), f"portfolio 报告未生成：{portfolio}"
    content = portfolio.read_text(encoding="utf-8")
    assert len(content) > 0
    # 报告应包含安全分析表与故障树关键词
    assert "安全分析表" in content
    assert "故障树" in content
    assert "FAULT" in content


def test_orchestrator_does_not_register_stale_plots(tmp_path):
    """当前输入未生成的时间线图不得从同一输出根的旧文件中登记。"""
    output_root = tmp_path / "outputs"
    plots_dir = output_root / "plots"
    plots_dir.mkdir(parents=True)
    stale_names = {
        "engineering_43_state_timeline.png",
        "engineering_43_torque_gating.png",
    }
    for name in stale_names:
        (plots_dir / name).write_bytes(b"old plot")
    _write_colcon_summary(output_root)

    proc = subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--output-root", str(output_root),
            "--source-root", str(output_root),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(
        (output_root / "results" / "engineering_43.json").read_text(encoding="utf-8")
    )
    assert result["plots"] == ["plots/engineering_43_detection_latency.png"]
    assert all((plots_dir / name).is_file() for name in stale_names)
