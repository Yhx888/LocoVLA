"""第 40 关 ROS2 控制节点测试。

覆盖：
- 编排入口在缺少 WSL2 证据文件时优雅降级（退出码 0，passed=False）
- 结果契约 JSON 包含完整的 schema 字段
- metrics 包含所有预期键
- 提供完整证据时结果通过验收
- portfolio 证据文件正确生成
"""
from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import matplotlib.image as mpimg
import numpy as np
import pytest
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
ORCHESTRATOR = ROOT / "scripts" / "run_engineering_lab_40.py"
PLOT_SCRIPT = ROOT / "scripts" / "tools" / "plot_engineering_40_timing.py"
ROS_FAULT_SCRIPT = ROOT / "scripts" / "tools" / "run_ros2_fault_injection.py"
ENGINEERING_43 = ROOT / "scripts" / "run_engineering_lab_43.py"


def _run_orchestrator(
    output_root: Path,
    *,
    source_root: Path,
) -> subprocess.CompletedProcess:
    """以子进程方式运行第 40 关编排入口。"""
    return subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--output-root", str(output_root),
            "--source-root", str(source_root),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def _populate_evidence(output_root: Path) -> None:
    """在 output_root 中创建完整的第 40 关证据文件。"""
    logs_dir = output_root / "logs"
    plots_dir = output_root / "plots"
    logs_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 写入 timing 数据（满足所有验收条件）
    timing = {
        "sample_count": 1000,
        "period_count": 999,
        "timer_period_ms_target": 10.0,
        "deadline_ms": 12.0,
        "statistics": {
            "mean_period_ms": 9.8,
            "min_period_ms": 9.7,
            "max_period_ms": 10.2,
            "p50_period_ms": 9.8,
            "p99_period_ms": 10.2,
            "deadline_miss_count": 0,
            "deadline_miss_rate": 0.0,
        },
        "offsets_ms": [0.0, 9.8, 19.7, 29.5],
        "periods_ms": [9.8, 9.9, 9.8],
    }
    (logs_dir / "engineering_40_timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 写入 QoS 数据（使 qos_compatible=1）
    qos = {
        "compatible": True,
        "observed": {
            "imu_subscription_count": 1,
            "safety_publisher_count": 1,
            "torque_publisher_count": 1,
            "imu_published_count": 100,
            "safety_received_count": 80,
            "torque_received_count": 80,
        },
    }
    (logs_dir / "engineering_40_qos.json").write_text(
        json.dumps(qos, ensure_ascii=False), encoding="utf-8"
    )
    (logs_dir / "engineering_40_colcon_test.log").write_text(
        "Summary: 34 tests, 0 errors, 0 failures, 0 skipped\n",
        encoding="utf-8",
    )

    plt.imsave(
        plots_dir / "engineering_40.png",
        np.zeros((4, 4, 3), dtype=np.uint8),
    )


def test_missing_evidence_graceful_degradation(tmp_path):
    """缺少 WSL2 证据文件时脚本不应崩溃，应优雅降级并输出结果契约。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, f"脚本意外失败：{proc.stderr}"
    result_path = output_root / "results" / "engineering_40.json"
    assert result_path.exists(), f"结果契约未生成：{result_path}"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    # 缺少 QoS 证据时 qos_compatible=0，不满足 ==1 的验收条件
    assert data["passed"] is False, "缺少证据时结果应为未通过"


def test_result_contract_schema(tmp_path):
    """结果契约应包含完整的 schema 字段。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_40.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    # 校验必要的顶层字段
    expected_keys = [
        "schema_version", "chapter_id", "created_at", "git_commit",
        "seed", "config", "metrics", "pass_conditions", "checks",
        "passed", "plots", "videos", "logs",
    ]
    for key in expected_keys:
        assert key in data, f"结果契约缺少字段：{key}"

    assert data["schema_version"] == "2.0"
    assert data["chapter_id"] == "40"
    assert data["seed"] == 0
    assert data["source_state"]["source_digest"]


def test_metrics_keys_present(tmp_path):
    """metrics 应包含所有第 40 关预期指标。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_40.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    expected_metrics = [
        "sample_count", "mean_period_ms", "p99_period_ms",
        "deadline_miss_count", "gtest_count", "gtest_errors", "gtest_failures",
        "qos_compatible",
    ]
    for key in expected_metrics:
        assert key in data["metrics"], f"metrics 缺少键：{key}"


def test_config_contains_ros2_fields(tmp_path):
    """config 应包含 ROS2 相关配置字段。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_40.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    config = data["config"]
    assert config["ros2_distro"] == "jazzy"
    assert config["control_rate_hz"] == 100
    assert "build_base" in config
    assert "install_base" in config


def test_with_complete_evidence_passes(tmp_path):
    """提供完整证据文件时结果应通过所有验收条件。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_40.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    assert data["passed"] is True, (
        f"完整证据下应通过验收，但 checks={data['checks']}"
    )
    assert data["metrics"]["gtest_failures"] == 0.0
    assert data["metrics"]["gtest_errors"] == 0.0
    assert data["metrics"]["gtest_count"] == 34.0
    assert data["metrics"]["deadline_miss_count"] == 0.0
    assert data["metrics"]["qos_compatible"] == 1.0
    assert data["metrics"]["mean_period_ms"] <= 10.5
    # 绘图文件应被收集
    assert len(data["plots"]) == 1


def test_portfolio_evidence_created(tmp_path):
    """编排入口应生成 portfolio 证据文件。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    portfolio = output_root / "portfolio" / "40" / "evidence.json"
    assert portfolio.exists(), f"portfolio 证据文件未生成：{portfolio}"
    data = json.loads(portfolio.read_text(encoding="utf-8"))
    assert data["chapter_id"] == "40"
    assert data["passed"] is False
    assert data["metrics"]
    assert "plots" in data
    assert "logs" in data


def test_default_metrics_when_timing_missing(tmp_path):
    """缺少 timing.json 时应使用合理的默认值。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_40.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    # fresh 目录不能凭空声称已经运行过 GTest。
    assert data["metrics"]["gtest_count"] == 0.0
    assert data["metrics"]["gtest_failures"] == 0.0
    # 默认 timing 全为零
    assert data["metrics"]["sample_count"] == 0.0
    assert data["metrics"]["mean_period_ms"] == 0.0


def test_qos_requires_real_endpoint_and_message_observations(tmp_path):
    """只有 compatible=true、但没有实际收发计数时不得通过。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)
    qos_path = output_root / "logs" / "engineering_40_qos.json"
    qos_path.write_text(
        json.dumps({"compatible": True, "observed": {}}),
        encoding="utf-8",
    )

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(
        (output_root / "results" / "engineering_40.json").read_text(encoding="utf-8")
    )
    assert data["metrics"]["qos_compatible"] == 0.0
    assert data["passed"] is False


def test_zero_gtests_cannot_pass_complete_evidence(tmp_path):
    """零测试不能借助零失败和其他完整证据伪装成通过。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)
    (output_root / "logs" / "engineering_40_colcon_test.log").unlink()

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(
        (output_root / "results" / "engineering_40.json").read_text(encoding="utf-8")
    )
    assert data["metrics"]["gtest_count"] == 0.0
    assert data["checks"]["gtest_count"] is False
    assert data["passed"] is False


def test_timing_json_cannot_spoof_colcon_test_result(tmp_path):
    """timing JSON 中手填测试数不能替代真实 colcon 日志。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)
    colcon_log = output_root / "logs" / "engineering_40_colcon_test.log"
    colcon_log.unlink()
    timing_path = output_root / "logs" / "engineering_40_timing.json"
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["gtest_count"] = 999
    timing["gtest_failures"] = 0
    timing_path.write_text(json.dumps(timing), encoding="utf-8")

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(
        (output_root / "results" / "engineering_40.json").read_text(encoding="utf-8")
    )
    assert data["metrics"]["gtest_count"] == 0.0
    assert data["checks"]["gtest_count"] is False
    assert data["passed"] is False


def test_colcon_failures_are_parsed_and_rejected(tmp_path):
    """格式正确但包含失败的 colcon 摘要必须进入指标并阻断通过。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)
    (output_root / "logs" / "engineering_40_colcon_test.log").write_text(
        "Summary: 34 tests, 0 errors, 1 failure, 0 skipped\n",
        encoding="utf-8",
    )

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(
        (output_root / "results" / "engineering_40.json").read_text(encoding="utf-8")
    )
    assert data["metrics"]["gtest_count"] == 34.0
    assert data["metrics"]["gtest_failures"] == 1.0
    assert data["checks"]["gtest_failures"] is False
    assert data["passed"] is False


def test_colcon_errors_are_parsed_and_rejected(tmp_path):
    """CTest error 不能因 failures=0 被忽略。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)
    (output_root / "logs" / "engineering_40_colcon_test.log").write_text(
        "Summary: 34 tests, 1 error, 0 failures, 0 skipped\n",
        encoding="utf-8",
    )

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(
        (output_root / "results" / "engineering_40.json").read_text(encoding="utf-8")
    )
    assert data["metrics"]["gtest_errors"] == 1.0
    assert data["checks"]["gtest_errors"] is False
    assert data["passed"] is False


@pytest.mark.parametrize(
    "content",
    [
        "",
        "all tests passed\n",
        "Summary: 34 tests, 0 failures\n",
        "Summary: thirty-four tests, 0 errors, 0 failures, 0 skipped\n",
        "Summary: 34 tests, 0 errors, -1 failures, 0 skipped\n",
    ],
)
def test_malformed_colcon_summary_cannot_pass(tmp_path, content):
    """仅接受 colcon test-result 的完整数字 Summary 行。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)
    (output_root / "logs" / "engineering_40_colcon_test.log").write_text(
        content,
        encoding="utf-8",
    )

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(
        (output_root / "results" / "engineering_40.json").read_text(encoding="utf-8")
    )
    assert data["metrics"]["gtest_count"] == 0.0
    assert data["metrics"]["gtest_errors"] == 0.0
    assert data["metrics"]["gtest_failures"] == 0.0
    assert data["passed"] is False


def test_truncated_png_is_not_accepted_as_plot_evidence(tmp_path):
    """仅有 PNG 文件头的截断文件不能进入结果证据。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)
    (output_root / "plots" / "engineering_40.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    proc = _run_orchestrator(output_root, source_root=tmp_path)

    assert proc.returncode == 0, proc.stderr
    data = json.loads(
        (output_root / "results" / "engineering_40.json").read_text(encoding="utf-8")
    )
    assert data["plots"] == []
    assert data["passed"] is False


def test_plot_script_accepts_output_root_and_real_nested_statistics(tmp_path):
    """绘图脚本应直接解析 control_node 的嵌套 statistics 格式。"""
    output_root = tmp_path / "outputs"
    _populate_evidence(output_root)

    proc = subprocess.run(
        [
            sys.executable,
            str(PLOT_SCRIPT),
            "--output-root",
            str(output_root),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    image_path = output_root / "plots" / "engineering_40.png"
    image = mpimg.imread(image_path)
    assert image.shape[0] >= 100
    assert image.shape[1] >= 100
    assert image.size > 10_000


def _load_ros_fault_module():
    spec = importlib.util.spec_from_file_location("ros2_fault_test_module", ROS_FAULT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ros2_fault_cli_exposes_fresh_output_and_install_prefix():
    """Windows 侧无需 ROS2 也应能检查故障脚本命令接口。"""
    proc = subprocess.run(
        [sys.executable, str(ROS_FAULT_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    assert "--output-root" in proc.stdout
    assert "--install-prefix" in proc.stdout


def test_ros2_fault_paths_and_control_command_are_bound_to_fresh_root(tmp_path):
    """故障、时序、QoS 和统一日志必须落在同一个 fresh 根目录。"""
    module = _load_ros_fault_module()
    paths = module.resolve_output_paths(str(tmp_path / "outputs"))
    assert paths["fault_result"].endswith(
        "/results/engineering_43_ros2_fault_injection.json"
    )
    assert paths["timing_log"].endswith("/logs/engineering_40_timing.json")
    assert paths["qos_log"].endswith("/logs/engineering_40_qos.json")
    assert paths["control_log"].endswith("/logs/engineering_42_log.jsonl")

    windows_paths = module.resolve_output_paths(r"C:\fresh evidence\outputs")
    assert windows_paths["fault_result"].startswith("/mnt/c/fresh evidence/outputs/")

    command = module.build_control_command(
        paths,
        install_prefix="/tmp/upkie install",
    )
    assert "/tmp/upkie install/setup.bash" in command
    assert "record_timing:=true" in command
    assert f"record_timing_path:={paths['timing_log']}" in command
    assert "record_log:=true" in command
    assert f"log_path:={paths['control_log']}" in command


def test_engineering_43_accepts_explicit_source_root(tmp_path):
    """第 43 关编排结果应能写入 fresh 项目根且绑定其源码摘要。"""
    output_root = tmp_path / "outputs"
    proc = subprocess.run(
        [
            sys.executable,
            str(ENGINEERING_43),
            "--output-root",
            str(output_root),
            "--source-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(
        (output_root / "results" / "engineering_43.json").read_text(encoding="utf-8")
    )
    assert result["schema_version"] == "2.0"
    assert result["source_state"]["source_digest"]
