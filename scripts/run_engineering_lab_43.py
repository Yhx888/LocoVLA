#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 43 关实验编排入口：故障演练→结果契约→portfolio 报告。

调用 ``scripts/tools/run_safety_fault_injection.py`` 注入 5 种故障，
生成故障演练 JSON，再合并 C++ 端 GoogleTest 统计信息，最终写出可由
仪表盘读取的结果契约（``outputs/results/engineering_43.json``）和一份
Markdown portfolio 报告（含安全分析表、故障树、演练记录）。

用法：
    python scripts/run_engineering_lab_43.py \
        [--output-root outputs] \
        [--colcon-test-log <path>] [--seed 0]
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

FAULT_SCRIPT = ROOT / "scripts" / "tools" / "run_safety_fault_injection.py"
PLOT_SCRIPT = ROOT / "scripts" / "tools" / "plot_engineering_43.py"


def _resolve_output_root(value: str, source_root: Path) -> Path:
    """将输出根目录解析为绝对路径，相对路径相对于源码根。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (source_root / p).resolve()


def _build_portfolio_report(
    summary: dict,
    gtest_count: int,
    gtest_failures: int,
    result_path: Path,
    fault_json_path: Path,
) -> str:
    """构造第 43 关 portfolio Markdown 报告。

    包含安全分析表、故障树、演练记录三部分。
    """
    lines: list[str] = []
    lines.append("# 第 43 关部署、安全与故障恢复报告\n")
    lines.append("## 指标\n")
    lines.append("## 1. 安全状态机\n")
    lines.append(
        "状态机五状态：`BOOT → SELF_CHECK → DISARMED → ARMED → FAULT`，"
        "故障检测优先级最高，FAULT 仅通过 `/reset` 服务人工复位。\n"
    )
    lines.append("- 力矩门控：仅 `ARMED` 状态输出 PD 力矩，其余状态输出零力矩。\n")
    lines.append(
        "- 故障触发条件：NaN / 通信失联 / 俯仰超限（|pitch|>0.3）/ 急停触发 / 传感器断流。\n"
    )

    lines.append("\n## 2. 安全分析表\n")
    lines.append("| 故障 | 检测信号 | 状态机动作 | 起始状态 | 最终状态 |")
    lines.append("|---|---|---|---|---|")
    fault_tree_map = {
        "imu_dropout": ("sensor_fresh=False", "进入 FAULT"),
        "timestamp_regression": ("communication_lost=True", "进入 FAULT"),
        "wheel_sign_swap": ("pitch=0.5 > 0.3", "进入 FAULT"),
        "cpu_overload": ("communication_lost=True", "进入 FAULT"),
        "command_loss": ("communication_lost=True", "进入 FAULT"),
    }
    for fault in summary["faults"]:
        detection, action = fault_tree_map.get(
            fault["fault_name"], ("未知", "进入 FAULT")
        )
        lines.append(
            f"| {fault['fault_name']} | {detection} | {action} | "
            f"{fault['start_state']} | {fault['final_state']} |"
        )

    lines.append("\n## 3. 故障树\n")
    lines.append("```")
    lines.append("任意工作状态 (ARMED/DISMARED/SELF_CHECK)")
    lines.append("  ├── IMU 断流 (sensor_fresh=False) ──────────> FAULT")
    lines.append("  ├── 时间戳倒退 (communication_lost=True) ───> FAULT")
    lines.append("  ├── 左右轮符号互换 (|pitch|>0.3) ──────────> FAULT")
    lines.append("  ├── CPU 过载 (communication_lost=True) ─────> FAULT")
    lines.append("  └── 高层命令失联 (communication_lost=True) ─> FAULT")
    lines.append("FAULT ──(/reset 服务)──> BOOT ──> SELF_CHECK ──> DISARMED ──> ARMED")
    lines.append("```")

    lines.append("\n## 4. 故障演练记录\n")
    lines.append("| 故障名称 | 检测延迟 (ms) | 制动延迟 (ms) | 安全 |")
    lines.append("|---|---|---|---|")
    for fault in summary["faults"]:
        safe_mark = "✓" if fault["safe"] else "✗"
        lines.append(
            f"| {fault['fault_name']} | {fault['detection_latency_ms']:.3f} | "
            f"{fault['brake_latency_ms']:.1f} | {safe_mark} |"
        )
    lines.append(
        f"\n- 故障总数：`{summary['fault_count']}`\n"
        f"- 检测成功数：`{summary['detected_count']}`\n"
        f"- 全部安全：`{summary['all_faults_safe']}`\n"
        f"- 平均检测延迟：`{summary['mean_detection_latency_ms']:.3f} ms`\n"
        f"- 平均制动延迟：`{summary['mean_brake_latency_ms']:.1f} ms`\n"
    )

    lines.append("\n## 5. C++ 测试统计\n")
    lines.append(
        f"- GoogleTest 用例：`{gtest_count}`，失败：`{gtest_failures}`\n"
    )
    lines.append(
        "- C++ 测试源文件：`ros2_ws/src/upkie_control/test/test_safety_state_machine.cpp`\n"
    )

    lines.append("\n## 6. 产物路径\n")
    lines.append(f"- 结果契约：`{result_path}`\n")
    lines.append(f"- 故障演练 JSON：`{fault_json_path}`\n")
    lines.append(
        "- portfolio 报告：`outputs/portfolio/43/engineering_43_report.md`\n"
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 43 关安全故障演练实验")
    parser.add_argument(
        "--output-root", default="outputs",
        help="输出根目录（相对路径相对于仓库根）",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="用于源码摘要和相对证据路径的项目根目录",
    )
    parser.add_argument("--colcon-test-log", default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

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
    fault_json_path = output_root / "results" / "engineering_43_fault_injection.json"

    # 调用故障演练脚本（在仓库根目录执行，便于相对路径解析）
    cmd = [
        sys.executable,
        str(FAULT_SCRIPT),
        "--output", str(fault_json_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        print(
            f"[FAIL] 第 43 关故障演练失败（退出码 {proc.returncode}）",
            file=sys.stderr,
        )
        return proc.returncode

    # 解析故障演练产物
    if not fault_json_path.exists():
        print(
            f"[FAIL] 故障演练 JSON 未生成：{fault_json_path}",
            file=sys.stderr,
        )
        return 1
    summary = json.loads(fault_json_path.read_text(encoding="utf-8"))

    plot_proc = subprocess.run(
        [
            sys.executable,
            str(PLOT_SCRIPT),
            "--input", str(fault_json_path),
            "--output-root", str(output_root),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if plot_proc.stdout:
        print(plot_proc.stdout, end="")
    if plot_proc.stderr:
        print(plot_proc.stderr, end="", file=sys.stderr)
    if plot_proc.returncode != 0:
        print("[FAIL] 第 43 关图表生成失败", file=sys.stderr)
        return plot_proc.returncode
    generated_line = next(
        (
            line.removeprefix("[GENERATED_PLOTS] ")
            for line in reversed(plot_proc.stdout.splitlines())
            if line.startswith("[GENERATED_PLOTS] ")
        ),
        None,
    )
    if generated_line is None:
        print("[FAIL] 第 43 关绘图脚本未返回本次生成清单", file=sys.stderr)
        return 1
    try:
        plots = [str(Path(item)) for item in json.loads(generated_line)]
    except (json.JSONDecodeError, TypeError):
        print("[FAIL] 第 43 关本次生成清单格式无效", file=sys.stderr)
        return 1

    # 合并 C++ 端测试信息，构造 metrics
    metrics: dict[str, float] = {
        "fault_count": float(summary["fault_count"]),
        "detected_count": float(summary["detected_count"]),
        "all_faults_safe": 1.0 if summary["all_faults_safe"] else 0.0,
        "mean_detection_latency_ms": float(summary["mean_detection_latency_ms"]),
        "mean_brake_latency_ms": float(summary["mean_brake_latency_ms"]),
        "gtest_count": float(gtest_count),
        "gtest_errors": float(gtest_errors),
        "gtest_failures": float(gtest_failures),
        "colcon_summary_valid": float(colcon_valid),
    }

    # 通过条件：全部故障安全 + 检测数等于故障数 + 检测延迟 ≤ 200ms + C++ 测试零失败
    result_path = output_root / "results" / "engineering_43.json"
    logs = [str(fault_json_path)]
    if colcon_path.is_file() and colcon_path.stat().st_size > 0:
        logs.append(str(colcon_path))

    write_experiment_result(
        result_path,
        chapter_id="43",
        seed=args.seed,
        config={
            "fault_json": str(fault_json_path),
            "colcon_test_log": str(colcon_path),
            "state_machine": "BOOT → SELF_CHECK → DISARMED → ARMED → FAULT",
        },
        metrics=metrics,
        pass_conditions={
            "all_faults_safe": {"operator": "==", "value": 1},
            "detected_count": {"operator": "==", "value": 5},
            "fault_count": {"operator": "==", "value": 5},
            "mean_detection_latency_ms": {"operator": "<=", "value": 200},
            "gtest_count": {"operator": ">=", "value": 1},
            "gtest_errors": {"operator": "==", "value": 0},
            "gtest_failures": {"operator": "==", "value": 0},
            "colcon_summary_valid": {"operator": "==", "value": 1},
        },
        plots=plots,
        logs=logs,
        root=source_root,
    )

    # 写 portfolio 报告
    portfolio = output_root / "portfolio" / "43" / "engineering_43_report.md"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        _build_portfolio_report(
            summary, gtest_count, gtest_failures, result_path, fault_json_path
        ),
        encoding="utf-8",
    )

    print(f"[OK] 第 43 关结果契约：{result_path}")
    print(f"[OK] portfolio：{portfolio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
