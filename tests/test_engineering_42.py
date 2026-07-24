"""第 42 关日志分析系统测试。

覆盖：
- 正常日志生成两张图表
- 缺失 timestamp_ns 字段被拒绝（退出码 1）
- 时间戳乱序被拒绝（退出码 1）
- JSON 解析失败被拒绝（退出码 1）
- 编排入口写出结果契约
"""
from __future__ import annotations

import json
import importlib.util
import shlex
import subprocess
import sys
from pathlib import Path

from upkie_mujoco_course.course.checkpoint import _markdown_portfolio_is_substantive
from upkie_mujoco_course.course.manifest import load_course_manifest
from upkie_mujoco_course.capstone.runner import _validate_log_contract
import upkie_mujoco_course.engineering as engineering_contract

ROOT = Path(__file__).resolve().parent.parent
ANALYZE_SCRIPT = ROOT / "scripts" / "tools" / "analyze_engineering_42_logs.py"
ORCHESTRATOR = ROOT / "scripts" / "run_engineering_lab_42.py"


def _write_colcon_summary(output_root: Path, content: str = "Summary: 42 tests, 0 errors, 0 failures, 0 skipped\n") -> Path:
    path = output_root / "logs" / "engineering_40_colcon_test.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path

_ANALYZE_SPEC = importlib.util.spec_from_file_location("analyze_engineering_42_logs", ANALYZE_SCRIPT)
assert _ANALYZE_SPEC and _ANALYZE_SPEC.loader
_ANALYZE_MODULE = importlib.util.module_from_spec(_ANALYZE_SPEC)
_ANALYZE_SPEC.loader.exec_module(_ANALYZE_MODULE)
REQUIRED_FIELDS = _ANALYZE_MODULE.REQUIRED_FIELDS


def _write_temp_log(path: Path, entries: list[dict]) -> None:
    """写入临时 JSON lines 日志。"""
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _make_valid_entry(timestamp_ns: int) -> dict:
    """构造符合共享日志字段契约的有效条目。"""
    return {
        "timestamp_ns": timestamp_ns,
        "episode_id": 0,
        "git_commit": "abc1234",
        "pitch_rad": 0.1,
        "pitch_rate_rad_s": 0.0,
        "raw_torque_common_nm": 0.3,
        "clamped_torque_common_nm": 0.3,
        "safety_flag": 0,
        "loop_cycle_ms": 10.0,
    }


def _run_analyze(log_path: Path, output_root: Path) -> subprocess.CompletedProcess:
    """以子进程方式运行分析脚本，便于校验退出码与 stderr。"""
    return subprocess.run(
        [
            sys.executable, str(ANALYZE_SCRIPT),
            "--log-path", str(log_path),
            "--output-root", str(output_root),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def test_normal_log_generates_plots(tmp_path):
    """正常日志应生成两张图表，且退出码 0。"""
    entries = [_make_valid_entry(1_000_000_000 + i * 10_000_000) for i in range(20)]
    log_path = tmp_path / "normal.jsonl"
    _write_temp_log(log_path, entries)

    proc = _run_analyze(log_path, tmp_path / "outputs")

    assert proc.returncode == 0, proc.stderr
    hist = tmp_path / "outputs" / "plots" / "engineering_42_latency_histogram.png"
    ts = tmp_path / "outputs" / "plots" / "engineering_42_state_torque_timeseries.png"
    assert hist.exists(), f"周期延迟直方图未生成：{hist}"
    assert ts.exists(), f"状态-力矩时间序列图未生成：{ts}"
    # 周期差值（10_000_000 ns = 10 ms）应反映在 stdout
    assert "10.0000 ms" in proc.stdout or "10.00" in proc.stdout


def test_missing_timestamp_rejected(tmp_path):
    """缺失 timestamp_ns 的日志应被拒绝（退出码 1），不生成图表。"""
    entry = _make_valid_entry(1_000_000_000)
    del entry["timestamp_ns"]
    log_path = tmp_path / "missing_ts.jsonl"
    _write_temp_log(log_path, [entry])

    proc = _run_analyze(log_path, tmp_path / "outputs")

    assert proc.returncode == 1
    assert "第 1 行" in proc.stderr
    assert "缺少字段 timestamp_ns" in proc.stderr
    # 失效场景下不应生成任何图表
    plots_dir = tmp_path / "outputs" / "plots"
    assert not plots_dir.exists() or not list(plots_dir.glob("*.png"))


def test_missing_other_field_rejected(tmp_path):
    """缺失非 timestamp_ns 字段也应被拒绝。"""
    entry = _make_valid_entry(1_000_000_000)
    del entry["clamped_torque_common_nm"]
    log_path = tmp_path / "missing_field.jsonl"
    _write_temp_log(log_path, [entry])

    proc = _run_analyze(log_path, tmp_path / "outputs")

    assert proc.returncode == 1
    assert "缺少字段 clamped_torque_common_nm" in proc.stderr


def test_out_of_order_timestamp_rejected(tmp_path):
    """乱序时间戳应被拒绝（退出码 1）。"""
    entries = [
        _make_valid_entry(1_000_000_000),
        _make_valid_entry(999_000_000),  # 倒退 1 ms
    ]
    log_path = tmp_path / "out_of_order.jsonl"
    _write_temp_log(log_path, entries)

    proc = _run_analyze(log_path, tmp_path / "outputs")

    assert proc.returncode == 1
    assert "第 2 行" in proc.stderr
    assert "时间戳乱序" in proc.stderr
    assert "prev=1000000000" in proc.stderr
    assert "curr=999000000" in proc.stderr


def test_invalid_json_rejected(tmp_path):
    """JSON 解析失败的行应被拒绝。"""
    log_path = tmp_path / "bad.jsonl"
    log_path.write_text("{not valid json}\n", encoding="utf-8")

    proc = _run_analyze(log_path, tmp_path / "outputs")

    assert proc.returncode == 1
    assert "第 1 行" in proc.stderr
    assert "JSON 解析失败" in proc.stderr


def test_equal_timestamp_allowed(tmp_path):
    """相等时间戳（非严格递减）应被接受。"""
    entries = [
        _make_valid_entry(1_000_000_000),
        _make_valid_entry(1_000_000_000),  # 相等，不视为乱序
        _make_valid_entry(1_000_000_000 + 10_000_000),
    ]
    log_path = tmp_path / "equal_ts.jsonl"
    _write_temp_log(log_path, entries)

    proc = _run_analyze(log_path, tmp_path / "outputs")

    assert proc.returncode == 0, proc.stderr


def test_metrics_out_payload(tmp_path):
    """--metrics-out 应写出包含 metrics 与 plots 的 JSON 契约。"""
    entries = [_make_valid_entry(1_000_000_000 + i * 10_000_000) for i in range(5)]
    log_path = tmp_path / "normal.jsonl"
    _write_temp_log(log_path, entries)
    metrics_path = tmp_path / "metrics.json"

    proc = subprocess.run(
        [
            sys.executable, str(ANALYZE_SCRIPT),
            "--log-path", str(log_path),
            "--output-root", str(tmp_path / "outputs"),
            "--metrics-out", str(metrics_path),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    assert metrics_path.exists()
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert payload["entry_count"] == 5
    assert payload["git_commit"] == "abc1234"
    assert "mean_cycle_ms" in payload["metrics"]
    assert REQUIRED_FIELDS is engineering_contract.REQUIRED_LOG_FIELDS
    assert payload["metrics"]["log_field_count"] == len(REQUIRED_FIELDS)
    assert len(payload["plots"]) == 2


def test_capstone_log_contract_accepts_engineering_result_with_perf_trace(tmp_path):
    """分析产物字段数应满足第45章快速日志契约。"""
    entries = [_make_valid_entry(1_000_000_000 + i * 10_000_000) for i in range(10)]
    log_path = tmp_path / "normal.jsonl"
    _write_temp_log(log_path, entries)
    output_root = tmp_path / "outputs"
    _write_colcon_summary(output_root)
    perf_trace = tmp_path / "perf_trace.txt"
    perf_trace.write_text("trace\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--log-path", str(log_path),
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
            "--perf-trace", str(perf_trace),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    contract = _validate_log_contract(output_root)
    assert contract["passed"] is True


def test_orchestrator_writes_result_contract(tmp_path):
    """编排入口应分析日志并写出结果契约与 portfolio。"""
    entries = [_make_valid_entry(1_000_000_000 + i * 10_000_000) for i in range(10)]
    log_path = tmp_path / "normal.jsonl"
    _write_temp_log(log_path, entries)
    output_root = tmp_path / "outputs"
    _write_colcon_summary(output_root)

    proc = subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--log-path", str(log_path),
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    result_path = output_root / "results" / "engineering_42.json"
    assert result_path.exists(), f"结果契约未生成：{result_path}"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["chapter_id"] == "42"
    assert data["source_state"]["source_digest"]
    assert data["passed"] is True
    assert data["metrics"]["log_field_count"] == len(
        engineering_contract.REQUIRED_LOG_FIELDS
    )
    assert data["seed"] == 0
    assert data["metrics"]["gtest_count"] == 42.0
    assert data["metrics"]["gtest_errors"] == 0.0
    assert data["metrics"]["gtest_failures"] == 0.0
    assert len(data["plots"]) == 2
    portfolio = output_root / "portfolio" / "42" / "engineering_42_report.md"
    assert portfolio.exists()
    assert _markdown_portfolio_is_substantive(portfolio.read_text(encoding="utf-8"))


def test_manifest_command_runs_with_required_log_path(tmp_path):
    """清单中的第 42 关命令应包含必需参数并能直接运行。"""
    entries = [_make_valid_entry(1_000_000_000 + i * 10_000_000) for i in range(10)]
    log_path = tmp_path / "normal.jsonl"
    _write_temp_log(log_path, entries)
    output_root = tmp_path / "outputs"
    _write_colcon_summary(output_root)

    manifest = load_course_manifest()
    chapter = next(item for item in manifest["chapters"] if item["id"] == "42")
    command = next(
        item for item in chapter["commands"]
        if item.startswith("python scripts/run_engineering_lab_42.py")
    )
    arguments = shlex.split(command)[1:]
    assert "--log-path" in arguments
    arguments[arguments.index("--log-path") + 1] = str(log_path)

    proc = subprocess.run(
        [
            sys.executable,
            *arguments,
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    assert (output_root / "results" / "engineering_42.json").is_file()


def test_orchestrator_rejects_malformed_colcon_summary(tmp_path):
    entries = [_make_valid_entry(1_000_000_000 + i * 10_000_000) for i in range(10)]
    log_path = tmp_path / "normal.jsonl"
    _write_temp_log(log_path, entries)
    output_root = tmp_path / "outputs"
    _write_colcon_summary(output_root, "all tests passed\n")

    proc = subprocess.run(
        [
            sys.executable,
            str(ORCHESTRATOR),
            "--log-path",
            str(log_path),
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
    data = json.loads(
        (output_root / "results" / "engineering_42.json").read_text(encoding="utf-8")
    )
    assert data["metrics"]["gtest_count"] == 0.0
    assert data["passed"] is False


def test_orchestrator_propagates_analyze_failure(tmp_path):
    """分析脚本失败时，编排入口应返回非零退出码且不写结果契约。"""
    entry = _make_valid_entry(1_000_000_000)
    del entry["timestamp_ns"]
    log_path = tmp_path / "missing_ts.jsonl"
    _write_temp_log(log_path, [entry])
    output_root = tmp_path / "outputs"

    proc = subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--log-path", str(log_path),
            "--output-root", str(output_root),
            "--source-root", str(tmp_path),
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )

    assert proc.returncode == 1
    result_path = output_root / "results" / "engineering_42.json"
    assert not result_path.exists()
