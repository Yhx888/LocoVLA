#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 40 关实验编排入口：ROS2 控制节点端到端验证→写结果契约。

本脚本在 Windows 侧执行，读取已有的 WSL2 构建和测试证据
（位于 outputs/logs/engineering_40_*.log 和 outputs/plots/engineering_40.png），
汇总 metrics 并写出统一结果契约（``outputs/results/engineering_40.json``）。

真正的 colcon 构建和 gtest 运行需在 WSL2 环境中完成，
本脚本仅负责结果汇总和证据完整性验证。

用法：
    python scripts/run_engineering_lab_40.py [--output-root outputs]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib.image as mpimg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.results import write_experiment_result  # noqa: E402


_COLCON_SUMMARY_RE = re.compile(
    r"^Summary: (?P<tests>\d+) tests?, "
    r"(?P<errors>\d+) errors?, "
    r"(?P<failures>\d+) failures?, "
    r"(?P<skipped>\d+) skipped$"
)


def _resolve_path(value: str, base: Path) -> Path:
    """将路径解析为绝对路径，相对路径相对于指定根目录。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _valid_png(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        image = mpimg.imread(path)
    except (OSError, ValueError, SyntaxError):
        return False
    return image.ndim in {2, 3} and image.size > 0


def _qos_observation_is_valid(data: dict) -> bool:
    observed = data.get("observed")
    required = (
        "imu_subscription_count",
        "safety_publisher_count",
        "torque_publisher_count",
        "imu_published_count",
        "safety_received_count",
        "torque_received_count",
    )
    return (
        data.get("compatible") is True
        and isinstance(observed, dict)
        and all(float(observed.get(name, 0)) > 0 for name in required)
    )


def _read_colcon_summary(path: Path) -> tuple[int, int, int, bool]:
    """严格读取 colcon test-result 的唯一完整 Summary 行。"""
    if not path.is_file():
        return 0, 0, 0, False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return 0, 0, 0, False
    matches = [match for line in lines if (match := _COLCON_SUMMARY_RE.fullmatch(line))]
    if len(matches) != 1:
        return 0, 0, 0, False
    match = matches[0]
    return (
        int(match.group("tests")),
        int(match.group("errors")),
        int(match.group("failures")),
        True,
    )
def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 40 关 ROS2 控制节点实验")
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="用于生成源码摘要和相对证据路径的项目根目录",
    )
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = _resolve_path(args.output_root, source_root)

    # 检查已有证据是否存在
    required_evidence = [
        output_root / "plots" / "engineering_40.png",
        output_root / "logs" / "engineering_40_timing.json",
        output_root / "logs" / "engineering_40_qos.json",
        output_root / "logs" / "engineering_40_colcon_test.log",
    ]
    missing = [str(p) for p in required_evidence if not p.exists()]
    if missing:
        print(f"[WARN] 缺少以下证据文件（需在 WSL2 中生成）：", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    # 读取已有的 timing 数据
    timing_path = output_root / "logs" / "engineering_40_timing.json"
    timing = _read_json(timing_path)
    statistics = timing.get("statistics")
    if not isinstance(statistics, dict):
        statistics = timing

    # 读取 QoS 数据
    qos_path = output_root / "logs" / "engineering_40_qos.json"
    qos = _read_json(qos_path)
    qos_compatible = 1 if _qos_observation_is_valid(qos) else 0
    colcon_path = output_root / "logs" / "engineering_40_colcon_test.log"
    gtest_count, gtest_errors, gtest_failures, colcon_valid = _read_colcon_summary(
        colcon_path
    )

    plot_path = output_root / "plots" / "engineering_40.png"
    plot_valid = _valid_png(plot_path)
    timing_valid = bool(timing) and float(timing.get("sample_count", 0)) >= 2
    evidence_complete = (
        timing_valid and bool(qos_compatible) and plot_valid and colcon_valid
    )

    metrics: dict[str, float] = {
        "sample_count": float(timing.get("sample_count", 0)),
        "mean_period_ms": float(statistics.get("mean_period_ms", 0)),
        "p99_period_ms": float(statistics.get("p99_period_ms", 0)),
        "deadline_miss_count": float(statistics.get("deadline_miss_count", 0)),
        "gtest_count": float(gtest_count),
        "gtest_errors": float(gtest_errors),
        "gtest_failures": float(gtest_failures),
        "qos_compatible": float(qos_compatible),
        "evidence_complete": 1.0 if evidence_complete else 0.0,
    }

    # 收集实际存在的 plots 和 logs
    plots = [str(plot_path)] if plot_valid else []

    log_candidates = [
        "engineering_40_timing.json",
        "engineering_40_qos.json",
        "engineering_40_colcon_test.log",
        "engineering_42_log.jsonl",
        "engineering_43_control_node.log",
    ]
    logs = []
    for filename in log_candidates:
        path = output_root / "logs" / filename
        if path.is_file() and path.stat().st_size > 0:
            logs.append(str(path))

    result_path = output_root / "results" / "engineering_40.json"
    write_experiment_result(
        result_path,
        chapter_id="40",
        seed=args.seed,
        config={
            "ros2_distro": "jazzy",
            "build_base": "~/upkie-ros2-build/build",
            "install_base": "~/upkie-ros2-build/install",
            "log_base": "~/upkie-ros2-build/log",
            "control_rate_hz": 100,
        },
        metrics=metrics,
        pass_conditions={
            "gtest_count": {"operator": ">=", "value": 1},
            "gtest_errors": {"operator": "==", "value": 0},
            "gtest_failures": {"operator": "==", "value": 0},
            "deadline_miss_count": {"operator": "==", "value": 0},
            "qos_compatible": {"operator": "==", "value": 1},
            "mean_period_ms": {"operator": "<=", "value": 10.5},
            "evidence_complete": {"operator": "==", "value": 1},
        },
        plots=plots,
        logs=logs,
        validate_references=False,
        root=source_root,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    portfolio = output_root / "portfolio" / "40" / "evidence.json"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        json.dumps(
            {
                "chapter_id": "40",
                "title": "ROS2 控制节点端到端验证",
                "passed": result["passed"],
                "metrics": metrics,
                "plots": result["plots"],
                "logs": result["logs"],
                "evidence": {
                    "summary": "真实 ROS2 时序、QoS 收发和有效绘图的联合验收",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[OK] 第 40 关结果契约：{result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
