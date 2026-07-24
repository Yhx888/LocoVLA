"""第 41 关实时循环与并发测试。

覆盖：
- 编排入口在跳过基准测试且无已有数据时优雅降级（退出码 0，passed=False）
- 结果契约 JSON 包含完整的 schema 字段
- metrics 包含实时性相关指标
- 已有通过结果被正确识别并提前退出
- CSV 原始数据被正确解析为统计指标
- portfolio 报告正确生成
"""
from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from matplotlib import pyplot as plt

from upkie_mujoco_course.course.checkpoint import _markdown_portfolio_is_substantive
from upkie_mujoco_course.course.results import write_experiment_result

ROOT = Path(__file__).resolve().parent.parent
ORCHESTRATOR = ROOT / "scripts" / "run_engineering_lab_41.py"
ANALYZER = ROOT / "scripts" / "analyze_realtime_lab.py"


def _load_orchestrator_module():
    spec = importlib.util.spec_from_file_location("run_engineering_lab_41", ORCHESTRATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_orchestrator(
    output_root: Path,
    *,
    skip_benchmark: bool = True,
    duration: int = 1,
) -> subprocess.CompletedProcess:
    """以子进程方式运行第 41 关编排入口。"""
    cmd = [
        sys.executable, str(ORCHESTRATOR),
        "--output-root", str(output_root),
        "--source-root", str(output_root.parent),
    ]
    if skip_benchmark:
        cmd.append("--skip-benchmark")
    else:
        cmd.extend(["--duration", str(duration)])
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(ROOT),
    )


def test_skip_benchmark_graceful_degradation(tmp_path):
    """跳过基准测试且无已有数据时，脚本应优雅降级并输出结果契约。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, f"脚本意外失败：{proc.stderr}"
    result_path = output_root / "results" / "engineering_41.json"
    assert result_path.exists(), f"结果契约未生成：{result_path}"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    # sample_count=0 < 5000，不满足验收条件
    assert data["passed"] is False, "无实际数据时结果应为未通过"


def test_result_contract_schema(tmp_path):
    """结果契约应包含完整的 schema 字段。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_41.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    expected_keys = [
        "schema_version", "chapter_id", "created_at", "git_commit",
        "seed", "config", "metrics", "pass_conditions", "checks",
        "passed", "plots", "videos", "logs",
    ]
    for key in expected_keys:
        assert key in data, f"结果契约缺少字段：{key}"

    assert data["schema_version"] == "2.0"
    assert data["chapter_id"] == "41"
    assert data["seed"] == 0


def test_metrics_keys_present(tmp_path):
    """metrics 应包含实时性相关指标。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_41.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    expected_metrics = [
        "sample_count", "improved_p99_ms",
        "improved_max_ms", "improved_deadline_miss_count",
    ]
    for key in expected_metrics:
        assert key in data["metrics"], f"metrics 缺少键：{key}"


def test_config_contains_timing_fields(tmp_path):
    """config 应包含定时基准测试相关配置。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_41.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    config = data["config"]
    assert config["period_ms"] == 10
    assert config["timer_resolution_ms"] == 1
    assert "duration_s" in config


def test_legacy_passing_result_is_not_reused(tmp_path):
    """旧契约即使 passed=true 也不得作为当前结果直接复用。"""
    output_root = tmp_path / "outputs"
    result_dir = output_root / "results"
    result_dir.mkdir(parents=True, exist_ok=True)

    # 写入一份已通过的旧结果
    old_result = {
        "schema_version": "1.0",
        "chapter_id": "41",
        "passed": True,
        "metrics": {"sample_count": 6000, "improved_p99_ms": 10.5},
    }
    (result_dir / "engineering_41.json").write_text(
        json.dumps(old_result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    assert "已有通过结果" not in proc.stdout
    data = json.loads(
        (result_dir / "engineering_41.json").read_text(encoding="utf-8")
    )
    assert data["schema_version"] == "2.0"
    assert data["passed"] is False
    assert data["metrics"]["sample_count"] == 0.0


@pytest.mark.parametrize("old_portfolio", [None, "# 旧版报告\n\n- 只有参数\n"])
def test_skip_benchmark_rebuilds_portfolio_from_valid_result(tmp_path, old_portfolio):
    """已有当前通过结果时，跳过基准也必须补齐当前 portfolio。"""
    output_root = tmp_path / "outputs"
    plot_path = output_root / "plots" / "engineering_41.png"
    log_path = output_root / "logs" / "engineering_41.json"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(plot_path, np.zeros((2, 2, 3), dtype=np.uint8))
    log_path.write_text('{"sample_count": 6000}\n', encoding="utf-8")
    write_experiment_result(
        output_root / "results" / "engineering_41.json",
        chapter_id="41",
        seed=41,
        config={"duration_s": 60, "period_ms": 10, "timer_resolution_ms": 1},
        metrics={
            "sample_count": 6000.0,
            "improved_p99_ms": 10.0,
            "improved_max_ms": 10.0,
            "improved_deadline_miss_count": 0.0,
        },
        pass_conditions={
            "sample_count": {"operator": ">=", "value": 5000},
            "improved_p99_ms": {"operator": "<", "value": 12},
            "improved_deadline_miss_count": {"operator": "==", "value": 0},
        },
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=tmp_path,
    )
    if old_portfolio is not None:
        portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
        portfolio.parent.mkdir(parents=True, exist_ok=True)
        portfolio.write_text(old_portfolio, encoding="utf-8")

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
    assert portfolio.is_file()
    content = portfolio.read_text(encoding="utf-8")
    assert _markdown_portfolio_is_substantive(content)
    assert "P99 周期" in content
    assert "最大周期" in content
    assert "deadline miss" in content


def test_skip_benchmark_preserves_substantive_analysis_portfolio(tmp_path):
    """已有分析报告包含动态证据时，跳过基准不得覆盖其内容。"""
    output_root = tmp_path / "outputs"
    plot_path = output_root / "plots" / "engineering_41.png"
    log_path = output_root / "logs" / "engineering_41.json"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(plot_path, np.zeros((2, 2, 3), dtype=np.uint8))
    log_path.write_text('{"sample_count": 6000}\n', encoding="utf-8")
    write_experiment_result(
        output_root / "results" / "engineering_41.json",
        chapter_id="41",
        seed=41,
        config={"duration_s": 60, "period_ms": 10, "timer_resolution_ms": 1},
        metrics={
            "sample_count": 6000.0,
            "improved_p99_ms": 10.0,
            "improved_max_ms": 10.0,
            "improved_deadline_miss_count": 0.0,
        },
        pass_conditions={
            "sample_count": {"operator": ">=", "value": 5000},
            "improved_p99_ms": {"operator": "<", "value": 12},
            "improved_deadline_miss_count": {"operator": "==", "value": 0},
        },
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=tmp_path,
    )
    portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        "# 第 41 关实时循环报告\n\n"
        "## 指标\n\n"
        "- baseline_p99: `11.111 ms`\n"
        "- baseline_deadline_miss: `7`\n"
        "- compute_p99: `2.222 ms`\n"
        "- 自定义证据：analyzer-run-2026\n",
        encoding="utf-8",
    )

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    content = portfolio.read_text(encoding="utf-8")
    assert "baseline_p99" in content
    assert "baseline_deadline_miss" in content
    assert "compute_p99" in content
    assert "analyzer-run-2026" in content


def test_csv_data_processed_correctly(tmp_path):
    """已有 CSV 原始数据配合 --skip-benchmark 应被解析为统计指标。"""
    output_root = tmp_path / "outputs"
    logs_dir = output_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 写入 CSV 原始周期数据（表头 + 5 行数据）
    csv_lines = ["period_ms\n"]
    periods = [9.8, 10.0, 10.1, 10.3, 10.5]
    for p in periods:
        csv_lines.append(f"{p}\n")
    (logs_dir / "engineering_41_realtime_raw.csv").write_text(
        "".join(csv_lines), encoding="utf-8"
    )

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_41.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    # 校验 CSV 被正确解析
    metrics = data["metrics"]
    assert metrics["sample_count"] == 5.0
    # p99 索引 = int(5 * 0.99) = 4，排序后 periods[4] = 10.5
    assert metrics["improved_p99_ms"] == 10.5
    assert metrics["improved_max_ms"] == 10.5
    # 所有值 < 12ms，无 deadline miss
    assert metrics["improved_deadline_miss_count"] == 0.0
    # sample_count=5 < 5000，总体不通过
    assert data["passed"] is False


def test_portfolio_report_created(tmp_path):
    """编排入口应生成 portfolio 实时延迟报告。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
    assert portfolio.exists(), f"portfolio 报告未生成：{portfolio}"
    content = portfolio.read_text(encoding="utf-8")
    assert "实时基线" in content or "实时" in content
    assert "100Hz" in content or "10ms" in content
    assert _markdown_portfolio_is_substantive(content)


def test_default_metrics_when_skip_and_no_data(tmp_path):
    """跳过基准测试且无任何数据时，metrics 应为零值。"""
    output_root = tmp_path / "outputs"

    proc = _run_orchestrator(output_root)

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_41.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    assert data["metrics"]["sample_count"] == 0.0
    assert data["metrics"]["improved_p99_ms"] == 0.0
    assert data["metrics"]["improved_max_ms"] == 0.0
    assert data["metrics"]["improved_deadline_miss_count"] == 0.0


def test_real_benchmark_branch_writes_checkpoint_evidence(tmp_path, monkeypatch):
    """真实分支应把采样、日志和图写入空输出根并登记到契约。"""
    module = _load_orchestrator_module()
    output_root = tmp_path / "outputs"
    portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        "# 第 41 关实时循环报告\n\n"
        "## 指标\n\n"
        "- baseline_p99: `11.111 ms`\n"
        "- baseline_deadline_miss: `7`\n"
        "- compute_p99: `2.222 ms`\n"
        "- 自定义证据：analyzer-run-2026\n",
        encoding="utf-8",
    )
    stats = {
        "sample_count": 6000,
        "mean_period_ms": 10.0,
        "p99_period_ms": 10.0,
        "max_period_ms": 10.0,
        "min_period_ms": 10.0,
        "deadline_miss_count": 0,
        "high_resolution_timer": True,
        "periods_ms": [10.0] * 6000,
    }
    monkeypatch.setattr(module, "_run_timing_benchmark", lambda duration_s: stats)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(ORCHESTRATOR),
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
            "--duration", "60",
        ],
    )

    assert module.main() == 0
    result = json.loads(
        (output_root / "results" / "engineering_41.json").read_text(encoding="utf-8")
    )
    assert result["passed"] is True
    assert result["plots"]
    assert result["logs"]
    for reference in [*result["plots"], *result["logs"]]:
        assert (tmp_path / reference).is_file(), reference
    content = portfolio.read_text(encoding="utf-8")
    assert "baseline_p99" in content
    assert "baseline_deadline_miss" in content
    assert "compute_p99" in content
    assert "analyzer-run-2026" in content


def test_analyzer_writes_all_artifacts_to_explicit_output_root(tmp_path):
    """分析入口不得把结果写回仓库默认 outputs。"""
    output_root = tmp_path / "outputs"
    logs_dir = output_root / "logs"
    logs_dir.mkdir(parents=True)
    header = "tick,start_ns,period_ns,compute_ns,deadline_miss,balance_nm,left_nm,right_nm\n"
    baseline_rows = [
        f"{tick},{tick * 10000000},10000000,10000,0,0.1,0.1,-0.1\n"
        for tick in range(6000)
    ]
    improved_rows = [
        f"{tick},{tick * 10000000},10000000,8000,0,0.1,0.1,-0.1\n"
        for tick in range(6000)
    ]
    (logs_dir / "engineering_41_realtime_raw.csv").write_text(
        header + "".join(baseline_rows), encoding="utf-8"
    )
    (logs_dir / "engineering_41_high_resolution_raw.csv").write_text(
        header + "".join(improved_rows), encoding="utf-8"
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(ANALYZER),
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(
        (output_root / "results" / "engineering_41.json").read_text(encoding="utf-8")
    )
    assert result["passed"] is True
    for reference in [*result["plots"], *result["logs"]]:
        assert (tmp_path / reference).is_file(), reference
    assert (output_root / "portfolio" / "41" / "realtime_latency_report.md").is_file()
