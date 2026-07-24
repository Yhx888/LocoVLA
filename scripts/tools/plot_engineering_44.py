#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 44 关：文档-代码一致性与接口架构可视化脚本。

生成 2 张图：
  1. ``engineering_44_interface_map.png`` —— 接口架构图
     （用 matplotlib 绘制 nodes/topics/services 关系图，节点用方框，
     话题用椭圆，服务用菱形，箭头连接）
  2. ``engineering_44_doc_coverage.png`` —— 文档覆盖率柱状图
     （接口数/服务数/话题数/配置项数 四组对比）

数据来源：
  - ``outputs/results/doc_code_consistency_44.json``（一致性检查报告）
  - ``docs/design/interface_contract.md``（接口契约文档）

Windows 端运行：
  .\\.venv\\Scripts\\python.exe scripts\\tools\\plot_engineering_44.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 非交互后端，适合脚本运行
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

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
REPORT_PATH = ROOT / "outputs" / "results" / "doc_code_consistency_44.json"
OUT_DIR = ROOT / "outputs" / "plots"


def load_report(path: Path = REPORT_PATH) -> dict:
    """读取一致性检查报告 JSON。"""
    if not path.exists():
        raise FileNotFoundError(
            f"未找到一致性检查报告：{path}，"
            "请先运行 scripts/tools/check_doc_code_consistency.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 图 1：接口架构图
# ---------------------------------------------------------------------------


def _draw_box(ax, x, y, w, h, text, color, text_color="black"):
    """绘制方框节点。"""
    rect = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.5,
        edgecolor="black",
        facecolor=color,
    )
    ax.add_patch(rect)
    ax.text(x, y, text, ha="center", va="center", fontsize=10, color=text_color, weight="bold")


def _draw_ellipse(ax, x, y, w, h, text, color):
    """绘制椭圆（话题）。"""
    ell = mpatches.Ellipse(
        (x, y), w, h, linewidth=1.2, edgecolor="black", facecolor=color
    )
    ax.add_patch(ell)
    ax.text(x, y, text, ha="center", va="center", fontsize=9, color="black")


def _draw_diamond(ax, x, y, w, h, text, color):
    """绘制菱形（服务）。"""
    pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
    poly = mpatches.Polygon(pts, closed=True, linewidth=1.2, edgecolor="black", facecolor=color)
    ax.add_patch(poly)
    ax.text(x, y, text, ha="center", va="center", fontsize=9, color="black")


def _draw_arrow(ax, x1, y1, x2, y2, color="#444444"):
    """绘制箭头连接。"""
    arrow = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="->,head_width=0.18,head_length=0.18",
        color=color,
        linewidth=1.0,
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(arrow)


def plot_interface_map(report: dict, out_path: Path) -> None:
    """图 1：接口架构图（nodes/topics/services 关系图）。"""
    summary = report.get("summary", {})
    topics = summary.get("doc_topics", [])
    services = summary.get("doc_services", [])

    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(-1, 15)
    ax.set_ylim(-1, 11)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "第 44 关：Upkie 控制节点接口架构图",
        fontsize=15,
        pad=20,
        weight="bold",
    )

    # 节点位置布局
    # 控制节点（中心方框）
    node_x, node_y = 7.0, 5.5
    _draw_box(ax, node_x, node_y, 3.0, 1.2,
              "upkie_control\n(C++ 节点)", "#FFE4B5")

    # IMU 驱动节点（左上方框）
    imu_node_x, imu_node_y = 1.5, 8.5
    _draw_box(ax, imu_node_x, imu_node_y, 2.4, 1.0,
              "IMU 驱动节点", "#B5E4FF")

    # 轮端驱动节点（右上方框）
    wheel_node_x, wheel_node_y = 12.5, 8.5
    _draw_box(ax, wheel_node_x, wheel_node_y, 2.4, 1.0,
              "轮端驱动节点", "#B5E4FF")

    # 监控/日志节点（右下方框）
    monitor_node_x, monitor_node_y = 12.5, 2.5
    _draw_box(ax, monitor_node_x, monitor_node_y, 2.4, 1.0,
              "监控/日志节点", "#B5E4FF")

    # 操作员节点（左下方框）
    operator_node_x, operator_node_y = 1.5, 2.5
    _draw_box(ax, operator_node_x, operator_node_y, 2.4, 1.0,
              "操作员终端", "#D5B5FF")

    # 话题（椭圆）
    # /imu 在 IMU 驱动与控制节点之间
    _draw_ellipse(ax, 4.0, 7.0, 1.6, 0.8, "/imu\n(100Hz)", "#FFFACD")
    # /wheel_torque 在控制节点与轮端驱动之间
    _draw_ellipse(ax, 10.0, 7.0, 1.8, 0.8, "/wheel_torque\n(100Hz)", "#FFFACD")
    # /safety_state 在控制节点与监控节点之间
    _draw_ellipse(ax, 10.0, 4.0, 1.8, 0.8, "/safety_state\n(每 tick 100Hz)", "#FFFACD")

    # 服务（菱形）
    # /estop, /arm, /reset 在操作员与控制节点之间
    _draw_diamond(ax, 4.0, 4.5, 1.6, 1.0, "/estop", "#FFB5B5")
    _draw_diamond(ax, 4.0, 3.0, 1.6, 1.0, "/arm", "#FFB5B5")
    _draw_diamond(ax, 4.0, 1.5, 1.6, 1.0, "/reset", "#FFB5B5")

    # 箭头连接
    # IMU 驱动 -> /imu -> 控制节点（订阅）
    _draw_arrow(ax, imu_node_x + 1.2, imu_node_y - 0.4, 3.4, 7.2)
    _draw_arrow(ax, 4.6, 7.0, node_x - 1.4, node_y + 0.4, color="#1f77b4")
    # 控制节点 -> /wheel_torque -> 轮端驱动（发布）
    _draw_arrow(ax, node_x + 1.4, node_y + 0.4, 9.2, 7.0, color="#ff7f0e")
    _draw_arrow(ax, 10.8, 7.2, wheel_node_x - 1.2, wheel_node_y - 0.4)
    # 控制节点 -> /safety_state -> 监控节点（发布）
    _draw_arrow(ax, node_x + 1.4, node_y - 0.4, 9.2, 4.0, color="#2ca02c")
    _draw_arrow(ax, 10.8, 3.8, monitor_node_x - 1.2, monitor_node_y + 0.4)
    # 操作员 -> /estop, /arm, /reset -> 控制节点（服务调用）
    _draw_arrow(ax, operator_node_x + 1.2, operator_node_y + 0.2, 3.4, 4.5, color="#d62728")
    _draw_arrow(ax, operator_node_x + 1.2, operator_node_y, 3.4, 3.0, color="#d62728")
    _draw_arrow(ax, operator_node_x + 1.2, operator_node_y - 0.2, 3.4, 1.5, color="#d62728")
    _draw_arrow(ax, 4.7, 4.5, node_x - 1.4, node_y - 0.2, color="#d62728")
    _draw_arrow(ax, 4.7, 3.0, node_x - 1.4, node_y - 0.4, color="#d62728")
    _draw_arrow(ax, 4.7, 1.5, node_x - 1.4, node_y - 0.6, color="#d62728")

    # 图例
    legend_handles = [
        mpatches.Patch(facecolor="#FFE4B5", edgecolor="black", label="ROS2 节点（方框）"),
        mpatches.Patch(facecolor="#FFFACD", edgecolor="black", label="话题（椭圆）"),
        mpatches.Patch(facecolor="#FFB5B5", edgecolor="black", label="服务（菱形）"),
        mpatches.Patch(facecolor="#B5E4FF", edgecolor="black", label="外部节点"),
    ]
    ax.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=4, fontsize=10, frameon=False)

    # 底部说明
    summary_text = (
        f"接口统计：话题 {len(topics)} 个 / 服务 {len(services)} 个 | "
        "数据源：interface_contract.md <-> control_node.cpp"
    )
    fig.text(0.5, 0.02, summary_text, ha="center", fontsize=10, color="#555555")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 接口架构图已生成: {out_path}")


# ---------------------------------------------------------------------------
# 图 2：文档覆盖率柱状图
# ---------------------------------------------------------------------------


def plot_doc_coverage(report: dict, out_path: Path) -> None:
    """图 2：文档覆盖率柱状图（接口数/服务数/话题数/配置项数 对比）。"""
    summary = report.get("summary", {})

    doc_topics = summary.get("doc_topics", [])
    code_topics = summary.get("code_topics", [])
    doc_services = summary.get("doc_services", [])
    code_services = summary.get("code_services", [])
    doc_config_paths = summary.get("doc_config_paths", [])
    missing_config_paths = summary.get("missing_config_paths", [])
    existing_config_paths = len(doc_config_paths) - len(missing_config_paths)

    # 数据组装：四个维度，文档 vs 代码
    categories = ["话题数", "服务数", "配置项数", "YAML 残留"]
    doc_values = [
        len(doc_topics),
        len(doc_services),
        len(doc_config_paths),
        len(summary.get("yaml_references", [])),
    ]
    code_values = [
        len(code_topics),
        len(code_services),
        len(doc_config_paths),  # 配置项的"代码"基准即文档引用总数
        0,  # 期望 YAML 残留为 0
    ]

    x = list(range(len(categories)))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 6))
    bars1 = ax.bar([i - width / 2 for i in x], doc_values, width,
                   label="文档声明数", color="#1f77b4", alpha=0.85)
    bars2 = ax.bar([i + width / 2 for i in x], code_values, width,
                   label="代码实现/期望数", color="#ff7f0e", alpha=0.85)

    # 在柱顶标注数值
    for bars in (bars1, bars2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{int(h)}",
                        xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=10)

    ax.set_xlabel("接口类别", fontsize=12)
    ax.set_ylabel("数量", fontsize=12)
    ax.set_title("第 44 关：文档-代码一致性覆盖率（接口数/服务数/话题数/配置项数）",
                 fontsize=13, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3, linestyle="--", axis="y")

    # 标注一致性结果
    overall_passed = report.get("overall_passed", False)
    status_text = "[通过] 一致性检查通过" if overall_passed else "[未通过] 一致性检查未通过"
    status_color = "#17745a" if overall_passed else "#d36b27"
    ax.text(0.02, 0.95, status_text, transform=ax.transAxes,
            fontsize=12, color=status_color, weight="bold",
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor=status_color, alpha=0.9))

    # 标注检查项通过率
    checks = report.get("checks", [])
    passed_count = sum(1 for c in checks if c.get("passed"))
    total_count = len(checks)
    if total_count > 0:
        ax.text(0.02, 0.86, f"检查项通过：{passed_count}/{total_count}",
                transform=ax.transAxes, fontsize=10, color="#555555",
                verticalalignment="top")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 文档覆盖率柱状图已生成: {out_path}")


def main() -> int:
    """入口：读取报告并生成 2 张图。"""
    parser = argparse.ArgumentParser(description="生成第 44 关文档一致性图表")
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    out_dir = output_root / "plots"
    report = load_report(report_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_interface_map(report, out_dir / "engineering_44_interface_map.png")
    plot_doc_coverage(report, out_dir / "engineering_44_doc_coverage.png")

    print(f"\n[SUMMARY] 2 张图表已生成到 {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
