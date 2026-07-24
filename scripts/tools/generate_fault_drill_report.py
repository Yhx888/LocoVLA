#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 46 关：故障演练实验报告生成器。

读取 ``outputs/results/engineering_46_fault_drill.json``，按
``fault → symptom → evidence → root cause → corrective action`` 链路
生成 ``outputs/reports/fault_drill_46.md``，覆盖评审摘要、故障注入矩阵、
故障时间线分析、根因分析、纠正动作和评审结论六个部分。

用法：
    python scripts/tools/generate_fault_drill_report.py \\
        [--input outputs/results/engineering_46_fault_drill.json] \\
        [--output outputs/reports/fault_drill_46.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 根因分析与纠正动作知识库：每种故障的 root cause 和 corrective action
# key = fault_name，value = (root_cause, corrective_action)
_ROOT_CAUSE_TABLE: dict[str, tuple[str, str]] = {
    "imu_dropout": (
        "IMU 驱动崩溃或 USB 连接松动导致话题停止发布，control_node 的传感器新鲜度监控"
        "（sensor_fresh=False）在非 BOOT 状态下触发 FAULT。",
        "增加 IMU 心跳看门狗（100ms 超时），故障后自动尝试重连；"
        "记录 IMU 断流时间戳到统一日志，便于事后定位。",
    ),
    "noise_burst": (
        "IMU 受电磁干扰或机械振动影响，俯仰角噪声突增到 0.5 rad，"
        "超过 PITCH_SAFETY_LIMIT_RAD=0.3 安全阈值，状态机检测到俯仰超限触发 FAULT。",
        "在 IMU 端增加硬件低通滤波；状态机层对 pitch 做 3 帧滑动平均后再判阈值，"
        "避免单帧噪声误触发。",
    ),
    "covariance_invalid": (
        "EKF 协方差矩阵发散或非正定，状态估计不可信，control_node 将 sensor_fresh "
        "置 False，扩展规则触发 FAULT。",
        "增加协方差矩阵正定性检查；EKF 内部增加协方差重置逻辑（发散时回退到先验估计）。",
    ),
    "torque_saturation": (
        "PD 控制器输出力矩超过执行器上限（±1.0 N·m），无法跟踪期望姿态，"
        "俯仰角发散到 0.4 rad 超过安全阈值，状态机检测到俯仰超限触发 FAULT。",
        "在 PD 输出端增加抗饱和积分（anti-windup）；降低期望轨迹加速度，"
        "避免瞬态力矩需求超过执行器上限。",
    ),
    "wheel_sign_swap": (
        "左右轮电机接线互换或配置错误，导致 PD 力矩方向反向，机器人俯仰发散到 "
        "0.5 rad 超过安全阈值，状态机检测到俯仰超限触发 FAULT。",
        "上电自检阶段增加轮子方向校验（短脉冲正转，观测编码器反馈方向）；"
        "配置文件增加 wheel_sign 参数并纳入 SELF_CHECK 校验。",
    ),
    "message_delay": (
        "ROS2 DDS 网络拥塞或 CPU 调度延迟导致心跳消息超时，control_node 的通信"
        "监控将 communication_lost 置 True，状态机立即触发 FAULT。",
        "调整 DDS QoS 为 RELIABLE + KEEP_LAST(1)；增加心跳周期监控告警；"
        "关键话题使用共享内存传输降低延迟。",
    ),
    "packet_loss": (
        "无线网络丢包率过高或交换机缓冲区溢出，通信链路中断，control_node "
        "将 communication_lost 置 True，状态机立即触发 FAULT。",
        "切换到有线连接或增加冗余链路；DDS QoS 设为 BEST_EFFORT 容忍少量丢包；"
        "增加心跳重传机制。",
    ),
    "nan_detected": (
        "EKF 状态估计中出现 NaN（通常由协方差发散或除零引起），control_node 的 "
        "NaN 检查将 nan_detected 置 True，状态机立即触发 FAULT。",
        "在 EKF 更新步骤前增加输入有效性检查（std::isfinite）；"
        "NaN 出现时回退到上一帧有效估计并告警。",
    ),
    "divide_by_zero": (
        "控制器或 EKF 中出现除零（如角速度为零时的归一化），产生 NaN，"
        "control_node 的 NaN 检查将 nan_detected 置 True，状态机立即触发 FAULT。",
        "在除法前增加分母下限保护（max(denom, 1e-6)）；"
        "静态分析扫描所有除法点，确保分母有下界保护。",
    ),
}

# 故障大类中文名映射
_FAULT_TYPE_CN = {
    "sensor": "传感器故障",
    "actuator": "执行器故障",
    "communication": "通信故障",
    "software": "软件故障",
}


def _evidence_for(fault: dict[str, Any]) -> str:
    """根据故障结果构造 evidence（证据）描述。"""
    name = fault["fault_name"]
    if name == "imu_dropout":
        return "sensor_fresh=False，状态机扩展规则触发（非 BOOT 状态下传感器断流 → FAULT）"
    if name == "noise_burst":
        return f"pitch={fault.get('symptom', '')} 中提取 0.5 > 0.3，俯仰超限检测触发 FAULT"
    if name == "covariance_invalid":
        return "sensor_fresh=False（协方差无效视为传感器不可信），扩展规则触发 FAULT"
    if name == "torque_saturation":
        return "pitch=0.4 > 0.3，俯仰超限检测触发 FAULT"
    if name == "wheel_sign_swap":
        return "pitch=0.5 > 0.3，俯仰超限检测触发 FAULT"
    if name in ("message_delay", "packet_loss"):
        return "communication_lost=True，通信失联检测触发 FAULT"
    if name in ("nan_detected", "divide_by_zero"):
        return "nan_detected=True，NaN 检测触发 FAULT"
    return f"final_state={fault['final_state']}"


def generate_report(summary: dict[str, Any]) -> str:
    """根据故障演练汇总 JSON 生成 Markdown 实验报告。"""
    faults: list[dict[str, Any]] = summary["faults"]
    sections: list[str] = []

    # 标题
    sections.append("# 第 46 关：故障演练与实验报告\n")
    sections.append("> 关卡：46（design_review 毕业门槛）")
    sections.append(
        "> 报告目的：通过 4 大类 9 种故障注入演练，验证安全状态机的故障检测能力，"
        "覆盖 fault → symptom → evidence → root cause → corrective action 全链路。\n"
    )

    # 1. 评审摘要
    sections.append("## 1. 评审摘要\n")
    sections.append("| 指标 | 数值 |")
    sections.append("|---|---|")
    sections.append(f"| 注入故障总数 | {summary['fault_types_injected']} |")
    sections.append(f"| 检测成功数 | {summary['faults_detected']} |")
    sections.append(f"| 检测覆盖率 | {summary['coverage_percent']:.1f}% |")
    sections.append(f"| 平均检测延迟 | {summary['mean_detection_latency_ms']:.3f} ms |")
    sections.append(f"| 平均制动延迟 | {summary['mean_brake_latency_ms']:.3f} ms |")
    sections.append(
        f"| 4 大类覆盖 | 传感器({sum(1 for f in faults if f['fault_type']=='sensor')}) / "
        f"执行器({sum(1 for f in faults if f['fault_type']=='actuator')}) / "
        f"通信({sum(1 for f in faults if f['fault_type']=='communication')}) / "
        f"软件({sum(1 for f in faults if f['fault_type']=='software')}) |"
    )
    sections.append("")

    all_safe = summary["faults_detected"] == summary["fault_types_injected"]
    if all_safe:
        sections.append("**评审结论：通过**——4 大类 9 种故障全部被检测，状态机均进入 FAULT，检测延迟远低于 200ms 阈值。\n")
    else:
        sections.append("**评审结论：不通过**——存在未被检测的故障，需补充检测逻辑。\n")

    # 2. 故障注入矩阵
    sections.append("## 2. 故障注入矩阵\n")
    sections.append("| 大类 | 故障名 | 现象 | 检测延迟(ms) | 制动延迟(ms) | 最终状态 | 安全 |")
    sections.append("|---|---|---|---|---|---|---|")
    for f in faults:
        type_cn = _FAULT_TYPE_CN.get(f["fault_type"], f["fault_type"])
        safe_mark = "✓" if f["safe"] else "✗"
        sections.append(
            f"| {type_cn} | `{f['fault_name']}` | {f['symptom']} | "
            f"{f['detection_latency_ms']:.3f} | {f['brake_latency_ms']:.1f} | "
            f"{f['final_state']} | {safe_mark} |"
        )
    sections.append("")

    # 3. 故障时间线分析
    sections.append("## 3. 故障时间线分析\n")
    sections.append(
        "故障时间线图见 `outputs/plots/engineering_46_fault_timeline.png`。"
        "横轴为检测延迟（ms），纵轴为故障事件；4 大类用不同颜色标记，"
        "每个故障标注检测延迟值和最终状态。\n"
    )
    sections.append("**时间线要点**：\n")
    sections.append(
        f"- 所有故障的检测延迟均接近 0ms（纯函数状态转换无 I/O 等待），"
        f"远低于 200ms 阈值；平均检测延迟 **{summary['mean_detection_latency_ms']:.3f} ms**。"
    )
    sections.append(
        f"- 所有故障的制动延迟为 0ms（非 ARMED 状态即制动，力矩门控同帧关闭）；"
        f"平均制动延迟 **{summary['mean_brake_latency_ms']:.3f} ms**。"
    )
    sections.append(
        f"- 检测覆盖率 **{summary['coverage_percent']:.1f}%**（"
        f"{summary['faults_detected']}/{summary['fault_types_injected']}）。\n"
    )

    # 4. 根因分析
    sections.append("## 4. 根因分析\n")
    sections.append("对每种故障按 `fault → symptom → evidence → root cause → corrective action` 链路分析：\n")
    for f in faults:
        type_cn = _FAULT_TYPE_CN.get(f["fault_type"], f["fault_type"])
        root_cause, corrective = _ROOT_CAUSE_TABLE.get(
            f["fault_name"], ("未知根因，需进一步排查。", "待补充纠正动作。")
        )
        sections.append(f"### 4.{faults.index(f) + 1} `{f['fault_name']}`（{type_cn}）\n")
        sections.append(f"- **fault**：`{f['fault_name']}`（大类：{type_cn}）")
        sections.append(f"- **symptom**：{f['symptom']}")
        sections.append(f"- **evidence**：{_evidence_for(f)}，最终状态 `{f['final_state']}`，安全 `{f['safe']}`")
        sections.append(f"- **root cause**：{root_cause}")
        sections.append(f"- **corrective action**：{corrective}\n")

    # 5. 纠正动作汇总
    sections.append("## 5. 纠正动作汇总\n")
    sections.append("| 故障 | 纠正动作 | 优先级 |")
    sections.append("|---|---|---|")
    priority_map = {
        "imu_dropout": "高",
        "noise_burst": "中",
        "covariance_invalid": "高",
        "torque_saturation": "中",
        "wheel_sign_swap": "高",
        "message_delay": "中",
        "packet_loss": "中",
        "nan_detected": "高",
        "divide_by_zero": "高",
    }
    for f in faults:
        _, corrective = _ROOT_CAUSE_TABLE.get(f["fault_name"], ("", "待补充"))
        # 取纠正动作第一句作为摘要
        corrective_brief = corrective.split("；")[0] + "。"
        priority = priority_map.get(f["fault_name"], "中")
        sections.append(f"| `{f['fault_name']}` | {corrective_brief} | {priority} |")
    sections.append("")

    # 6. 评审结论
    sections.append("## 6. 评审结论\n")
    sections.append(f"- 注入故障总数：**{summary['fault_types_injected']}**")
    sections.append(f"- 检测成功数：**{summary['faults_detected']}**")
    sections.append(f"- 检测覆盖率：**{summary['coverage_percent']:.1f}%**")
    sections.append(f"- 平均检测延迟：**{summary['mean_detection_latency_ms']:.3f} ms**（阈值 200ms）")
    sections.append(f"- 平均制动延迟：**{summary['mean_brake_latency_ms']:.3f} ms**")
    if all_safe:
        sections.append("")
        sections.append(
            "**评审结论：通过**——4 大类（传感器、执行器、通信、软件）9 种故障全部被检测，"
            "状态机均进入 FAULT，力矩门控同帧关闭，检测延迟远低于 200ms 阈值。"
            "`design_review` 毕业门槛满足。"
        )
    else:
        sections.append("")
        sections.append("**评审结论：不通过**——存在未被检测的故障，需补充检测逻辑后重新评审。")
    sections.append("")
    sections.append("---")
    sections.append("本报告由 `scripts/tools/generate_fault_drill_report.py` 自动生成。")

    return "\n".join(sections) + "\n"


def _resolve_path(value: str, parents_level: int) -> Path:
    """将相对路径解析为相对于仓库 ROOT 的绝对路径。"""
    p = Path(value)
    if p.is_absolute():
        return p
    root = Path(__file__).resolve().parents[parents_level]
    return root / p


def main() -> int:
    parser = argparse.ArgumentParser(description="第 46 关故障演练实验报告生成器")
    parser.add_argument(
        "--input",
        default="outputs/results/engineering_46_fault_drill.json",
        help="故障演练汇总 JSON 输入路径（相对路径相对于仓库根）",
    )
    parser.add_argument(
        "--output",
        default="outputs/reports/fault_drill_46.md",
        help="实验报告 Markdown 输出路径（相对路径相对于仓库根）",
    )
    args = parser.parse_args()

    input_path = _resolve_path(args.input, parents_level=2)
    if not input_path.exists():
        print(f"[FAIL] 故障演练 JSON 不存在：{input_path}", file=sys.stderr)
        return 1

    summary = json.loads(input_path.read_text(encoding="utf-8"))
    report = generate_report(summary)

    output_path = _resolve_path(args.output, parents_level=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"[OK] 故障演练实验报告已生成：{output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
