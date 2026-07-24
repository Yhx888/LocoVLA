#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 42 关日志分析工具：解析 JSON lines，生成可视化，拒绝失效字段。

统一日志契约字段由 ``upkie_mujoco_course.engineering.REQUIRED_LOG_FIELDS`` 定义。

失效字段拒绝机制：
    - 缺失任一字段：退出码 1，输出错误行号，不生成图表
    - 时间戳乱序（curr < prev）：退出码 1，输出乱序行号，不生成图表
    - JSON 解析失败：退出码 1，输出错误行号，不生成图表

用法：
    python scripts/tools/analyze_engineering_42_logs.py \
        --log-path <path> --output-root outputs [--metrics-out <path>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # 非交互后端，避免 Windows 显示问题
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from upkie_mujoco_course.engineering import REQUIRED_LOG_FIELDS

# 中文字体配置（Windows 上 Microsoft YaHei 通常可用）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Noto Sans SC", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False  # 负号正常显示

REQUIRED_FIELDS = REQUIRED_LOG_FIELDS

# 周期 deadline，沿用第 41 关 100 Hz 控制环的 12 ms 判定线
DEADLINE_MS = 12.0


def _get_git_commit() -> str:
    """获取当前 git commit hash，失败时返回 'unknown'。

    优先使用 subprocess 读取当前仓库的 HEAD，确保 metrics 文件记录的
    git_commit 反映分析时的代码版本，而非日志条目中可能过期的值。
    """
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


class LogParseError(ValueError):
    """日志解析失败异常，承载行号与原因。"""

    def __init__(self, line_no: int, reason: str) -> None:
        self.line_no = line_no
        self.reason = reason
        super().__init__(f"第 {line_no} 行：{reason}")


def parse_log_lines(path: Path) -> list[dict[str, Any]]:
    """解析 JSON lines，缺失字段或乱序时抛出 LogParseError。

    Args:
        path: JSON lines 文件路径，每行一个 JSON 对象。

    Returns:
        按行解析后的字典列表，字段完整且时间戳单调非降。
    """
    entries: list[dict[str, Any]] = []
    prev_ts: int | None = None
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                # 跳过空行，不计入行号诊断
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LogParseError(line_no, f"JSON 解析失败：{exc.msg}") from exc
            if not isinstance(entry, dict):
                raise LogParseError(line_no, "日志条目必须是 JSON 对象")
            # 字段完整性校验：缺失任一关键字段即拒绝，不静默补零
            missing = [k for k in REQUIRED_FIELDS if k not in entry]
            if missing:
                raise LogParseError(line_no, f"缺少字段 {'、'.join(missing)}")
            # timestamp_ns 类型校验（bool 是 int 子类，需排除）
            ts = entry["timestamp_ns"]
            if not isinstance(ts, int) or isinstance(ts, bool):
                raise LogParseError(
                    line_no,
                    f"timestamp_ns 必须是整数，实际类型为 {type(ts).__name__}",
                )
            # 单调性校验：curr 严格小于 prev 视为乱序
            if prev_ts is not None and ts < prev_ts:
                raise LogParseError(
                    line_no, f"时间戳乱序（prev={prev_ts}, curr={ts}）"
                )
            prev_ts = ts
            entries.append(entry)
    if not entries:
        raise LogParseError(0, "日志为空或仅含空行")
    return entries


def plot_latency_histogram(
    entries: list[dict[str, Any]], output_path: Path
) -> dict[str, float]:
    """生成周期延迟直方图，返回统计 metrics。

    周期定义为相邻 timestamp_ns 之差（ns → ms）。单条日志无法计算周期时，
    视为 0 样本并跳过绘图，但仍返回空 metrics 供下游处理。
    """
    timestamps = [int(e["timestamp_ns"]) for e in entries]
    diffs_ms = [
        (timestamps[i + 1] - timestamps[i]) / 1e6
        for i in range(len(timestamps) - 1)
    ]
    if not diffs_ms:
        # 单条日志：无法计算周期，写空图保留契约可读性
        diffs_ms = [0.0]
    mean_ms = sum(diffs_ms) / len(diffs_ms)
    sorted_diffs = sorted(diffs_ms)
    p99_idx = max(0, int(0.99 * (len(sorted_diffs) - 1)))
    p99_ms = sorted_diffs[p99_idx]
    miss_count = sum(1 for d in diffs_ms if d > DEADLINE_MS)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(
        diffs_ms,
        bins=50,
        color="#4c72b0",
        edgecolor="#2c3e50",
        linewidth=0.3,
        alpha=0.85,
    )
    ax.axvline(
        mean_ms, color="#2ca02c", linewidth=1.4, linestyle="-",
        label=f"均值 {mean_ms:.3f} ms",
    )
    ax.axvline(
        p99_ms, color="#d62728", linewidth=1.2, linestyle="--",
        label=f"P99 {p99_ms:.3f} ms",
    )
    ax.axvline(
        DEADLINE_MS, color="#ff7f0e", linewidth=1.0, linestyle=":",
        label=f"deadline {DEADLINE_MS:.1f} ms（miss={miss_count}）",
    )
    ax.set_xlabel("周期 (ms)")
    ax.set_ylabel("频次")
    ax.set_title(f"第 42 关 周期延迟分布（样本数 {len(diffs_ms)}）")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return {
        "log_field_count": len(REQUIRED_FIELDS),
        "sample_count": float(len(diffs_ms)),
        "mean_cycle_ms": float(mean_ms),
        "p99_cycle_ms": float(p99_ms),
        "max_cycle_ms": float(max(diffs_ms)),
        "min_cycle_ms": float(min(diffs_ms)),
        "deadline_miss_count": float(miss_count),
        "deadline_miss_rate": float(miss_count / len(diffs_ms) if diffs_ms else 0.0),
    }


def plot_state_torque_timeseries(
    entries: list[dict[str, Any]], output_path: Path
) -> None:
    """生成状态-力矩时间序列（双 y 轴）。

    左轴：pitch_rad、pitch_rate_rad_s
    右轴：raw_torque_common_nm、clamped_torque_common_nm
    safety_flag 变化点以橙色虚线标注。
    """
    base_ts = int(entries[0]["timestamp_ns"])
    t_s = [(int(e["timestamp_ns"]) - base_ts) / 1e9 for e in entries]
    pitch = [float(e["pitch_rad"]) for e in entries]
    pitch_rate = [float(e["pitch_rate_rad_s"]) for e in entries]
    raw_torque = [float(e["raw_torque_common_nm"]) for e in entries]
    clamped_torque = [float(e["clamped_torque_common_nm"]) for e in entries]
    safety_flag = [int(e["safety_flag"]) for e in entries]

    fig, ax_left = plt.subplots(figsize=(12, 6))
    ax_right = ax_left.twinx()

    # 左轴：状态量
    ax_left.plot(t_s, pitch, color="#1f77b4", linewidth=1.0, label="pitch (rad)")
    ax_left.plot(
        t_s, pitch_rate, color="#17becf", linewidth=1.0, label="pitch_rate (rad/s)"
    )
    ax_left.set_xlabel("时间 (s)")
    ax_left.set_ylabel("状态 (rad, rad/s)", color="#1f77b4")
    ax_left.tick_params(axis="y", labelcolor="#1f77b4")
    ax_left.grid(True, alpha=0.3)

    # 右轴：力矩
    ax_right.plot(
        t_s, raw_torque, color="#d62728", linewidth=1.0, linestyle="--",
        label="raw_torque (N·m)",
    )
    ax_right.plot(
        t_s, clamped_torque, color="#9467bd", linewidth=1.0,
        label="clamped_torque (N·m)",
    )
    ax_right.set_ylabel("力矩 (N·m)", color="#d62728")
    ax_right.tick_params(axis="y", labelcolor="#d62728")

    # safety_flag 变化点：在发生变化的位置画橙色点划线
    for i in range(1, len(safety_flag)):
        if safety_flag[i] != safety_flag[i - 1]:
            ax_left.axvline(
                t_s[i], color="#ff7f0e", linewidth=0.8, linestyle=":",
                label="safety_flag 切换" if i == 1 else None,
            )

    # 合并双轴图例
    lines_left, labels_left = ax_left.get_legend_handles_labels()
    lines_right, labels_right = ax_right.get_legend_handles_labels()
    ax_left.legend(
        lines_left + lines_right, labels_left + labels_right,
        loc="upper right", fontsize=9,
    )

    ax_left.set_title(f"第 42 关 状态-力矩时间序列（共 {len(entries)} 条日志）")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    """主入口，返回 0=成功，1=失效。"""
    parser = argparse.ArgumentParser(
        description="第 42 关日志分析：JSON lines 解析 + 可视化 + 失效字段拒绝",
    )
    parser.add_argument("--log-path", required=True, help="JSON lines 日志文件路径")
    parser.add_argument(
        "--output-root", default="outputs",
        help="输出根目录（默认 outputs，图表写入 <root>/plots/）",
    )
    parser.add_argument(
        "--metrics-out", default=None,
        help="可选：将 metrics 与图表路径写入 JSON 文件，供编排入口读取",
    )
    parser.add_argument(
        "--warmup-skip", type=int, default=0,
        help="跳过前 N 行预热数据（用于剔除控制节点启动瞬态，默认 0 不跳过）",
    )
    args = parser.parse_args()

    log_path = Path(args.log_path).resolve()
    if not log_path.exists():
        print(f"[ERROR] 日志文件不存在：{log_path}", file=sys.stderr)
        return 1

    try:
        entries = parse_log_lines(log_path)
    except LogParseError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    # 跳过预热数据：剔除控制节点启动/IMU 发布器进程切换瞬态
    # 字段完整性校验仍在全量日志上进行（parse_log_lines 已完成），
    # 此处仅对统计与绘图样本做截断，保留契约的失效拒绝语义。
    if args.warmup_skip > 0 and len(entries) > args.warmup_skip:
        entries = entries[args.warmup_skip:]
        print(f"[INFO] 跳过前 {args.warmup_skip} 行预热数据，剩余 {len(entries)} 行")

    output_root = Path(args.output_root).resolve()
    plots_dir = output_root / "plots"
    hist_path = plots_dir / "engineering_42_latency_histogram.png"
    ts_path = plots_dir / "engineering_42_state_torque_timeseries.png"

    metrics = plot_latency_histogram(entries, hist_path)
    plot_state_torque_timeseries(entries, ts_path)

    print(f"[OK] 解析日志 {len(entries)} 条")
    print(f"[OK] 周期延迟直方图：{hist_path}")
    print(f"[OK] 状态-力矩时间序列：{ts_path}")
    print(f"  样本数：{int(metrics['sample_count'])}")
    print(f"  均值：{metrics['mean_cycle_ms']:.4f} ms")
    print(f"  P99：{metrics['p99_cycle_ms']:.4f} ms")
    print(f"  max：{metrics['max_cycle_ms']:.4f} ms")
    print(
        f"  deadline miss：{int(metrics['deadline_miss_count'])}/"
        f"{int(metrics['sample_count'])} ({metrics['deadline_miss_rate'] * 100:.2f}%)"
    )

    if args.metrics_out:
        metrics_path = Path(args.metrics_out).resolve()
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "entry_count": len(entries),
            "git_commit": entries[0].get("git_commit", "unknown"),
            "analysis_git_commit": _get_git_commit(),
            "episode_id": entries[0].get("episode_id", 0),
            "log_path": str(log_path),
            "metrics": metrics,
            "plots": [str(hist_path), str(ts_path)],
        }
        metrics_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OK] metrics 已写入：{metrics_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
