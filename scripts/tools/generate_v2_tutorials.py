from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.manifest import load_course_manifest


FORMULAS = {
    "00": "能力 = 可解释知识 + 可复现实验 + 可审查证据",
    "01": "数组形状：x.shape = (样本数, 特征数)",
    "02": "可复现实验 = 代码 commit + 配置 + seed + 环境 + 原始结果",
    "03": "p_world = R_world_body p_body + t_world_body",
    "04": "x_dot = f(x, u)，线性化后 delta_x_dot ≈ A delta_x + B delta_u",
    "05": "y_k = x_k + n_k，n_k 表示测量噪声",
    "06": "q_{k+1}, v_{k+1} = step(q_k, v_k, u_k, dt)",
    "07": "v2 模型契约：nq=13, nv=12, nu=6",
    "08": "单位四元数满足 qw^2 + qx^2 + qy^2 + qz^2 = 1",
    "09": "tau_wheel = clip(tau_cmd, -1, 1) N·m",
    "10": "|F_t| <= mu F_n",
    "11": "RobotSpec -> model + mapping + control semantics",
    "12": "u = K e：误差经过反馈后生成纠偏动作",
    "13": "u = Kp e + Ki integral(e) + Kd de/dt",
    "14": "M(q) q_ddot + C(q,q_dot)q_dot + g(q) = S^T tau + J^T lambda",
    "15": "s^2 + 2 zeta omega_n s + omega_n^2 = 0",
    "16": "x_dot = A x + B u，y = C x + D u",
    "17": "J = sum(x^T Q x + u^T R u)，u = -Kx",
    "18": "tau_left/right = balance_torque ± yaw_torque",
    "19": "theta_k = alpha(theta_{k-1}+omega dt)+(1-alpha)theta_acc",
    "20": "K_k = P^- H^T (H P^- H^T + R)^-1",
    "21": "f(x) ≈ f(x_hat) + F(x-x_hat)",
    "22": "theta_hat = argmin ||Phi theta - y||^2",
    "23": "min 0.5 x^T H x + f^T x, s.t. Ax <= b",
    "24": "在预测时域内最小化状态误差和控制代价，并满足输入约束",
    "25": "step(a) -> observation, reward, terminated, truncated, info",
    "26": "r = sum_i w_i r_i，终止条件独立于奖励",
    "27": "grad J(theta) = E[grad log pi_theta(a|s) A(s,a)]",
    "28": "L_clip = E[min(r_t A_t, clip(r_t,1-epsilon,1+epsilon)A_t)]",
    "29": "p_sim(phi) 覆盖真实参数 phi_real 的可信区间",
    "30": "u = clip(u_classic + beta u_rl)",
    "31": "gap = metric_real - metric_sim，并报告置信区间",
    "32": "语言任务 -> 感知/规划 -> 安全速度 -> 低层力矩",
    "33": "depth(u,v) + camera model -> target distance and offset",
    "34": "instruction -> {verb, target_color, stop_at_target}",
    "35": "episode = {rgb, depth, proprioception, action, instruction, timestamp, metadata}",
    "36": "L_BC = mean ||pi_theta(o,l) - a_expert||^2",
    "37": "success rate, collision rate, stopping error, max pitch, latency",
    "38": "tau = [2, 0.8, 3, 0.8] dot [e_x, e_v, e_pitch, e_pitch_rate]",
    "39": "source -> target -> dependency -> test",
    "40": "/imu -> control_node(100 Hz) -> /wheel_torque",
    "41": "jitter = actual_period - desired_period",
    "42": "evidence = timestamp + state + action + config + commit",
    "43": "BOOT -> SELF_CHECK -> DISARMED -> ARMED -> FAULT",
    "44": "requirement -> interface -> risk -> verification evidence",
    "45": "system score = min(code, physics, robustness, realtime, safety, docs)",
    "46": "fault -> symptom -> evidence -> root cause -> corrective action",
    "47": "claim -> design reason -> experiment evidence -> limitation",
    "H01": "BOM item = model + count + source + substitute + license evidence",
    "H02": "clearance = hole_size - shaft_size",
    "H03": "P = U I，首次上电使用限流降低故障能量",
    "H04": "tau ≈ Kt Iq，FOC 用电角度控制 q 轴电流",
    "H05": "omega = unwrap(theta_k-theta_{k-1}) / dt",
    "H06": "theta_k = alpha(theta_{k-1}+omega dt)+(1-alpha)theta_acc",
    "H07": "servo_count -> joint_angle -> leg_height",
    "H08": "tau_safe = estop * rate_limit(low_pass(tau_raw))",
    "H09": "valid = sequence_new AND timestamp_fresh AND value_bounded",
    "H10": "simulation distribution should cover measured hardware uncertainty",
}


STAGE_INTUITION = {
    "0": "先把数学和工具变成可运行的小实验。每个抽象符号都要能在 Upkie 数据里找到对应量。",
    "1": "仿真不是动画播放器，而是一组状态、约束、接触和执行器语义。模型物理错了，后续算法越强越会放大错误。",
    "2": "控制器像持续扶住扫把的手：看偏差、预测趋势、给出有限动作，并承认工作范围。",
    "3": "估计与优化解决的是看不准、模型不准和动作受限；结果必须带不确定性和约束。",
    "4": "学习算法不会自动理解物理。环境、奖励、终止、seed 和基线共同决定实验是否可信。",
    "5": "VLA 负责把语言和视觉目标变成高层任务，低层稳定、限幅和急停始终由确定性安全控制承担。",
    "6": "工程部署关注接口、时间、故障和复现。平均能跑不等于最坏情况安全。",
    "7": "毕业项目不是功能拼盘，而是一条从需求到证据、从故障到复盘的完整工程链。",
    "H": "硬件把每个软件假设变成电流、温度、公差和风险；先低能量验证，再逐级闭环。",
}

CURATED_CHAPTERS = {"00", "01", "02", "03", "04", "05", "11", "13", "14", "15", "16", "18", "20", "21", "22", "23", "27", "31", "H01"}


def render(chapter: dict, previous: str | None, next_id: str | None) -> str:
    ready = chapter["status"] == "ready"
    status = "可执行" if ready else "规划中"
    expected = "生成测试、日志和可视化证据。" if ready else "明确拒绝验收并提示本关尚未建设完成。"
    prerequisite = "无；这是课程入口。" if previous is None else f"完成 `{previous}` 的证据验收，或通过先修诊断。"
    next_text = "进入毕业答辩与持续迭代。" if next_id is None else f"下一关 `{next_id}` 会把本关结果作为输入，而不是重新开始。"
    formula = FORMULAS[chapter["id"]]
    return f"""# {chapter['id']} {chapter['title']}

> 建设状态：{status}  
> 阶段：{chapter['stage_title']}  
> 作品集目录：`{chapter['portfolio']}`

## 岗位任务

{chapter['task']} 你需要交付的不只是运行截图，而是可解释设计、固定配置、量化指标和失败分析。

## 学习目标

- 能理解：用自己的话说明“{chapter['title']}”解决什么工程问题。
- 能推导：从假设和单位出发解释本关核心关系，不跳过符号含义。
- 能实现：运行检查点，保存测试、日志、图表或视频三类证据。

## 前置关卡

{prerequisite}

## 先观察现象

先看错误基线：关闭或故意破坏本关关键环节，记录机器人姿态、接触、动作和日志最先出现的异常。不要先读结论；先写下三个观察，再提出一个可被数据推翻的原因假设。

## 直觉与概念

{STAGE_INTUITION[chapter['stage']]}

本关核心问题是：**如何用可测量证据判断“{chapter['title']}”已经达到岗位可用，而不是只在一次演示中碰巧工作？**

## 教科书级展开

核心关系：

```text
{formula}
```

阅读公式或契约时按七层顺序检查：直觉、符号、物理意义、设计动机、逐步推导、数值算例、代码映射。所有物理量使用 SI 单位；离散时间量必须说明采样周期。该关系默认模型字段、坐标方向和执行器语义与 `configs/robot/upkie.json` 一致。

适用范围是当前关卡声明的平衡点、约束和数据分布。接触丢失、传感器过期、动作饱和、输入超出训练分布或公式假设不成立时，必须进入诊断/安全路径，不能继续外推。

数值算例从配置中取一组实际参数，手算一个时间步，再与代码输出逐项对齐。若两者不同，优先检查单位、左右轮方向、平衡点和数组顺序。

## 动手检查点

```powershell
{chapter['command']}
```

预期结果：{expected} 命令必须从项目根目录运行，原始输出写入 `outputs/`，不能手工改写成“更好看”的结果。

## 可视化证据

至少生成 `{chapter['visualizations'][0]}`。控制类优先画状态与力矩时间序列；学习类画奖励分解和评估分布；感知类保留 RGB、深度与检测叠加；工程类画延迟分布和故障时间线。

视觉只回答“发生了什么”，日志给出时间与数值，测试负责可重复判定；三者缺一不可。

## 故障诊断挑战

故意制造一个与“{chapter['title']}”直接相关的错误。按“现象 -> 第一处异常证据 -> 根因假设 -> 最小验证 -> 修复后对比”记录，不允许通过放宽阈值隐藏失败。

## 三档任务

- 基础任务：在固定 seed 下通过本关检查点，并解释每个输出字段。
- 岗位挑战：加入噪声、延迟、扰动或边界输入，报告成功与失败分布。
- 开放探索：替换一种方法或参数，先写假设，再用同一评估协议公平比较。

## 复盘与面试

1. 本关最关键的假设是什么？失效时第一个可观测信号是什么？
2. 为什么当前接口、单位和限幅这样设计？有哪些可替代方案？
3. 你能用哪三份证据证明结果可复现？
4. 如果指标退化 20%，你先查模型、数据、控制还是部署？为什么？

## 下一关

{next_text}
"""


def main() -> None:
    chapters = load_course_manifest()["chapters"]
    for index, chapter in enumerate(chapters):
        previous = chapters[index - 1]["id"] if index else None
        next_id = chapters[index + 1]["id"] if index + 1 < len(chapters) else None
        path = ROOT / chapter["tutorial"]
        if chapter["id"] in CURATED_CHAPTERS and path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(chapter, previous, next_id), encoding="utf-8")
    print(f"已生成 {len(chapters)} 个 v2 课程关卡。")


if __name__ == "__main__":
    main()
