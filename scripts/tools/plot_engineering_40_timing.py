#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 40 关证据采集：生成频率/抖动图。

读取 outputs/logs/engineering_40_timing.json，生成两张子图：
1. 周期时序图（每个 tick 的周期，标称 10ms 红线 + 12ms deadline 红虚线）
2. 周期分布直方图（频率分布）

输出：outputs/plots/engineering_40.png
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 非交互后端，避免 Windows 显示问题
import matplotlib.pyplot as plt

# 中文字体配置（Windows 上 Microsoft YaHei 通常可用）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False  # 负号正常显示


def main() -> int:
    parser = argparse.ArgumentParser(description="绘制第 40 关 ROS2 控制周期证据")
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    requested_root = Path(args.output_root)
    output_root = (
        requested_root.resolve()
        if requested_root.is_absolute()
        else (repo_root / requested_root).resolve()
    )
    timing_path = output_root / "logs" / "engineering_40_timing.json"
    output_path = output_root / "plots" / "engineering_40.png"

    with open(timing_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = data["statistics"]
    periods = data["periods_ms"]
    offsets = data["offsets_ms"]
    if not periods or not offsets:
        raise ValueError("timing 数据必须包含非空 periods_ms 和 offsets_ms")
    target_ms = data["timer_period_ms_target"]
    deadline_ms = data["deadline_ms"]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"hspace": 0.35})

    # ---- 子图 1：周期时序图 ----
    ax1 = axes[0]
    # x 轴用样本序号（第几个周期）
    x = list(range(1, len(periods) + 1))
    ax1.plot(x, periods, color="#1f77b4", linewidth=0.6, label="实测周期")
    ax1.axhline(target_ms, color="#2ca02c", linewidth=1.2, linestyle="-",
                label=f"标称周期 {target_ms:.1f} ms")
    ax1.axhline(deadline_ms, color="#d62728", linewidth=1.0, linestyle="--",
                label=f"deadline {deadline_ms:.1f} ms")
    ax1.set_xlabel("周期序号")
    ax1.set_ylabel("周期 (ms)")
    ax1.set_title(
        f"控制节点 wall_timer 周期时序（{len(periods)} 个样本，"
        f"mean={stats['mean_period_ms']:.3f} ms，"
        f"P99={stats['p99_period_ms']:.3f} ms，"
        f"deadline miss={stats['deadline_miss_count']}）"
    )
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3)
    # y 轴范围给足余量，突出抖动
    y_min = min(min(periods), target_ms) - 0.5
    y_max = max(max(periods), deadline_ms) + 0.5
    ax1.set_ylim(y_min, y_max)

    # ---- 子图 2：周期分布直方图 ----
    ax2 = axes[1]
    # bin 宽度 0.05 ms
    bin_width = 0.05
    bin_start = float(min(periods))
    bin_end = float(max(periods))
    bins = []
    b = bin_start
    while b <= bin_end + bin_width:
        bins.append(b)
        b += bin_width
    ax2.hist(periods, bins=bins, color="#4c72b0", edgecolor="#2c3e50",
             linewidth=0.3, alpha=0.85)
    ax2.axvline(stats["mean_period_ms"], color="#2ca02c", linewidth=1.4,
                linestyle="-", label=f"均值 {stats['mean_period_ms']:.3f} ms")
    ax2.axvline(stats["p50_period_ms"], color="#ff7f0e", linewidth=1.2,
                linestyle=":", label=f"P50 {stats['p50_period_ms']:.3f} ms")
    ax2.axvline(stats["p99_period_ms"], color="#d62728", linewidth=1.2,
                linestyle="--", label=f"P99 {stats['p99_period_ms']:.3f} ms")
    ax2.set_xlabel("周期 (ms)")
    ax2.set_ylabel("样本计数")
    ax2.set_title(
        f"wall_timer 周期分布（min={stats['min_period_ms']:.3f} ms，"
        f"max={stats['max_period_ms']:.3f} ms，"
        f"bin 宽 {bin_width} ms）"
    )
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.suptitle(
        f"第 40 关：控制节点 100 Hz wall_timer 频率/抖动证据\n"
        f"采集时长 {offsets[-1]/1000:.2f} s，样本数 {len(periods)+1}，"
        f"deadline miss rate {stats['deadline_miss_rate']*100:.2f}%",
        fontsize=12,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"频率图已保存到 {output_path}")
    print(f"  样本数: {len(periods)+1}")
    print(f"  平均周期: {stats['mean_period_ms']:.4f} ms")
    print(f"  P50: {stats['p50_period_ms']:.4f} ms")
    print(f"  P99: {stats['p99_period_ms']:.4f} ms")
    print(f"  min: {stats['min_period_ms']:.4f} ms")
    print(f"  max: {stats['max_period_ms']:.4f} ms")
    print(f"  deadline miss: {stats['deadline_miss_count']}/{len(periods)} "
          f"({stats['deadline_miss_rate']*100:.2f}%)")
    return 0


if __name__ == "__main__":
    main()
