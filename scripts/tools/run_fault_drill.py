#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 46 关：综合故障演练脚本。

在第 43 关安全状态机基础上扩展，注入 4 大类故障（传感器、执行器、通信、软件），
共 9 种具体故障，生成故障时间线图和实验报告数据。

4 大类故障：
1. 传感器故障：IMU 断流、噪声突增、协方差无效
2. 执行器故障：力矩饱和、轮符号互换
3. 通信故障：消息延迟、丢包
4. 软件故障：NaN、除零

复用第 43 关 ``run_safety_fault_injection.py`` 的 SafetyState/SafetyInput/transition 逻辑
（内联重实现，避免跨模块依赖）。每种故障记录 fault_type、fault_name、symptom、
detection_latency_ms、brake_latency_ms、final_state、safe 七个字段。

产物：
- ``outputs/results/engineering_46_fault_drill.json``：故障演练汇总 JSON
- ``outputs/plots/engineering_46_fault_timeline.png``：故障时间线图

用法：
    python scripts/tools/run_fault_drill.py \\
        [--output outputs/results/engineering_46_fault_drill.json] \\
        [--plot outputs/plots/engineering_46_fault_timeline.png]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 中文字体配置（Windows 优先 Microsoft YaHei）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Noto Sans SC", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 俯仰安全阈值（rad），与 C++ PITCH_SAFETY_LIMIT_RAD 一致
PITCH_SAFETY_LIMIT_RAD = 0.3


class SafetyState(IntEnum):
    """安全状态机五状态，与 C++ SafetyState 枚举一一对应。"""

    BOOT = 0
    SELF_CHECK = 1
    DISARMED = 2
    ARMED = 3
    FAULT = 4


@dataclass
class SafetyInput:
    """状态机输入向量，与 C++ SafetyInput 结构对齐。"""

    current_state: int
    pitch_rad: float
    sensor_fresh: bool
    estop_released: bool
    arm_requested: bool
    reset_requested: bool
    nan_detected: bool
    communication_lost: bool


def transition(inp: SafetyInput) -> SafetyState:
    """复现 C++ safety_state_machine.cpp 的转换逻辑。

    优先级（自顶向下）：
      1. FAULT + 显式 reset → BOOT（人工复位）
      2. 任何故障条件 → FAULT（NaN / 通信失联 / 急停触发 / 俯仰超限）
      3. 传感器断流扩展规则：非 BOOT 状态下 sensor_fresh=False → FAULT
      4. 状态机正常推进（BOOT→SELF_CHECK→DISARMED→ARMED）
    """
    # 1. reset 优先：FAULT → BOOT
    if inp.current_state == SafetyState.FAULT and inp.reset_requested:
        return SafetyState.BOOT
    # 2. 故障触发（任意状态 → FAULT）：NaN / 通信失联 / 急停
    if inp.nan_detected or inp.communication_lost or not inp.estop_released:
        return SafetyState.FAULT
    if abs(inp.pitch_rad) > PITCH_SAFETY_LIMIT_RAD:
        return SafetyState.FAULT
    # 3. 传感器断流扩展规则（对应 control_node 的传感器新鲜度监控）
    if not inp.sensor_fresh and inp.current_state != SafetyState.BOOT:
        return SafetyState.FAULT
    # 4. 正常推进
    if inp.current_state == SafetyState.BOOT:
        return SafetyState.SELF_CHECK
    if inp.current_state == SafetyState.SELF_CHECK:
        return SafetyState.DISARMED if inp.sensor_fresh else SafetyState.SELF_CHECK
    if inp.current_state == SafetyState.DISARMED:
        if (
            inp.sensor_fresh
            and abs(inp.pitch_rad) < PITCH_SAFETY_LIMIT_RAD
            and inp.estop_released
            and inp.arm_requested
        ):
            return SafetyState.ARMED
        return SafetyState.DISARMED
    if inp.current_state == SafetyState.ARMED:
        return SafetyState.ARMED
    return SafetyState.FAULT


@dataclass
class FaultResult:
    """单个故障演练结果。

    Attributes:
        fault_type: 故障大类（sensor/actuator/communication/software）
        fault_name: 具体故障名
        symptom: 故障现象描述
        detection_latency_ms: 检测延迟（ms）
        brake_latency_ms: 制动延迟（ms），非 ARMED 状态为 0
        final_state: 最终状态名（BOOT/SELF_CHECK/DISARMED/ARMED/FAULT）
        safe: 是否进入 FAULT（True 表示安全检测成功）
    """

    fault_type: str
    fault_name: str
    symptom: str
    detection_latency_ms: float
    brake_latency_ms: float
    final_state: str
    safe: bool


def _measure_transition(inp: SafetyInput) -> tuple[SafetyState, float]:
    """应用故障并计时检测延迟，返回 (下一状态, 检测延迟 ms)。"""
    t0 = time.monotonic()
    next_state = transition(inp)
    t1 = time.monotonic()
    return next_state, (t1 - t0) * 1000.0


def _make_result(
    fault_type: str,
    fault_name: str,
    symptom: str,
    inp: SafetyInput,
) -> FaultResult:
    """构造单个故障演练结果。

    起始状态固定为 ARMED（最危险的工作状态，故障应立即被拦截）。
    制动延迟：非 ARMED 状态即制动（0ms），仍处于 ARMED 视为未制动（999ms 哨兵）。
    """
    next_state, latency_ms = _measure_transition(inp)
    brake_latency = 0.0 if next_state != SafetyState.ARMED else 999.0
    return FaultResult(
        fault_type=fault_type,
        fault_name=fault_name,
        symptom=symptom,
        detection_latency_ms=round(latency_ms, 3),
        brake_latency_ms=brake_latency,
        final_state=next_state.name,
        safe=next_state == SafetyState.FAULT,
    )


def inject_sensor_faults() -> list[FaultResult]:
    """传感器故障：IMU 断流、噪声突增、协方差无效。"""
    results: list[FaultResult] = []
    # IMU 断流：sensor_fresh=False，扩展规则触发 FAULT
    inp = SafetyInput(SafetyState.ARMED, 0.05, False, True, False, False, False, False)
    results.append(
        _make_result("sensor", "imu_dropout", "IMU 断流 500ms，sensor_fresh=False", inp)
    )
    # 噪声突增：pitch=0.5 > 0.3 安全阈值，俯仰超限触发 FAULT
    inp = SafetyInput(SafetyState.ARMED, 0.5, True, True, False, False, False, False)
    results.append(
        _make_result("sensor", "noise_burst", "噪声突增导致 pitch=0.5 > 0.3", inp)
    )
    # 协方差无效：传感器不新鲜（协方差无效时数据不可信）
    inp = SafetyInput(SafetyState.ARMED, 0.0, False, True, False, False, False, False)
    results.append(
        _make_result("sensor", "covariance_invalid", "协方差无效，传感器不新鲜", inp)
    )
    return results


def inject_actuator_faults() -> list[FaultResult]:
    """执行器故障：力矩饱和、轮符号互换。"""
    results: list[FaultResult] = []
    # 力矩饱和：pitch 发散到 0.4 > 0.3，俯仰超限触发 FAULT
    inp = SafetyInput(SafetyState.ARMED, 0.4, True, True, False, False, False, False)
    results.append(
        _make_result(
            "actuator", "torque_saturation", "力矩饱和导致 pitch 发散到 0.4", inp
        )
    )
    # 轮符号互换：左右轮方向反，pitch 发散到 0.5 > 0.3
    inp = SafetyInput(SafetyState.ARMED, 0.5, True, True, False, False, False, False)
    results.append(
        _make_result(
            "actuator", "wheel_sign_swap", "左右轮符号互换导致发散到 0.5", inp
        )
    )
    return results


def inject_communication_faults() -> list[FaultResult]:
    """通信故障：消息延迟、丢包。"""
    results: list[FaultResult] = []
    # 消息延迟：心跳超时，communication_lost=True
    inp = SafetyInput(SafetyState.ARMED, 0.05, True, True, False, False, False, True)
    results.append(
        _make_result("communication", "message_delay", "消息延迟导致通信失联", inp)
    )
    # 丢包：通信链路中断，communication_lost=True
    inp = SafetyInput(SafetyState.ARMED, 0.05, True, True, False, False, False, True)
    results.append(
        _make_result("communication", "packet_loss", "丢包导致通信失联", inp)
    )
    return results


def inject_software_faults() -> list[FaultResult]:
    """软件故障：NaN、除零。"""
    results: list[FaultResult] = []
    # NaN 检测：nan_detected=True，立即触发 FAULT
    inp = SafetyInput(SafetyState.ARMED, 0.05, True, True, False, False, True, False)
    results.append(_make_result("software", "nan_detected", "NaN 检测", inp))
    # 除零：产生 NaN，视为 nan_detected=True
    inp = SafetyInput(SafetyState.ARMED, 0.05, True, True, False, False, True, False)
    results.append(
        _make_result("software", "divide_by_zero", "除零导致 NaN", inp)
    )
    return results


def plot_fault_timeline(results: list[FaultResult], output_path: Path) -> None:
    """生成故障时间线图。

    x 轴：检测延迟（ms），y 轴：故障事件（按 fault_name 排列）。
    每种故障大类用不同颜色标记，标注检测延迟值和最终状态。
    """
    # 4 大类故障的颜色与标记映射
    type_styles = {
        "sensor": {"color": "#1f77b4", "marker": "o", "label": "传感器故障"},
        "actuator": {"color": "#ff7f0e", "marker": "s", "label": "执行器故障"},
        "communication": {"color": "#2ca02c", "marker": "^", "label": "通信故障"},
        "software": {"color": "#d62728", "marker": "D", "label": "软件故障"},
    }

    # y 轴标签：fault_name（自顶向下排列，与列表顺序一致）
    fault_names = [r.fault_name for r in results]
    # 反转使第一个故障在顶部
    y_positions = list(range(len(fault_names)))[::-1]

    fig, ax = plt.subplots(figsize=(12, 7))

    # 按大类分组绘制，便于图例去重
    plotted_types: set[str] = set()
    for idx, r in enumerate(results):
        style = type_styles.get(r.fault_type, {"color": "gray", "marker": "x", "label": r.fault_type})
        y = y_positions[idx]
        # 横向条形：从 0 到 detection_latency_ms
        ax.barh(
            y,
            max(r.detection_latency_ms, 0.001),  # 避免 0 宽度不可见
            left=0.0,
            height=0.6,
            color=style["color"],
            alpha=0.35,
            edgecolor=style["color"],
            linewidth=0.5,
        )
        # 标记点
        legend_label = style["label"] if r.fault_type not in plotted_types else None
        ax.scatter(
            r.detection_latency_ms,
            y,
            color=style["color"],
            marker=style["marker"],
            s=120,
            zorder=5,
            label=legend_label,
        )
        plotted_types.add(r.fault_type)
        # 标注：检测延迟值 + 最终状态（用 OK/FAIL 避免 ✓ 字形缺失）
        safe_mark = "OK" if r.safe else "FAIL"
        annotation = f"{r.detection_latency_ms:.3f}ms -> {r.final_state} [{safe_mark}]"
        ax.annotate(
            annotation,
            xy=(r.detection_latency_ms, y),
            xytext=(8, 0),
            textcoords="offset points",
            fontsize=8,
            va="center",
            color=style["color"],
        )

    # 坐标轴配置
    ax.set_yticks(y_positions)
    ax.set_yticklabels(fault_names, fontsize=9)
    ax.set_xlabel("检测延迟 (ms)", fontsize=11)
    ax.set_ylabel("故障事件", fontsize=11)
    ax.set_title("第 46 关：综合故障演练时间线（4 大类 9 种故障）", fontsize=13)
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.axvline(x=200, color="red", linestyle=":", linewidth=1.2, alpha=0.6, label="200ms 阈值")

    # x 轴留余量给标注
    x_max = max((r.detection_latency_ms for r in results), default=1.0)
    ax.set_xlim(-0.05, x_max * 1.5 + 0.5)

    # 图例
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_fault_drill() -> dict[str, Any]:
    """运行全部 4 大类故障注入，返回汇总结果。"""
    results: list[FaultResult] = []
    results.extend(inject_sensor_faults())
    results.extend(inject_actuator_faults())
    results.extend(inject_communication_faults())
    results.extend(inject_software_faults())

    summary: dict[str, Any] = {
        "fault_types_injected": len(results),
        "faults_detected": sum(1 for r in results if r.safe),
        "mean_detection_latency_ms": round(
            sum(r.detection_latency_ms for r in results) / len(results), 3
        ),
        "mean_brake_latency_ms": round(
            sum(r.brake_latency_ms for r in results) / len(results), 3
        ),
        "coverage_percent": 100.0 * sum(1 for r in results if r.safe) / len(results),
        "faults": [asdict(r) for r in results],
    }
    return summary


def _resolve_path(value: str, parents_level: int) -> Path:
    """将相对路径解析为相对于仓库 ROOT 的绝对路径。"""
    p = Path(value)
    if p.is_absolute():
        return p
    root = Path(__file__).resolve().parents[parents_level]
    return root / p


def main() -> int:
    parser = argparse.ArgumentParser(description="第 46 关综合故障演练")
    parser.add_argument(
        "--output",
        default="outputs/results/engineering_46_fault_drill.json",
        help="故障演练结果 JSON 输出路径（相对路径相对于仓库根）",
    )
    parser.add_argument(
        "--plot",
        default="outputs/plots/engineering_46_fault_timeline.png",
        help="故障时间线图输出路径（相对路径相对于仓库根）",
    )
    args = parser.parse_args()

    summary = run_fault_drill()

    # 写故障演练 JSON
    output_path = _resolve_path(args.output, parents_level=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 生成故障时间线图
    plot_path = _resolve_path(args.plot, parents_level=2)
    plot_fault_timeline(
        [FaultResult(**f) for f in summary["faults"]], plot_path
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[OK] 故障演练 JSON：{output_path}", file=sys.stderr)
    print(f"[OK] 故障时间线图：{plot_path}", file=sys.stderr)
    return 0 if summary["faults_detected"] == summary["fault_types_injected"] else 1


if __name__ == "__main__":
    sys.exit(main())
