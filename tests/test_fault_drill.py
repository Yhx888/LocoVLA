"""第 46 关综合故障演练测试。

覆盖：
- 故障演练脚本可运行（退出码 0）
- 4 大类故障全部覆盖（sensor/actuator/communication/software）
- 所有故障被检测（faults_detected == fault_types_injected）
- 平均检测延迟 ≤ 200ms
- 故障时间线图存在
- 编排脚本写出结果契约 engineering_46.json 且 passed=True
- 故障演练实验报告 fault_drill_46.md 存在
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FAULT_DRILL_SCRIPT = ROOT / "scripts" / "tools" / "run_fault_drill.py"
ORCHESTRATOR = ROOT / "scripts" / "run_engineering_lab_46.py"

# 4 大类故障的期望集合
_EXPECTED_FAULT_TYPES = {"sensor", "actuator", "communication", "software"}


@pytest.fixture(scope="module")
def fault_summary(tmp_path_factory):
    """运行故障演练脚本一次，返回 (汇总 JSON, 输出目录)。

    使用 module 级 scope 避免重复运行子进程，输出到临时目录不污染仓库。
    """
    out_dir = tmp_path_factory.mktemp("fault_46")
    out_path = out_dir / "engineering_46_fault_drill.json"
    plot_path = out_dir / "engineering_46_fault_timeline.png"
    proc = subprocess.run(
        [
            sys.executable, str(FAULT_DRILL_SCRIPT),
            "--output", str(out_path),
            "--plot", str(plot_path),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, f"故障演练脚本退出码非 0：\n{proc.stderr}"
    assert out_path.exists(), f"故障演练 JSON 未生成：{out_path}"
    assert plot_path.exists(), f"故障时间线图未生成：{plot_path}"
    summary = json.loads(out_path.read_text(encoding="utf-8"))
    return summary, out_dir


@pytest.fixture(scope="module")
def orchestrator_output(tmp_path_factory):
    """运行第 46 关编排脚本一次，返回 output_root 路径。"""
    output_root = tmp_path_factory.mktemp("engineering_46")
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


def test_fault_drill_runs(fault_summary):
    """故障演练脚本应成功运行并产出汇总 JSON。"""
    summary, _ = fault_summary
    assert "fault_types_injected" in summary
    assert "faults" in summary
    assert "faults_detected" in summary


def test_fault_types_covered(fault_summary):
    """4 大类故障全部覆盖（sensor/actuator/communication/software）。"""
    summary, _ = fault_summary
    actual_types = {f["fault_type"] for f in summary["faults"]}
    missing = _EXPECTED_FAULT_TYPES - actual_types
    assert not missing, f"缺少故障大类：{missing}，实际：{actual_types}"


def test_all_faults_detected(fault_summary):
    """所有故障被检测（faults_detected == fault_types_injected）。"""
    summary, _ = fault_summary
    assert summary["faults_detected"] == summary["fault_types_injected"]
    for fault in summary["faults"]:
        assert fault["safe"] is True, f"{fault['fault_name']} 未进入 FAULT"
        assert fault["final_state"] == "FAULT"


def test_detection_latency_within_200ms(fault_summary):
    """平均检测延迟应 ≤ 200ms。"""
    summary, _ = fault_summary
    assert summary["mean_detection_latency_ms"] <= 200


def test_fault_timeline_plot_exists(fault_summary):
    """故障时间线图 engineering_46_fault_timeline.png 应存在且非空。"""
    _, out_dir = fault_summary
    plot_path = out_dir / "engineering_46_fault_timeline.png"
    assert plot_path.exists(), f"故障时间线图未生成：{plot_path}"
    assert plot_path.stat().st_size > 0, "故障时间线图为空文件"


def test_orchestrator_writes_result_contract(orchestrator_output):
    """编排脚本应写出 engineering_46.json 结果契约且 passed=True。"""
    result_path = orchestrator_output / "results" / "engineering_46.json"
    assert result_path.exists(), f"结果契约未生成：{result_path}"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["chapter_id"] == "46"
    assert data["passed"] is True
    assert data["metrics"]["fault_types_injected"] == 9.0
    assert data["metrics"]["faults_detected"] == 9.0
    assert data["metrics"]["coverage_percent"] == 100.0
    assert data["metrics"]["mean_detection_latency_ms"] <= 200.0


def test_fault_drill_report_exists(orchestrator_output):
    """故障演练实验报告 fault_drill_46.md 应存在且非空。"""
    report_path = orchestrator_output / "reports" / "fault_drill_46.md"
    assert report_path.exists(), f"实验报告未生成：{report_path}"
    content = report_path.read_text(encoding="utf-8")
    assert len(content) > 0
    # 报告应包含关键章节
    assert "评审摘要" in content
    assert "故障注入矩阵" in content
    assert "根因分析" in content
    assert "纠正动作" in content
    assert "评审结论" in content
    assert "FAULT" in content
