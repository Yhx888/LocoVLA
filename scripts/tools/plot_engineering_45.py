#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 45 关综合毕业项目可视化脚本。

生成 3 张图：
  1. ``engineering_45_e2e_flow.png`` —— 端到端流程图
     （5 个步骤的方框图：仿真启动 → PD 控制 → 安全状态机 → 日志记录 → 综合分析，
     标注每步的通过/失败状态和耗时）
  2. ``engineering_45_dimension_scores.png`` —— 8 维度评分雷达图
     （code/physics/robustness/realtime/safety/docs/design_review/oral_defense，
     每个维度 0.0 或 1.0）
  3. ``engineering_45_simulation_timeline.png`` —— 仿真时间线
     （base pitch、joint positions、torques 随时间变化，来自 1000 步仿真数据）

数据来源：
  - run_capstone() 返回的 report dict（含 dimension_scores、e2e_pipeline、simulation_data）

Windows 端运行：
  .\\.venv\\Scripts\\python.exe scripts\\tools\\plot_engineering_45.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 非交互后端，适合脚本运行
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# 中文字体配置（Windows 端优先使用 SimHei 或 Microsoft YaHei）
for font_name in ("Microsoft YaHei", "SimHei", "DejaVu Sans"):
    try:
        matplotlib.rcParams["font.sans-serif"] = [font_name]
        break
    except Exception:
        continue
matplotlib.rcParams["axes.unicode_minus"] = False  # 负号正常显示

# 仓库根目录
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "plots"

# 8 个评分维度（雷达图顺序）
DIMENSIONS = [
    "code",
    "physics",
    "robustness",
    "realtime",
    "safety",
    "docs",
    "design_review",
    "oral_defense",
]

# 维度中文名（用于雷达图标签）
DIMENSIONS_CN = {
    "code": "代码测试\ncode",
    "physics": "物理指标\nphysics",
    "robustness": "鲁棒性\nrobustness",
    "realtime": "实时性\nrealtime",
    "safety": "安全性\nsafety",
    "docs": "文档\ndocs",
    "design_review": "设计评审\ndesign_review",
    "oral_defense": "口头答辩\noral_defense",
}

# 5 步真实端到端链路（任务 4.2）
E2E_PIPELINE_STEPS = [
    ("physics", "仿真启动", "1000 步 MuJoCo 仿真"),
    ("code", "PD 控制", "PD 控制器应用到 1000 步仿真"),
    ("safety", "安全状态机", "pitch=0.5 触发 FAULT"),
    ("realtime", "日志记录", "9 字段 JSON lines"),
    ("robustness", "综合分析", "8 维度全部通过"),
]


def plot_e2e_flow(report: dict, out_path: Path) -> None:
    """图 1：端到端流程图。

    5 个步骤的方框图，从左到右排列，标注每步的通过/失败状态、耗时和关键指标。
    通过的步骤方框为绿色，失败的为红色，箭头连接表示流程。
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    e2e_pipeline = report.get("e2e_pipeline", {})
    e2e_overrides = report.get("e2e_overrides", {})

    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_xlim(0, 5.5)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    # 标题
    system_score = float(report.get("system_score", 0.0))
    status_text = "通过" if system_score >= 1.0 else "未通过"
    ax.set_title(
        f"第 45 关：端到端毕业项目流程图\nsystem_score = {system_score:.1f}（{status_text}）",
        fontsize=15,
        pad=20,
        weight="bold",
    )

    # 5 个步骤方框的位置（x 坐标）
    box_width = 0.9
    box_height = 1.6
    box_y = 2.5
    box_xs = [0.3, 1.4, 2.5, 3.6, 4.7]

    for i, (step_key, step_name, step_desc) in enumerate(E2E_PIPELINE_STEPS):
        result = e2e_pipeline.get(step_key, {})
        passed = bool(result.get("passed", False))
        details = result.get("details", {})
        elapsed_ms = float(details.get("elapsed_ms", 0.0))
        impacted = e2e_overrides.get(step_key, [])

        # 方框颜色
        color = "#17745a" if passed else "#d36b27"
        edge_color = "#0d4f3a" if passed else "#8a3a14"

        # 绘制方框
        x = box_xs[i]
        box = FancyBboxPatch(
            (x, box_y), box_width, box_height,
            boxstyle="round,pad=0.05",
            facecolor=color, edgecolor=edge_color, linewidth=2.0, alpha=0.85,
        )
        ax.add_patch(box)

        # 步骤序号 + 名称
        status_icon = "[OK]" if passed else "[X]"
        ax.text(
            x + box_width / 2, box_y + box_height - 0.25,
            f"{status_icon} 步骤 {i + 1}",
            ha="center", va="center", fontsize=11, weight="bold", color="white",
        )
        ax.text(
            x + box_width / 2, box_y + box_height - 0.55,
            step_name,
            ha="center", va="center", fontsize=12, weight="bold", color="white",
        )
        ax.text(
            x + box_width / 2, box_y + box_height - 0.85,
            step_desc,
            ha="center", va="center", fontsize=9, color="white",
        )
        # 耗时
        ax.text(
            x + box_width / 2, box_y + 0.3,
            f"{elapsed_ms:.2f} ms",
            ha="center", va="center", fontsize=10, weight="bold", color="white",
        )
        # 失败时归零维度
        if impacted:
            ax.text(
                x + box_width / 2, box_y + 0.05,
                f"归零: {','.join(impacted)}",
                ha="center", va="center", fontsize=8, color="#ffe0e0",
            )

        # 箭头连接到下一步
        if i < len(E2E_PIPELINE_STEPS) - 1:
            arrow = FancyArrowPatch(
                (x + box_width + 0.02, box_y + box_height / 2),
                (box_xs[i + 1] - 0.02, box_y + box_height / 2),
                arrowstyle="->", mutation_scale=20,
                color="#444444", linewidth=2.0,
            )
            ax.add_patch(arrow)

    # 底部汇总说明
    e2e_passed_count = sum(1 for v in e2e_pipeline.values() if v.get("passed"))
    e2e_total = len(E2E_PIPELINE_STEPS)
    summary_text = (
        f"5 步真实端到端链路通过数：{e2e_passed_count} / {e2e_total}\n"
        f"任一步骤失败令对应维度归零，system_score = min(所有维度)\n"
        f"链路：仿真启动 → PD 控制 → 安全状态机 → 日志记录 → 综合分析"
    )
    fig.text(
        0.5, 0.02, summary_text,
        ha="center", fontsize=10, color="#555555",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f5f5f5", edgecolor="#cccccc"),
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 端到端流程图已生成: {out_path}")


def plot_dimension_scores(report: dict, out_path: Path) -> None:
    """图 2：8 维度评分雷达图。

    用极坐标投影绘制，每个维度 0.0 或 1.0，
    通过的维度填充绿色，未通过的填充红色。
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dim_scores = report.get("dimension_scores", {})

    # 准备数据
    values = [float(dim_scores.get(dim, 0.0)) for dim in DIMENSIONS]
    values_closed = values + values[:1]

    # 角度
    angles = np.linspace(0, 2 * np.pi, len(DIMENSIONS), endpoint=False).tolist()
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": "polar"})

    # 雷达图填充
    color = "#17745a" if all(v >= 1.0 for v in values) else "#d36b27"
    ax.fill(angles_closed, values_closed, color=color, alpha=0.25)
    ax.plot(angles_closed, values_closed, color=color, linewidth=2.0, marker="o", markersize=8)

    # 顶点标注分数
    for angle, value, dim in zip(angles, values, DIMENSIONS):
        ax.text(
            angle, value + 0.1, f"{value:.1f}",
            ha="center", va="center", fontsize=11, weight="bold", color=color,
        )

    # 角度标签
    ax.set_xticks(angles)
    ax.set_xticklabels([DIMENSIONS_CN[dim] for dim in DIMENSIONS], fontsize=11)

    # 径向范围
    ax.set_ylim(0.0, 1.15)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.0", "0.25", "0.5", "0.75", "1.0"], fontsize=9, color="#555555")

    # 标题
    system_score = float(report.get("system_score", 0.0))
    status_text = "通过" if system_score >= 1.0 else "未通过"
    ax.set_title(
        f"第 45 关：8 维度评分雷达图\nsystem_score = {system_score:.1f}（{status_text}）",
        fontsize=14, pad=30, weight="bold",
    )

    # 端到端验证归零说明
    overrides = report.get("end_to_end_overrides", {})
    e2e_overrides = report.get("e2e_overrides", {})
    all_overrides = {**overrides, **e2e_overrides}
    if all_overrides:
        override_text = "归零维度：\n" + "\n".join(
            f"  - {step} → {', '.join(dims)}" for step, dims in all_overrides.items()
        )
    else:
        override_text = "端到端验证：6 步快速验证 + 5 步真实链路全部通过\n（无维度被强制归零）"
    fig.text(
        0.5, 0.02, override_text, ha="center", fontsize=10, color="#555555",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f5f5f5", edgecolor="#cccccc"),
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 8 维度评分雷达图已生成: {out_path}")


def plot_simulation_timeline(report: dict, out_path: Path) -> None:
    """图 3：仿真时间线图。

    3 个子图（来自 1000 步仿真数据）：
      - 上：base pitch 随时间变化
      - 中：6 个关节位置随时间变化
      - 下：6 个 ctrl 力矩随时间变化

    数据来源：report["simulation_data"]["physics"]（1000 步被动仿真）和
              report["simulation_data"]["code"]（1000 步 PD 控制仿真）。
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sim_data = report.get("simulation_data", {})

    # 优先使用 physics 数据（被动仿真，更稳定）
    physics_data = sim_data.get("physics", {})
    code_data = sim_data.get("code", {})

    if not physics_data and not code_data:
        # 兜底：生成空图
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(0.5, 0.5, "无仿真数据可用", ha="center", va="center",
                fontsize=14, transform=ax.transAxes)
        ax.set_title("第 45 关：仿真时间线图（无数据）", fontsize=14)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[WARN] 仿真时间线图无数据: {out_path}")
        return

    # 使用 code 数据（有 PD 控制的数据更有意义）
    plot_data = code_data if code_data else physics_data
    source_label = "PD 控制 1000 步" if code_data else "被动仿真 1000 步"

    time_series = plot_data.get("time", [])
    pitch_series = plot_data.get("base_pitch", [])
    joint_names = plot_data.get("joint_names", [])
    joint_positions = plot_data.get("joint_positions", [])
    torques = plot_data.get("torques", [])

    if not time_series:
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(0.5, 0.5, "时间序列数据为空", ha="center", va="center",
                fontsize=14, transform=ax.transAxes)
        ax.set_title("第 45 关：仿真时间线图（无时间数据）", fontsize=14)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    time_arr = np.array(time_series)

    # 3 个子图
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # 子图 1：base pitch
    ax1 = axes[0]
    pitch_arr = np.array(pitch_series)
    ax1.plot(time_arr, pitch_arr, color="#17745a", linewidth=1.5, label="base pitch")
    ax1.set_ylabel("base pitch (rad)", fontsize=11)
    ax1.set_title(
        f"第 45 关：仿真时间线图（{source_label}，{len(time_arr)} 步）",
        fontsize=13, weight="bold", pad=15,
    )
    ax1.grid(True, alpha=0.3, linestyle="--")
    ax1.legend(loc="best", fontsize=9)
    # 标注最终 pitch
    final_pitch = float(pitch_arr[-1]) if len(pitch_arr) > 0 else 0.0
    ax1.text(
        0.02, 0.95, f"final pitch = {final_pitch:.4f} rad",
        transform=ax1.transAxes, fontsize=10, va="top",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fffbe6", edgecolor="#cccccc"),
    )

    # 子图 2：6 个关节位置
    ax2 = axes[1]
    if joint_positions and joint_names:
        joint_pos_arr = np.array(joint_positions)
        colors = plt.cm.tab10(np.linspace(0, 1, len(joint_names)))
        for i, jname in enumerate(joint_names):
            ax2.plot(
                time_arr, joint_pos_arr[:, i],
                color=colors[i], linewidth=1.0, alpha=0.85, label=jname,
            )
    ax2.set_ylabel("关节位置 (rad)", fontsize=11)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(loc="best", fontsize=8, ncol=3)

    # 子图 3：6 个 ctrl 力矩
    ax3 = axes[2]
    if torques and joint_names:
        torque_arr = np.array(torques)
        colors = plt.cm.tab10(np.linspace(0, 1, len(joint_names)))
        for i, jname in enumerate(joint_names):
            ax3.plot(
                time_arr, torque_arr[:, i],
                color=colors[i], linewidth=1.0, alpha=0.85, label=jname,
            )
    ax3.set_ylabel("ctrl 力矩 (N·m)", fontsize=11)
    ax3.set_xlabel("仿真时间 (s)", fontsize=11)
    ax3.grid(True, alpha=0.3, linestyle="--")
    ax3.legend(loc="best", fontsize=8, ncol=3)

    # 底部说明
    total_steps = len(time_arr)
    final_time = float(time_arr[-1]) if len(time_arr) > 0 else 0.0
    fig.text(
        0.5, 0.005,
        f"仿真步数：{total_steps} | 总时长：{final_time:.3f}s | 关节数：{len(joint_names)} | 数据来源：simulation_data.json",
        ha="center", fontsize=9, color="#555555",
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 仿真时间线图已生成: {out_path}")


def main() -> int:
    """入口：调用 run_capstone 获取最新 report，生成 3 张图。"""
    sys.path.insert(0, str(ROOT / "src"))

    from upkie_mujoco_course.capstone import run_capstone

    report = run_capstone("outputs")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_e2e_flow(report, OUT_DIR / "engineering_45_e2e_flow.png")
    plot_dimension_scores(report, OUT_DIR / "engineering_45_dimension_scores.png")
    plot_simulation_timeline(report, OUT_DIR / "engineering_45_simulation_timeline.png")

    print("\n[SUMMARY] 3 张图表已生成到 outputs/plots/")
    print(f"  system_score = {report['system_score']:.1f}")
    print(f"  passed = {report['passed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
