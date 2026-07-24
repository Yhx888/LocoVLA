#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 43 关：真实 ROS2 故障注入可视化脚本。

读取 outputs/results/engineering_43_ros2_fault_injection.json，生成 3 张图：
  1. engineering_43_state_timeline.png  —— 状态时间线（x=时间s, y=状态0-4, 标注故障注入点）
  2. engineering_43_torque_gating.png  —— 力矩门控时间线（x=时间s, y=力矩N·m, 标注故障检测点）
  3. engineering_43_detection_latency.png —— 5 种故障检测延迟柱状图

Windows 端运行：
  .\\.venv\\Scripts\\python.exe scripts\\tools\\plot_engineering_43.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 非交互后端，适合脚本运行
import matplotlib.pyplot as plt

# 中文字体配置（Windows 端）
for font_name in ("Microsoft YaHei", "SimHei", "DejaVu Sans"):
    try:
        matplotlib.rcParams["font.sans-serif"] = [font_name]
        break
    except Exception:
        continue
matplotlib.rcParams["axes.unicode_minus"] = False  # 负号正常显示

# 状态名 -> 数值映射（与 C++ SafetyState 枚举一致）
STATE_TO_ID = {
    "BOOT": 0,
    "SELF_CHECK": 1,
    "DISARMED": 2,
    "ARMED": 3,
    "FAULT": 4,
}
ID_TO_STATE = {v: k for k, v in STATE_TO_ID.items()}

# 仓库根目录
ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "outputs" / "results" / "engineering_43_ros2_fault_injection.json"
OUT_DIR = ROOT / "outputs" / "plots"

# 故障名中文映射
FAULT_NAME_CN = {
    "imu_dropout": "IMU 断流\n300ms",
    "nan_injection": "NaN 注入",
    "timestamp_regression": "时间戳\n回退",
    "communication_lost": "通信中断\n250ms",
    "estop": "急停触发",
}

# 故障名英文映射（用于文件名）
FAULT_NAME_EN = {
    "imu_dropout": "imu_dropout",
    "nan_injection": "nan_injection",
    "timestamp_regression": "timestamp_regression",
    "communication_lost": "communication_lost",
    "estop": "estop",
}


def load_data(path: Path = INPUT_PATH) -> dict:
    """读取故障注入结果 JSON。"""
    if not path.exists():
        raise FileNotFoundError(f"未找到输入文件: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def plot_state_timeline(data: dict, out_path: Path) -> bool:
    """图 1：状态时间线（x=时间s, y=状态0-4, 标注故障注入点）。"""
    timeline = data.get("state_timeline", [])
    if not timeline:
        print("[WARN] state_timeline 为空，跳过状态时间线图")
        return False

    times = [item["t_s"] for item in timeline]
    state_ids = [STATE_TO_ID.get(item["state"], 0) for item in timeline]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.step(times, state_ids, where="post", color="#1f77b4", linewidth=1.5)
    ax.set_xlabel("时间 (s)", fontsize=12)
    ax.set_ylabel("安全状态", fontsize=12)
    ax.set_title("第 43 关：安全状态机时间线（真实 ROS2 故障注入）", fontsize=14)
    ax.set_yticks(list(ID_TO_STATE.keys()))
    ax.set_yticklabels([ID_TO_STATE[i] for i in sorted(ID_TO_STATE.keys())], fontsize=11)
    ax.grid(True, alpha=0.3, linestyle="--")

    # 标注故障注入点和检测点
    faults = data.get("faults", [])
    colors = ["#d62728", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b"]
    for i, fault in enumerate(faults):
        t_fault = fault.get("fault_injection_time_s")
        t_det = fault.get("fault_detected_time_s")
        name = fault.get("fault_name", f"fault_{i}")
        color = colors[i % len(colors)]
        # 故障注入点（虚线 + 三角）
        if t_fault is not None:
            ax.axvline(x=t_fault, color=color, linestyle="--", alpha=0.7, linewidth=1)
            ax.plot(t_fault, 4.3, marker="v", color=color, markersize=10, zorder=5)
            ax.annotate(
                f"{name}\n注入",
                xy=(t_fault, 4.3),
                xytext=(t_fault, 4.8),
                fontsize=8,
                color=color,
                ha="center",
                arrowprops=dict(arrowstyle="->", color=color, lw=0.8),
            )
        # 故障检测点（实线 + 圆点）
        if t_det is not None:
            ax.plot(t_det, 4.0, marker="o", color=color, markersize=8, zorder=5)

    ax.set_xlim(left=max(0, min(times) - 0.5), right=max(times) + 0.5)
    ax.set_ylim(-0.5, 5.2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 状态时间线图已生成: {out_path}")
    return True


def plot_torque_gating(data: dict, out_path: Path) -> bool:
    """图 2：力矩门控时间线（x=时间s, y=力矩N·m, 标注故障检测点）。"""
    timeline = data.get("torque_timeline", [])
    if not timeline:
        print("[WARN] torque_timeline 为空，跳过力矩门控图")
        return False

    times = [item["t_s"] for item in timeline]
    left = [item.get("torque_left", 0.0) for item in timeline]
    right = [item.get("torque_right", 0.0) for item in timeline]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(times, left, color="#1f77b4", linewidth=1.2, label="左轮力矩")
    ax.plot(times, right, color="#ff7f0e", linewidth=1.2, label="右轮力矩")
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5, alpha=0.5)

    ax.set_xlabel("时间 (s)", fontsize=12)
    ax.set_ylabel("力矩 (N·m)", fontsize=12)
    ax.set_title("第 43 关：力矩门控时间线（真实 ROS2 故障注入）", fontsize=14)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3, linestyle="--")

    # 标注故障检测点（力矩从非零变为零的瞬间）
    faults = data.get("faults", [])
    colors = ["#d62728", "#2ca02c", "#9467bd", "#8c564b", "#e377c2"]
    for i, fault in enumerate(faults):
        t_det = fault.get("fault_detected_time_s")
        t_brake = fault.get("brake_time_s")
        name = fault.get("fault_name", f"fault_{i}")
        color = colors[i % len(colors)]
        # 故障检测点
        if t_det is not None:
            ax.axvline(x=t_det, color=color, linestyle="--", alpha=0.6, linewidth=1)
            ax.annotate(
                f"{name}\n检测",
                xy=(t_det, 0.5),
                xytext=(t_det, 0.8),
                fontsize=8,
                color=color,
                ha="center",
                rotation=30,
                arrowprops=dict(arrowstyle="->", color=color, lw=0.8),
            )
        # 制动点（力矩归零）
        if t_brake is not None:
            ax.plot(t_brake, 0.0, marker="x", color=color, markersize=10, zorder=5)

    ax.set_xlim(left=max(0, min(times) - 0.5), right=max(times) + 0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 力矩门控图已生成: {out_path}")
    return True


def plot_detection_latency(data: dict, out_path: Path) -> bool:
    """图 3：5 种故障检测延迟柱状图。"""
    faults = data.get("faults", [])
    if not faults:
        print("[WARN] faults 为空，跳过检测延迟柱状图")
        return False

    names = [FAULT_NAME_CN.get(f.get("fault_name", ""), f.get("fault_name", "")) for f in faults]
    det_lats = [f.get("detection_latency_ms", 0) or 0 for f in faults]
    brake_lats = [f.get("brake_latency_ms", 0) or 0 for f in faults]

    x = list(range(len(faults)))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar([i - width / 2 for i in x], det_lats, width,
                   label="检测延迟 (ms)", color="#1f77b4", alpha=0.85)
    bars2 = ax.bar([i + width / 2 for i in x], brake_lats, width,
                   label="制动延迟 (ms)", color="#ff7f0e", alpha=0.85)

    # 在柱顶标注数值
    for bar in bars1:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("故障类型", fontsize=12)
    ax.set_ylabel("延迟 (ms)", fontsize=12)
    ax.set_title("第 43 关：5 种故障检测/制动延迟（真实 ROS2 测量）", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3, linestyle="--", axis="y")

    # 标注均值
    summary = data.get("summary", {})
    mean_det = summary.get("mean_detection_latency_ms")
    mean_brake = summary.get("mean_brake_latency_ms")
    if mean_det is not None:
        ax.axhline(y=mean_det, color="#1f77b4", linestyle=":", alpha=0.6, linewidth=1)
        ax.text(len(faults) - 0.5, mean_det + 3, f"均值={mean_det:.1f}ms",
                color="#1f77b4", fontsize=9, ha="right")
    if mean_brake is not None:
        ax.axhline(y=mean_brake, color="#ff7f0e", linestyle=":", alpha=0.6, linewidth=1)
        ax.text(len(faults) - 0.5, mean_brake + 3, f"均值={mean_brake:.1f}ms",
                color="#ff7f0e", fontsize=9, ha="right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 检测延迟柱状图已生成: {out_path}")
    return True


def generate_plots(data: dict, out_dir: Path) -> list[Path]:
    """生成当前输入支持的图表，并返回本次实际写出的路径。"""
    targets = [
        (plot_state_timeline, out_dir / "engineering_43_state_timeline.png"),
        (plot_torque_gating, out_dir / "engineering_43_torque_gating.png"),
        (plot_detection_latency, out_dir / "engineering_43_detection_latency.png"),
    ]
    return [path for plotter, path in targets if plotter(data, path)]


def main() -> int:
    parser = argparse.ArgumentParser(description="生成第 43 关故障注入图表")
    parser.add_argument("--input", default=str(INPUT_PATH))
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    out_dir = output_root / "plots"
    data = load_data(input_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    generated = generate_plots(data, out_dir)

    print(f"\n[SUMMARY] 图表已生成到 {out_dir}")
    print("[GENERATED_PLOTS] " + json.dumps([str(path) for path in generated]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
