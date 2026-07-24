#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 43 关：安全状态机故障演练脚本。

注入 5 种故障（IMU 断流、时间戳倒退、左右轮符号互换、CPU 过载、高层命令失联），
通过纯 Python 仿真安全状态机转换逻辑，记录检测延迟、制动延迟和最终状态。

注意：本脚本是 C++ test_safety_state_machine 的补充，不替代真实 ROS2 节点测试。
C++ 测试覆盖状态机正确性，本脚本覆盖故障注入的可观测性。

与 C++ ``safety_state_machine.cpp`` 的关系：
- 核心转换逻辑（reset 优先、NaN/通信失联/俯仰超限/急停 → FAULT、BOOT→SELF_CHECK→
  DISARMED→ARMED 推进）与 C++ 纯函数 ``transition`` 一致。
- 额外扩展：当 ``sensor_fresh=False`` 且当前状态非 BOOT 时进入 FAULT。该规则对应
  ``control_node.cpp`` 中对传感器新鲜度的监控（IMU 断流必须触发安全保护），
  C++ 纯函数未显式包含此规则，但在节点层由调用方保证。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Callable

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
        if inp.sensor_fresh:
            return SafetyState.DISARMED
        return SafetyState.SELF_CHECK
    if inp.current_state == SafetyState.DISARMED:
        if (inp.sensor_fresh
                and abs(inp.pitch_rad) < PITCH_SAFETY_LIMIT_RAD
                and inp.estop_released
                and inp.arm_requested):
            return SafetyState.ARMED
        return SafetyState.DISARMED
    if inp.current_state == SafetyState.ARMED:
        return SafetyState.ARMED
    return SafetyState.FAULT


def is_armed(state: SafetyState) -> bool:
    """是否允许输出 PD 力矩（仅 ARMED 状态允许）。"""
    return state == SafetyState.ARMED


@dataclass
class FaultInjection:
    """单个故障注入器：名称、描述、apply 函数。"""

    name: str
    description: str
    apply: Callable[[SafetyInput], SafetyInput]


def inject_imu_dropout() -> FaultInjection:
    """故障 1：IMU 断流（sensor_fresh=False）。

    仿真 IMU 在 500ms 内停止发布数据，状态机通过扩展规则检测到
    传感器不新鲜并进入 FAULT。
    """

    def apply(inp: SafetyInput) -> SafetyInput:
        return SafetyInput(
            inp.current_state, inp.pitch_rad, False, inp.estop_released,
            inp.arm_requested, inp.reset_requested, inp.nan_detected,
            inp.communication_lost,
        )

    return FaultInjection("imu_dropout", "IMU 断流 500ms，sensor_fresh=False", apply)


def inject_timestamp_regress() -> FaultInjection:
    """故障 2：时间戳倒退（视为 communication_lost）。

    时间戳倒退意味着数据链路出现异常或重放，状态机将其映射为
    通信失联并进入 FAULT。
    """

    def apply(inp: SafetyInput) -> SafetyInput:
        return SafetyInput(
            inp.current_state, inp.pitch_rad, inp.sensor_fresh, inp.estop_released,
            inp.arm_requested, inp.reset_requested, inp.nan_detected, True,
        )

    return FaultInjection("timestamp_regression", "时间戳倒退，视为通信失联", apply)


def inject_wheel_sign_swap() -> FaultInjection:
    """故障 3：左右轮符号互换（pitch 超限模拟）。

    左右轮符号互换会导致机器人俯仰发散，仿真中将 pitch 设为 0.5 rad
    （超过 0.3 rad 安全阈值），状态机检测到俯仰超限并进入 FAULT。
    """

    def apply(inp: SafetyInput) -> SafetyInput:
        return SafetyInput(
            inp.current_state, 0.5, inp.sensor_fresh, inp.estop_released,
            inp.arm_requested, inp.reset_requested, inp.nan_detected,
            inp.communication_lost,
        )

    return FaultInjection("wheel_sign_swap", "左右轮符号互换导致俯仰发散到 0.5 rad", apply)


def inject_cpu_overload() -> FaultInjection:
    """故障 4：CPU 过载（communication_lost）。

    CPU 过载导致控制循环超时、通信心跳丢失，状态机检测到通信失联
    并进入 FAULT。
    """

    def apply(inp: SafetyInput) -> SafetyInput:
        return SafetyInput(
            inp.current_state, inp.pitch_rad, inp.sensor_fresh, inp.estop_released,
            inp.arm_requested, inp.reset_requested, inp.nan_detected, True,
        )

    return FaultInjection("cpu_overload", "CPU 过载导致通信超时", apply)


def inject_command_loss() -> FaultInjection:
    """故障 5：高层命令失联（communication_lost）。

    高层命令链路中断，状态机检测到通信失联并进入 FAULT。
    """

    def apply(inp: SafetyInput) -> SafetyInput:
        return SafetyInput(
            inp.current_state, inp.pitch_rad, inp.sensor_fresh, inp.estop_released,
            inp.arm_requested, inp.reset_requested, inp.nan_detected, True,
        )

    return FaultInjection("command_loss", "高层命令失联", apply)


def _build_faults() -> list[FaultInjection]:
    """构造全部 5 种故障注入器。"""
    return [
        inject_imu_dropout(),
        inject_timestamp_regress(),
        inject_wheel_sign_swap(),
        inject_cpu_overload(),
        inject_command_loss(),
    ]


def run_fault_drill() -> dict:
    """运行全部 5 种故障注入，返回汇总结果。"""
    faults = _build_faults()
    results = []
    for fault in faults:
        # 起始状态：ARMED（最危险的工作状态，故障应立即被拦截）
        start_state = SafetyState.ARMED
        # 构造正常工作输入
        inp = SafetyInput(
            current_state=start_state,
            pitch_rad=0.05,
            sensor_fresh=True,
            estop_released=True,
            arm_requested=False,
            reset_requested=False,
            nan_detected=False,
            communication_lost=False,
        )
        # 应用故障并计时检测延迟
        t0 = time.monotonic()
        modified = fault.apply(inp)
        next_state = transition(modified)
        t1 = time.monotonic()
        detection_latency_ms = (t1 - t0) * 1000.0
        # 制动延迟：故障检测后立即输出零力矩（非 ARMED 状态即制动）
        # 若仍处于 ARMED 则视为未制动（999.0 ms 哨兵值）
        brake_latency_ms = 0.0 if next_state != SafetyState.ARMED else 999.0
        results.append({
            "fault_name": fault.name,
            "description": fault.description,
            "start_state": start_state.name,
            "final_state": next_state.name,
            "detection_latency_ms": round(detection_latency_ms, 3),
            "brake_latency_ms": brake_latency_ms,
            "safe": next_state == SafetyState.FAULT,
        })
    summary = {
        "fault_count": len(results),
        "detected_count": sum(1 for r in results if r["safe"]),
        "all_faults_safe": all(r["safe"] for r in results),
        "mean_detection_latency_ms": round(
            sum(r["detection_latency_ms"] for r in results) / len(results), 3
        ),
        "mean_brake_latency_ms": round(
            sum(r["brake_latency_ms"] for r in results) / len(results), 3
        ),
        "faults": results,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="第 43 关安全状态机故障演练")
    parser.add_argument(
        "--output",
        default="outputs/results/engineering_43_fault_injection.json",
        help="故障演练结果 JSON 输出路径（相对路径相对于仓库根）",
    )
    args = parser.parse_args()

    summary = run_fault_drill()

    # 解析输出路径：相对路径相对于仓库根（脚本位于 scripts/tools/）
    output_path = Path(args.output)
    if not output_path.is_absolute():
        root = Path(__file__).resolve().parents[2]
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[OK] 故障演练结果已写入：{output_path}", file=sys.stderr)
    return 0 if summary["all_faults_safe"] else 1


if __name__ == "__main__":
    sys.exit(main())
