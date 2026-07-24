from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.results import write_experiment_result


def load_trace(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    required = {"period_ns", "compute_ns", "deadline_miss", "balance_nm", "left_nm", "right_nm"}
    if len(rows) != 6000 or not rows or not required <= set(rows[0]):
        raise ValueError("实时日志必须包含 6000 行及完整周期、计算、deadline 和力矩字段")
    return {key: np.asarray([float(row[key]) for row in rows]) for key in required}


def main() -> None:
    parser = argparse.ArgumentParser(description="分析第 41 关 60 秒实时控制日志")
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--source-root", default=str(ROOT))
    parser.add_argument("--baseline")
    parser.add_argument("--improved")
    args = parser.parse_args()
    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (source_root / output_root).resolve()
    baseline_path = Path(args.baseline) if args.baseline else output_root / "logs" / "engineering_41_realtime_raw.csv"
    improved_path = Path(args.improved) if args.improved else output_root / "logs" / "engineering_41_high_resolution_raw.csv"
    if not baseline_path.is_absolute():
        baseline_path = (source_root / baseline_path).resolve()
    if not improved_path.is_absolute():
        improved_path = (source_root / improved_path).resolve()
    baseline = load_trace(baseline_path)
    improved = load_trace(improved_path)
    baseline_period = baseline["period_ns"][1:] / 1e6
    improved_period = improved["period_ns"][1:] / 1e6
    metrics = {
        "sample_count": float(len(improved["period_ns"])),
        "baseline_p99_ms": float(np.percentile(baseline_period, 99)),
        "improved_p99_ms": float(np.percentile(improved_period, 99)),
        "improved_max_ms": float(np.max(improved_period)),
        "baseline_deadline_miss_count": float(np.sum(baseline["deadline_miss"])),
        "improved_deadline_miss_count": float(np.sum(improved["deadline_miss"])),
        "compute_p99_ms": float(np.percentile(improved["compute_ns"] / 1e6, 99)),
    }
    plot = output_root / "plots" / "engineering_41.png"
    plot.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Noto Sans SC", "SimHei"]
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].hist(baseline_period, bins=50, alpha=.65, label="默认计时器")
    axes[0].hist(improved_period, bins=50, alpha=.65, label="1 ms 计时器")
    axes[0].axvline(12, color="#d36b27", linestyle="--", label="P99 门槛")
    axes[0].set(xlabel="周期 [ms]", title="60 秒周期分布")
    axes[0].legend(); axes[0].grid(alpha=.2)
    axes[1].plot(improved["balance_nm"][:300], label="公共力矩")
    axes[1].plot(improved["left_nm"][:300], label="左轮")
    axes[1].plot(improved["right_nm"][:300], label="右轮")
    axes[1].set(xlabel="tick", ylabel="力矩 [N*m]", title="实时控制输出")
    axes[1].legend(); axes[1].grid(alpha=.2)
    figure.tight_layout(); figure.savefig(plot, dpi=150); plt.close(figure)
    log = output_root / "logs" / "engineering_41.json"
    log.write_text(json.dumps({"metrics": metrics, "baseline": str(baseline_path), "improved": str(improved_path)}, ensure_ascii=False, indent=2), encoding="utf-8")
    result = write_experiment_result(output_root / "results" / "engineering_41.json", chapter_id="41", seed=41, config={"duration_s": 60, "period_ms": 10, "timer_resolution_ms": 1}, metrics=metrics, pass_conditions={"sample_count": {"operator": "==", "value": 6000}, "improved_p99_ms": {"operator": "<", "value": 12}, "improved_max_ms": {"operator": "<", "value": 20}, "improved_deadline_miss_count": {"operator": "==", "value": 0}}, plots=[str(plot)], logs=[str(log), str(baseline_path), str(improved_path)], root=source_root)
    portfolio = output_root / "portfolio" / "41" / "realtime_latency_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(f"# 第 41 关实时循环报告\n\n## 指标\n\n- 默认计时器 P99：`{metrics['baseline_p99_ms']:.3f} ms`，miss：`{metrics['baseline_deadline_miss_count']:.0f}`\n- 1 ms 计时器 P99：`{metrics['improved_p99_ms']:.3f} ms`，最大：`{metrics['improved_max_ms']:.3f} ms`，miss：`{metrics['improved_deadline_miss_count']:.0f}`\n- 此结果是 Windows 开发基线，不声明硬实时保证。\n", encoding="utf-8")
    print(json.dumps(json.loads(result.read_text(encoding="utf-8"))["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
