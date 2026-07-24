#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 44 关实验编排入口：生成设计评审报告→写结果契约。

调用 ``scripts/tools/generate_design_review_report.py`` 生成
``outputs/reports/design_review_44.md``，再据此汇总 metrics 写出
统一结果契约（``outputs/results/engineering_44.json``）与 portfolio
报告（``outputs/portfolio/44/engineering_44_report.md``）。

用法：
    python scripts/run_engineering_lab_44.py [--output-root outputs]
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

REPORT_SCRIPT = ROOT / "scripts" / "tools" / "generate_design_review_report.py"
CONSISTENCY_SCRIPT = ROOT / "scripts" / "tools" / "check_doc_code_consistency.py"
PLOT_SCRIPT = ROOT / "scripts" / "tools" / "plot_engineering_44.py"


def _resolve_output_root(value: str, source_root: Path) -> Path:
    """将输出根目录解析为绝对路径，相对路径相对于源码根。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (source_root / p).resolve()


def _parse_design_review_metrics(report_path: Path) -> dict[str, float]:
    """从本次设计评审 Markdown 的摘要表解析验收指标。"""
    rows: dict[str, str] = {}
    for line in report_path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 2:
            rows[cells[0]] = cells[1]
    fields = {
        "design_doc_word_count": "设计文档字数（估算）",
        "doc_coverage_percent": "文档接口覆盖率",
        "interface_count": "接口总数（话题+服务+参数）",
        "risk_count": "FMEA 风险条目数",
        "verification_count": "毕业门槛类别数",
    }
    missing = [label for label in fields.values() if label not in rows]
    if missing:
        raise ValueError(f"设计评审摘要缺少指标：{missing}")
    return {
        name: float(rows[label].rstrip("%"))
        for name, label in fields.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 44 关设计评审实验")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--source-root", default=str(ROOT))
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = _resolve_output_root(args.output_root, source_root)

    # 1. 调用设计评审报告生成器
    cmd = [
        sys.executable,
        str(REPORT_SCRIPT),
        "--output-root",
        str(output_root),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        print(
            f"[FAIL] 设计评审报告生成失败（退出码 {proc.returncode}）",
            file=sys.stderr,
        )
        return proc.returncode

    report_path = output_root / "reports" / "design_review_44.md"
    if not report_path.exists():
        print(f"[FAIL] 评审报告未生成：{report_path}", file=sys.stderr)
        return 1

    # 2. 汇总本次生成的设计报告与一致性检查指标
    consistency_cmd = [
        sys.executable,
        str(CONSISTENCY_SCRIPT),
        "--output-root",
        str(output_root),
    ]
    consistency_proc = subprocess.run(consistency_cmd, cwd=str(ROOT))
    if consistency_proc.returncode != 0:
        print("[FAIL] 文档与代码一致性检查未通过", file=sys.stderr)
        return consistency_proc.returncode
    consistency_path = output_root / "results" / "doc_code_consistency_44.json"
    try:
        report_metrics = _parse_design_review_metrics(report_path)
        consistency = json.loads(consistency_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] 第 44 关证据产物解析失败：{exc}", file=sys.stderr)
        return 1
    consistency_checks = consistency.get("checks", [])

    plot_proc = subprocess.run(
        [
            sys.executable,
            str(PLOT_SCRIPT),
            "--report", str(consistency_path),
            "--output-root", str(output_root),
        ],
        cwd=str(ROOT),
    )
    if plot_proc.returncode != 0:
        print("[FAIL] 第 44 关图表生成失败", file=sys.stderr)
        return plot_proc.returncode
    plots = [
        str(output_root / "plots" / "engineering_44_interface_map.png"),
        str(output_root / "plots" / "engineering_44_doc_coverage.png"),
    ]

    metrics: dict[str, float] = {
        **report_metrics,
        "consistency_overall_passed": float(bool(consistency.get("overall_passed"))),
        "consistency_check_count": float(len(consistency_checks)),
    }

    # 3. 写结果契约
    result_path = output_root / "results" / "engineering_44.json"
    write_experiment_result(
        result_path,
        chapter_id="44",
        seed=args.seed,
        config={
            "report_path": str(report_path),
            "design_docs": [
                "docs/design/system_design.md",
                "docs/design/interface_contract.md",
            ],
        },
        metrics=metrics,
        pass_conditions={
            "doc_coverage_percent": {"operator": "==", "value": 100},
            "interface_count": {"operator": ">=", "value": 10},
            "verification_count": {"operator": "==", "value": 8},
            "consistency_overall_passed": {"operator": "==", "value": 1},
            "consistency_check_count": {"operator": ">=", "value": 7},
        },
        plots=plots,
        logs=[str(report_path), str(consistency_path)],
        root=source_root,
    )

    # 4. 写 portfolio 报告
    portfolio = output_root / "portfolio" / "44" / "engineering_44_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        "# 第 44 关系统设计与接口评审报告\n\n"
        "## 评审摘要\n\n"
        "| 指标 | 数值 |\n"
        "|---|---|\n"
        f"| 文档覆盖率 | {metrics['doc_coverage_percent']:.1f}% |\n"
        f"| 接口总数 | {int(metrics['interface_count'])} |\n"
        f"| FMEA 风险条目数 | {int(metrics['risk_count'])} |\n"
        f"| 毕业门槛类别数 | {int(metrics['verification_count'])} |\n"
        f"| 设计文档字数（估算） | {int(metrics['design_doc_word_count'])} |\n\n"
        "## 通过条件\n\n"
        "- 门槛：`doc_coverage_percent == 100`、`interface_count >= 10`、"
        "`verification_count == 8`\n"
        f"- 当前文档覆盖率：{metrics['doc_coverage_percent']:.1f}%\n"
        f"- 当前接口总数：{int(metrics['interface_count'])}\n"
        f"- 当前毕业门槛类别数：{int(metrics['verification_count'])}\n\n"
        "## 证据文件\n\n"
        f"- 设计评审报告：`outputs/reports/design_review_44.md`\n"
        f"- 结果契约：`{result_path}`\n"
        f"- 系统设计文档：`docs/design/system_design.md`\n"
        f"- 接口契约文档：`docs/design/interface_contract.md`\n",
        encoding="utf-8",
    )

    print(f"[OK] 第 44 关结果契约：{result_path}")
    print(f"[OK] portfolio：{portfolio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
