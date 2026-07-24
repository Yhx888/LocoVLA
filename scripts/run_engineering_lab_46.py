#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 46 关实验编排入口：综合故障演练→报告→结果契约。

调用 ``scripts/tools/run_fault_drill.py`` 注入 4 大类 9 种故障，生成故障演练 JSON
和故障时间线图；再调用 ``scripts/tools/generate_fault_drill_report.py`` 生成实验
报告；最终汇总 metrics 写出统一结果契约（``outputs/results/engineering_46.json``）
和一份 Markdown portfolio 报告。

用法：
    python scripts/run_engineering_lab_46.py [--output-root outputs]
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

FAULT_DRILL_SCRIPT = ROOT / "scripts" / "tools" / "run_fault_drill.py"
REPORT_SCRIPT = ROOT / "scripts" / "tools" / "generate_fault_drill_report.py"


def _resolve_output_root(value: str, source_root: Path) -> Path:
    """将输出根目录解析为绝对路径，相对路径相对于源码根。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (source_root / p).resolve()


def _build_portfolio_report(
    summary: dict,
    result_path: Path,
    fault_json_path: Path,
    report_path: Path,
    plot_path: Path,
) -> str:
    """构造第 46 关 portfolio Markdown 报告。"""
    lines: list[str] = []
    lines.append("# 第 46 关故障演练与实验报告\n")
    lines.append("## 1. 评审摘要\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 注入故障总数 | {summary['fault_types_injected']} |")
    lines.append(f"| 检测成功数 | {summary['faults_detected']} |")
    lines.append(f"| 检测覆盖率 | {summary['coverage_percent']:.1f}% |")
    lines.append(f"| 平均检测延迟 | {summary['mean_detection_latency_ms']:.3f} ms |")
    lines.append(f"| 平均制动延迟 | {summary['mean_brake_latency_ms']:.3f} ms |")
    lines.append("")

    lines.append("## 2. 故障注入矩阵\n")
    lines.append("| 大类 | 故障名 | 现象 | 最终状态 | 安全 |")
    lines.append("|---|---|---|---|---|")
    type_cn = {
        "sensor": "传感器",
        "actuator": "执行器",
        "communication": "通信",
        "software": "软件",
    }
    for fault in summary["faults"]:
        safe_mark = "✓" if fault["safe"] else "✗"
        lines.append(
            f"| {type_cn.get(fault['fault_type'], fault['fault_type'])} | "
            f"`{fault['fault_name']}` | {fault['symptom']} | "
            f"{fault['final_state']} | {safe_mark} |"
        )
    lines.append("")

    lines.append("## 3. 故障时间线分析\n")
    lines.append(f"故障时间线图：`{plot_path}`\n")
    lines.append(
        f"- 平均检测延迟：**{summary['mean_detection_latency_ms']:.3f} ms**（阈值 200ms）\n"
        f"- 平均制动延迟：**{summary['mean_brake_latency_ms']:.3f} ms**\n"
        f"- 检测覆盖率：**{summary['coverage_percent']:.1f}%**\n"
    )

    lines.append("## 4. 产物路径\n")
    lines.append(f"- 结果契约：`{result_path}`")
    lines.append(f"- 故障演练 JSON：`{fault_json_path}`")
    lines.append(f"- 实验报告：`{report_path}`")
    lines.append(f"- 故障时间线图：`{plot_path}`")
    lines.append("- portfolio 报告：`outputs/portfolio/46/engineering_46_report.md`\n")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 46 关综合故障演练实验")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--output-root", default="outputs",
        help="输出根目录（相对路径相对于仓库根）",
    )
    parser.add_argument("--source-root", default=str(ROOT))
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = _resolve_output_root(args.output_root, source_root)
    fault_json_path = output_root / "results" / "engineering_46_fault_drill.json"
    plot_path = output_root / "plots" / "engineering_46_fault_timeline.png"
    report_path = output_root / "reports" / "fault_drill_46.md"

    # 1. 调用故障演练脚本（生成 JSON + 时间线图）
    cmd = [
        sys.executable,
        str(FAULT_DRILL_SCRIPT),
        "--output", str(fault_json_path),
        "--plot", str(plot_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        print(
            f"[FAIL] 第 46 关故障演练失败（退出码 {proc.returncode}）",
            file=sys.stderr,
        )
        return proc.returncode

    if not fault_json_path.exists():
        print(f"[FAIL] 故障演练 JSON 未生成：{fault_json_path}", file=sys.stderr)
        return 1
    if not plot_path.exists():
        print(f"[FAIL] 故障时间线图未生成：{plot_path}", file=sys.stderr)
        return 1

    summary = json.loads(fault_json_path.read_text(encoding="utf-8"))

    # 2. 调用实验报告生成器
    cmd = [
        sys.executable,
        str(REPORT_SCRIPT),
        "--input", str(fault_json_path),
        "--output", str(report_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        print(
            f"[FAIL] 实验报告生成失败（退出码 {proc.returncode}）",
            file=sys.stderr,
        )
        return proc.returncode

    if not report_path.exists():
        print(f"[FAIL] 实验报告未生成：{report_path}", file=sys.stderr)
        return 1

    # 3. 汇总 metrics 并写结果契约
    metrics: dict[str, float] = {
        "fault_types_injected": float(summary["fault_types_injected"]),
        "faults_detected": float(summary["faults_detected"]),
        "coverage_percent": float(summary["coverage_percent"]),
        "mean_detection_latency_ms": float(summary["mean_detection_latency_ms"]),
        "mean_brake_latency_ms": float(summary["mean_brake_latency_ms"]),
    }

    # 通过条件：9 种故障全检测 + 检测延迟 ≤ 200ms + 覆盖率 100%
    result_path = output_root / "results" / "engineering_46.json"
    write_experiment_result(
        result_path,
        chapter_id="46",
        seed=args.seed,
        config={
            "fault_json": str(fault_json_path),
            "report_path": str(report_path),
            "plot_path": str(plot_path),
            "fault_categories": ["sensor", "actuator", "communication", "software"],
        },
        metrics=metrics,
        pass_conditions={
            "faults_detected": {"operator": "==", "value": 9},
            "fault_types_injected": {"operator": "==", "value": 9},
            "coverage_percent": {"operator": "==", "value": 100},
            "mean_detection_latency_ms": {"operator": "<=", "value": 200},
        },
        plots=[str(plot_path)],
        logs=[str(fault_json_path), str(report_path)],
        root=source_root,
    )

    # 4. 写 portfolio 报告
    portfolio = output_root / "portfolio" / "46" / "engineering_46_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        _build_portfolio_report(
            summary, result_path, fault_json_path, report_path, plot_path
        ),
        encoding="utf-8",
    )

    print(f"[OK] 第 46 关结果契约：{result_path}")
    print(f"[OK] portfolio：{portfolio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
