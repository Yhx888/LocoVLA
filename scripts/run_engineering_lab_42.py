#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 42 关实验编排入口：分析日志→写结果契约。

调用 ``scripts/tools/analyze_engineering_42_logs.py`` 解析 JSON lines
统一日志、生成图表与 metrics，再合并 C++ 端 GoogleTest 统计与性能 trace
信息，最终写出可由仪表盘读取的结果契约（``outputs/results/engineering_42.json``）
和一份 Markdown portfolio 报告。

用法：
    python scripts/run_engineering_lab_42.py \
        --log-path <path> [--output-root outputs] \
        [--colcon-test-log <path>] [--perf-trace <path>] [--seed 0]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.results import write_experiment_result  # noqa: E402
from upkie_mujoco_course.engineering.lab import read_colcon_test_summary  # noqa: E402

ANALYZE_SCRIPT = ROOT / "scripts" / "tools" / "analyze_engineering_42_logs.py"


def _resolve_output_root(value: str, source_root: Path) -> Path:
    """将输出根目录解析为绝对路径，相对路径相对于源码根。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (source_root / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 42 关日志分析实验")
    parser.add_argument("--log-path", required=True, help="JSON lines 日志路径")
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="用于源码摘要和相对证据路径的项目根目录",
    )
    parser.add_argument("--colcon-test-log", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--perf-trace", default=None,
        help="可选：性能 trace 文件路径（perf/telemetry）",
    )
    args = parser.parse_args()

    log_path = Path(args.log_path).resolve()
    if not log_path.exists():
        print(f"[FAIL] 日志文件不存在：{log_path}", file=sys.stderr)
        return 1

    source_root = Path(args.source_root).resolve()
    output_root = _resolve_output_root(args.output_root, source_root)
    colcon_path = (
        Path(args.colcon_test_log).resolve()
        if args.colcon_test_log
        else output_root / "logs" / "engineering_40_colcon_test.log"
    )
    gtest_count, gtest_errors, gtest_failures, colcon_valid = read_colcon_test_summary(
        colcon_path
    )
    metrics_path = output_root / "logs" / "engineering_42_metrics.json"

    # 调用分析脚本（在仓库根目录执行，便于相对路径解析）
    cmd = [
        sys.executable,
        str(ANALYZE_SCRIPT),
        "--log-path", str(log_path),
        "--output-root", str(output_root),
        "--metrics-out", str(metrics_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        print(
            f"[FAIL] 第 42 关日志分析失败（退出码 {proc.returncode}）",
            file=sys.stderr,
        )
        return proc.returncode

    # 解析分析脚本产出的 metrics 契约
    if not metrics_path.exists():
        print(f"[FAIL] metrics 文件未生成：{metrics_path}", file=sys.stderr)
        return 1
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics: dict[str, float] = dict(payload["metrics"])
    plots: list[str] = list(payload["plots"])
    log_path_str: str = payload["log_path"]
    git_commit: str = payload.get("analysis_git_commit") or payload.get("git_commit", "unknown")

    # 合并 C++ 端测试与性能 trace 信息
    metrics["gtest_count"] = float(gtest_count)
    metrics["gtest_errors"] = float(gtest_errors)
    metrics["gtest_failures"] = float(gtest_failures)
    metrics["colcon_summary_valid"] = float(colcon_valid)
    metrics["perf_trace_present"] = 1.0 if args.perf_trace else 0.0

    logs: list[str] = [log_path_str]
    if colcon_path.is_file() and colcon_path.stat().st_size > 0:
        logs.append(str(colcon_path))
    if args.perf_trace:
        logs.append(str(Path(args.perf_trace).resolve()))

    # 写结果契约：第 42 关的通过条件是 C++ 测试零失败 + 日志零 deadline miss
    result_path = output_root / "results" / "engineering_42.json"
    write_experiment_result(
        result_path,
        chapter_id="42",
        seed=args.seed,
        config={
            "log_path": log_path_str,
            "colcon_test_log": str(colcon_path),
            "perf_trace": args.perf_trace or "",
        },
        metrics=metrics,
        pass_conditions={
            "gtest_count": {"operator": ">=", "value": 1},
            "gtest_errors": {"operator": "==", "value": 0},
            "gtest_failures": {"operator": "==", "value": 0},
            "colcon_summary_valid": {"operator": "==", "value": 1},
            "deadline_miss_count": {"operator": "<=", "value": 0},
        },
        plots=plots,
        logs=logs,
        git_commit=git_commit,
        root=source_root,
    )

    # 写 portfolio 报告
    portfolio = output_root / "portfolio" / "42" / "engineering_42_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        "# 第 42 关统一日志契约报告\n\n"
        "## 指标\n\n"
        f"- 日志条目数：`{payload['entry_count']}`\n"
        f"- 平均周期：`{metrics['mean_cycle_ms']:.3f} ms`\n"
        f"- P99 周期：`{metrics['p99_cycle_ms']:.3f} ms`\n"
        f"- 最大周期：`{metrics['max_cycle_ms']:.3f} ms`\n"
        f"- deadline miss：`{int(metrics['deadline_miss_count'])}/"
        f"{int(metrics['sample_count'])}`\n"
        f"- colcon 测试：`{gtest_count}`，错误：`{gtest_errors}`，失败：`{gtest_failures}`\n"
        f"- 性能 trace：`{args.perf_trace or '未提供'}`\n"
        f"- 结果契约：`{result_path}`\n",
        encoding="utf-8",
    )

    print(f"[OK] 第 42 关结果契约：{result_path}")
    print(f"[OK] portfolio：{portfolio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
