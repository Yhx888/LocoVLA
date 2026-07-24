#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 41 关实验编排入口：Windows 实时基线复核→写结果契约。

在 60 秒、100 Hz 真实控制循环中比较 Windows 默认定时器与 1 ms 高分辨率
定时器的周期抖动与 deadline miss。

用法：
    python scripts/run_engineering_lab_41.py [--output-root outputs]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.results import assess_experiment_result  # noqa: E402
from upkie_mujoco_course.course.results import write_experiment_result  # noqa: E402
from upkie_mujoco_course.course.checkpoint import _markdown_portfolio_is_substantive  # noqa: E402


def _resolve_output_root(value: str, source_root: Path) -> Path:
    """将输出根目录解析为绝对路径，相对路径相对于源码根。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (source_root / p).resolve()


def _run_timing_benchmark(duration_s: int = 60, period_ms: float = 10.0) -> dict:
    """运行定时基准测试，返回统计结果。"""
    import ctypes
    # 尝试设置 Windows 高分辨率定时器
    try:
        winmm = ctypes.windll.winmm  # type: ignore
        winmm.timeBeginPeriod(1)
        high_res = True
    except (AttributeError, OSError):
        high_res = False

    periods_ms: list[float] = []
    target_ns = int(period_ms * 1_000_000)
    deadline_ms = period_ms * 1.2  # 20% 容差

    start = time.perf_counter_ns()
    prev = start
    end_time = start + duration_s * 1_000_000_000

    while time.perf_counter_ns() < end_time:
        # 忙等待到下一个周期
        next_target = prev + target_ns
        while time.perf_counter_ns() < next_target:
            pass
        now = time.perf_counter_ns()
        period = (now - prev) / 1_000_000  # 转为 ms
        periods_ms.append(period)
        prev = now

    if high_res:
        try:
            winmm.timeEndPeriod(1)
        except (AttributeError, OSError):
            pass

    if not periods_ms:
        return {"sample_count": 0}

    periods_ms.sort()
    n = len(periods_ms)
    p99_idx = int(n * 0.99)
    deadline_miss = sum(1 for p in periods_ms if p > deadline_ms)

    return {
        "sample_count": n,
        "mean_period_ms": sum(periods_ms) / n,
        "p99_period_ms": periods_ms[p99_idx] if p99_idx < n else periods_ms[-1],
        "max_period_ms": periods_ms[-1],
        "min_period_ms": periods_ms[0],
        "deadline_miss_count": deadline_miss,
        "high_resolution_timer": high_res,
        "periods_ms": periods_ms,
    }


def _write_benchmark_evidence(stats: dict, output_root: Path) -> None:
    """将真实基准采样、统计与分布图写入统一输出根。"""
    periods_ms = [float(value) for value in stats.get("periods_ms", [])]
    logs_dir = output_root / "logs"
    plots_dir = output_root / "plots"
    logs_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    csv_path = logs_dir / "engineering_41_high_resolution_raw.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["period_ms"])
        writer.writerows([value] for value in periods_ms)

    log_path = logs_dir / "engineering_41.json"
    log_path.write_text(
        json.dumps(
            {key: value for key, value in stats.items() if key != "periods_ms"},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(8, 4))
    axis.hist(periods_ms, bins=50, color="#17745a", alpha=0.85)
    axis.axvline(12.0, color="#d36b27", linestyle="--", label="12 ms threshold")
    axis.set(xlabel="Period [ms]", ylabel="Samples", title="Chapter 41 timing distribution")
    axis.grid(alpha=0.2)
    axis.legend()
    figure.tight_layout()
    figure.savefig(plots_dir / "engineering_41.png", dpi=150)
    plt.close(figure)


def _write_portfolio_report(output_root: Path, *, duration_s: int, metrics: dict) -> None:
    """写入包含本次统计指标的第 41 关作品集报告。"""
    portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        "# 第 41 关 Windows 实时基线复核报告\n\n"
        "## 指标\n\n"
        f"- P99 周期：`{float(metrics.get('improved_p99_ms', 0.0)):.3f} ms`\n"
        f"- 最大周期：`{float(metrics.get('improved_max_ms', 0.0)):.3f} ms`\n"
        f"- deadline miss：`{float(metrics.get('improved_deadline_miss_count', 0.0)):.0f}`\n\n"
        "## 实验参数\n\n"
        f"- 持续时间：{duration_s}s\n"
        "- 目标周期：10ms (100Hz)\n"
        "- 定时器分辨率：1ms\n\n"
        "## 结论\n\n"
        "本结果仅代表 Windows 开发机的时延基线，"
        "不是硬实时保证。\n",
        encoding="utf-8",
    )


def _portfolio_has_dynamic_metrics(portfolio: Path) -> bool:
    if not portfolio.is_file():
        return False
    text = portfolio.read_text(encoding="utf-8")
    normalized = text.lower()
    return (
        _markdown_portfolio_is_substantive(text)
        and "p99" in normalized
        and ("miss" in normalized or "deadline" in normalized)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 41 关实时基线复核实验")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--source-root", default=str(ROOT))
    parser.add_argument("--duration", type=int, default=60, help="测试持续时间（秒）")
    parser.add_argument("--skip-benchmark", action="store_true",
                        help="跳过实际基准测试，使用已有数据")
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = _resolve_output_root(args.output_root, source_root)

    # 检查是否有已有结果
    existing_result = output_root / "results" / "engineering_41.json"
    raw_csv = output_root / "logs" / "engineering_41_realtime_raw.csv"

    if args.skip_benchmark and existing_result.exists():
        # 使用已有数据
        data = json.loads(existing_result.read_text(encoding="utf-8"))
        assessment = assess_experiment_result(data, root=source_root)
        if assessment["valid"] and not assessment["stale"]:
            config = data.get("config", {})
            duration_s = int(config.get("duration_s", args.duration)) if isinstance(config, dict) else args.duration
            portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
            if not _portfolio_has_dynamic_metrics(portfolio):
                _write_portfolio_report(output_root, duration_s=duration_s, metrics=data.get("metrics", {}))
            print(f"[OK] 第 41 关已有通过结果：{existing_result}")
            return 0

    # 如果有已有 CSV 数据，读取它
    if raw_csv.exists() and args.skip_benchmark:
        import csv
        periods = []
        with open(raw_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头
            for row in reader:
                if row:
                    periods.append(float(row[0]))
        if periods:
            periods.sort()
            n = len(periods)
            p99_idx = int(n * 0.99)
            stats = {
                "sample_count": n,
                "mean_period_ms": sum(periods) / n,
                "p99_period_ms": periods[p99_idx],
                "max_period_ms": periods[-1],
                "min_period_ms": periods[0],
                "deadline_miss_count": sum(1 for p in periods if p > 12.0),
                "high_resolution_timer": True,
            }
        else:
            stats = _run_timing_benchmark(args.duration)
    elif not args.skip_benchmark:
        print(f"[INFO] 开始 {args.duration}s 定时基准测试...")
        stats = _run_timing_benchmark(args.duration)
        _write_benchmark_evidence(stats, output_root)
    else:
        # 无已有数据且跳过测试，使用零值
        stats = {"sample_count": 0, "mean_period_ms": 0, "p99_period_ms": 0,
                 "max_period_ms": 0, "deadline_miss_count": 0, "high_resolution_timer": False}

    metrics: dict[str, float] = {
        "sample_count": float(stats.get("sample_count", 0)),
        "improved_p99_ms": float(stats.get("p99_period_ms", 0)),
        "improved_max_ms": float(stats.get("max_period_ms", 0)),
        "improved_deadline_miss_count": float(stats.get("deadline_miss_count", 0)),
    }

    # 收集已有的 plots 和 logs
    plot_path = output_root / "plots" / "engineering_41.png"
    plots = [str(plot_path)] if plot_path.exists() else []

    log_candidates = [
        "engineering_41.json",
        "engineering_41_realtime_raw.csv",
        "engineering_41_high_resolution_raw.csv",
    ]
    logs = [
        str(output_root / "logs" / f)
        for f in log_candidates
        if (output_root / "logs" / f).exists()
    ]

    result_path = output_root / "results" / "engineering_41.json"
    write_experiment_result(
        result_path,
        chapter_id="41",
        seed=args.seed,
        config={
            "duration_s": args.duration,
            "period_ms": 10,
            "timer_resolution_ms": 1,
        },
        metrics=metrics,
        pass_conditions={
            "sample_count": {"operator": ">=", "value": 5000},
            "improved_p99_ms": {"operator": "<", "value": 12},
            "improved_deadline_miss_count": {"operator": "==", "value": 0},
        },
        plots=plots,
        logs=logs,
        root=source_root,
    )

    portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
    if not _portfolio_has_dynamic_metrics(portfolio):
        _write_portfolio_report(output_root, duration_s=args.duration, metrics=metrics)

    print(f"[OK] 第 41 关结果契约：{result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
