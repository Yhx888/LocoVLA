# 46 故障演练与实验报告

> 建设状态：可执行  
> 阶段：岗位毕业项目（design_review 门槛）  
> 作品集目录：`outputs/portfolio/46`

## 岗位任务

完成《故障演练与实验报告》岗位任务：在第 43 关安全状态机基础上，注入 4 大类（传感器、执行器、通信、软件）共 9 种故障，生成故障时间线图和实验报告，按 `fault → symptom → evidence → root cause → corrective action` 链路完成根因分析。你需要交付的不只是运行截图，而是可解释设计、固定配置、量化指标和失败分析。

## 学习目标

- 能理解：用自己的话说明"故障演练"解决什么工程问题——验证而非假设，安全状态机必须在故障注入下被证明有效。
- 能推导：从 4 大类故障的检测信号出发，解释 `fault → symptom → evidence → root cause → corrective action` 链路每一步的输入和输出。
- 能实现：运行检查点，保存测试、日志、图表三类证据，并能解释 9 种故障的检测路径和纠正动作。

## 前置关卡

完成 `45` 的证据验收，或通过先修诊断。第 45 关的综合毕业项目为本关提供了系统级视角，本关在其基础上聚焦故障注入与实验报告的工程方法论。

## 先观察现象

先看错误基线：关闭或故意破坏本关关键环节，记录机器人姿态、接触、动作和日志最先出现的异常。不要先读结论；先写下三个观察，再提出一个可被数据推翻的原因假设。

**观察示例**：
1. 注入 IMU 断流故障后，`sensor_fresh=False`，状态机从 ARMED 立即跳到 FAULT，力矩归零。
2. 注入 NaN 故障后，`nan_detected=True`，状态机在第 2 优先级就拦截故障，进入 FAULT。
3. 注入左右轮符号互换故障后，pitch 发散到 0.5 rad（超过 0.3 rad 安全阈值），俯仰超限检测触发 FAULT。

## 直觉与概念

<!-- upkie-animation:46-core -->

毕业项目不是功能拼盘，而是一条从需求到证据、从故障到复盘的完整工程链。

本关核心问题是：**如何用可测量证据判断"安全状态机"已经达到岗位可用，而不是只在一次演示中碰巧工作？**

### 为什么需要故障演练（验证而非假设）

工程中有一个反直觉的原则：**安全系统不能用"没出过事"来证明安全，只能用"故意搞破坏后仍能保护"来证明安全**。这就是故障演练（fault injection drill）的本质。

如果只做正向测试（"正常输入→正常输出"），会遗漏两类致命问题：
- **检测逻辑死区**：状态机的某个故障分支从未被执行过，可能隐藏 bug。
- **恢复路径缺陷**：故障检测后力矩没有真正归零，或者复位流程卡死。

故障演练的工程价值在于：把"假设安全"变成"证据安全"。4 大类故障覆盖了机器人系统的主要失效模式：

1. **传感器故障**：感知层失效（IMU 断流、噪声、协方差发散）。
2. **执行器故障**：执行层失效（力矩饱和、方向错误）。
3. **通信故障**：链路层失效（延迟、丢包）。
4. **软件故障**：计算层失效（NaN、除零）。

## 教科书级展开

### 核心链路：fault → symptom → evidence → root cause → corrective action

fault（故障）         注入的具体故障，如 IMU 断流、NaN
↓
symptom（现象）       故障引起的可观测现象，如 pitch 发散、sensor_fresh=False
↓
evidence（证据）      状态机的检测信号和最终状态，如 final_state=FAULT
↓
root cause（根因）     故障的物理或软件根因，如 USB 连接松动、EKF 协方差发散
↓
corrective action     纠正动作，如增加心跳看门狗、协方差重置逻辑

阅读这条链路时按七层顺序检查：

1. **直觉**：每个故障从注入到检测到纠正，形成闭环。
2. **符号**：`fault_type`（大类）、`fault_name`（具体故障）、`symptom`（现象）、`detection_latency_ms`（检测延迟）、`final_state`（最终状态）、`safe`（是否进入 FAULT）。
3. **物理意义**：4 大类对应感知、执行、链路、计算四层失效模式，覆盖机器人系统的主要风险面。
4. **设计动机**：故障演练不是一次性测试，而是可重复的回归基线——每次代码变更后重跑，确保安全逻辑不退化。
5. **逐步推导**：注入故障 → 状态机 `transition` 函数评估输入 → 命中故障分支 → 返回 FAULT → 力矩门控关闭 → 记录检测延迟和最终状态。
6. **数值算例**：起始状态 ARMED，注入 `pitch=0.5`（超过 `PITCH_SAFETY_LIMIT_RAD=0.3`）→ `abs(0.5) > 0.3` 为真 → 进入 FAULT，检测延迟 0ms，制动延迟 0ms。
7. **代码映射**：`scripts/tools/run_fault_drill.py` 的 `transition` 函数复现 C++ `safety_state_machine.cpp` 的纯函数逻辑，`_make_result` 函数构造每个故障的演练结果。

### 4 大类 9 种故障

| 大类 | 故障名 | 现象 | 检测信号 |
|---|---|---|---|
| 传感器 | `imu_dropout` | IMU 断流 500ms | `sensor_fresh=False` |
| 传感器 | `noise_burst` | 噪声突增 pitch=0.5 | `abs(pitch) > 0.3` |
| 传感器 | `covariance_invalid` | 协方差无效 | `sensor_fresh=False` |
| 执行器 | `torque_saturation` | 力矩饱和 pitch=0.4 | `abs(pitch) > 0.3` |
| 执行器 | `wheel_sign_swap` | 轮符号互换 pitch=0.5 | `abs(pitch) > 0.3` |
| 通信 | `message_delay` | 消息延迟 | `communication_lost=True` |
| 通信 | `packet_loss` | 丢包 | `communication_lost=True` |
| 软件 | `nan_detected` | NaN | `nan_detected=True` |
| 软件 | `divide_by_zero` | 除零→NaN | `nan_detected=True` |

### 检测机制

状态机 `transition` 函数的故障检测优先级（自顶向下）：

1. **reset 优先**：FAULT + reset → BOOT（人工复位）
2. **NaN / 通信失联 / 急停**：任意状态 → FAULT
3. **俯仰超限**：`abs(pitch) > 0.3` → FAULT
4. **传感器断流**：非 BOOT 状态下 `sensor_fresh=False` → FAULT

4 大类故障的检测路径：
- 传感器故障 → 命中优先级 2（NaN）或 3（俯仰超限）或 4（传感器断流）
- 执行器故障 → 命中优先级 3（俯仰超限，因为执行器故障导致姿态发散）
- 通信故障 → 命中优先级 2（communication_lost）
- 软件故障 → 命中优先级 2（nan_detected）

### 纠正动作

每种故障的纠正动作分三类：
- **硬件层**：如 USB 连接加固、增加硬件滤波、冗余链路。
- **软件层**：如心跳看门狗、协方差重置、抗饱和积分、除法下限保护。
- **流程层**：如上电自检增加轮子方向校验、配置参数纳入 SELF_CHECK。

适用范围是当前关卡声明的平衡点、约束和数据分布。接触丢失、传感器过期、动作饱和、输入超出训练分布或公式假设不成立时，必须进入诊断/安全路径，不能继续外推。

## 动手检查点

### 1. 运行综合故障演练实验

```powershell
python scripts/run_engineering_lab_46.py --output-root outputs
```

该命令调用 `scripts/tools/run_fault_drill.py` 注入 4 大类 9 种故障，生成故障演练 JSON（`outputs/results/engineering_46_fault_drill.json`）和故障时间线图（`outputs/plots/engineering_46_fault_timeline.png`），再调用 `scripts/tools/generate_fault_drill_report.py` 生成实验报告（`outputs/reports/fault_drill_46.md`），最终写出结果契约 `outputs/results/engineering_46.json` 和 portfolio 报告 `outputs/portfolio/46/engineering_46_report.md`。

预期输出：9 种故障全部检测成功（`faults_detected == fault_types_injected == 9`），检测覆盖率 100%，平均检测延迟远低于 200ms 阈值。

### 2. 运行 Python 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_fault_drill.py
```

测试覆盖：故障演练脚本可运行、4 大类故障全覆盖、所有故障被检测、平均检测延迟 ≤ 200ms、故障时间线图存在、编排脚本写出结果契约且 passed=True、实验报告存在。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 46
```

## 可视化证据

本关的故障时间线图 `outputs/plots/engineering_46_fault_timeline.png` 包含：

1. **横轴**：检测延迟（ms），纵轴：故障事件（按 fault_name 排列）。
2. **4 大类颜色编码**：传感器（蓝）、执行器（橙）、通信（绿）、软件（红）。
3. **每个故障标注**：检测延迟值、最终状态、安全标记（OK/FAIL）。
4. **200ms 阈值线**：红色虚线，所有故障检测延迟均远低于此线。

实验报告 `outputs/reports/fault_drill_46.md` 包含评审摘要、故障注入矩阵、故障时间线分析、根因分析（9 种故障的 root cause）、纠正动作汇总和评审结论六部分。

视觉只回答"发生了什么"，日志给出时间与数值，测试负责可重复判定；三者缺一不可。

## 故障诊断挑战

**场景**：注入 NaN 故障，确认状态机进入 FAULT。

**现象**：EKF 状态估计中出现 NaN（通常由协方差发散或除零引起），控制节点继续运行但状态机输出 FAULT。

**第一处异常证据**：`nan_detected=True`，状态机第 2 优先级规则触发：NaN 检测 → FAULT。

**根因假设**：`transition` 函数第 2 优先级规则——`if inp.nan_detected or inp.communication_lost or not inp.estop_released: return SafetyState.FAULT`——在 NaN 检测为真时立即返回 FAULT，力矩门控同帧关闭。

**最小验证**：运行 `tests/test_fault_drill.py::test_all_faults_detected`，确认 `nan_detected` 和 `divide_by_zero` 两种故障的 `final_state` 均为 `FAULT`，`safe` 均为 `True`。

**修复后对比**：在 EKF 更新步骤前增加 `std::isfinite` 检查，NaN 出现时回退到上一帧有效估计并告警；修复后重新运行故障演练，确认 NaN 故障仍被检测（状态机是最后一道防线，EKF 修复是预防措施）。

按"现象 -> 第一处异常证据 -> 根因假设 -> 最小验证 -> 修复后对比"记录，不允许通过放宽阈值隐藏失败。

## 三档任务

- **基础任务**：在固定 seed 下通过本关检查点（`tests/test_fault_drill.py` 全部 7 个测试通过），并解释 4 大类故障的检测优先级。
- **岗位挑战**：运行 4 大类 9 种故障注入演练，报告每种故障的检测延迟、制动延迟和最终状态，确认检测覆盖率 100%。本关 9 种故障全部安全，平均检测延迟 0ms。
- **开放探索**：添加一种新故障类型（如 `battery_low` 电池低电量），先写假设"该故障应触发 WARNING 而非 FAULT"，再修改 `SafetyInput` 和 `transition` 函数，用同一评估协议验证假设。

## 复盘与面试

1. 本关最关键的假设是什么？失效时第一个可观测信号是什么？
   - 关键假设：4 大类故障覆盖了机器人系统的主要失效模式，且状态机的 4 级优先级检测能拦截所有故障。失效时第一个信号是 `/safety_state` 话题发布 FAULT（力矩门控关闭）。

2. 为什么当前接口、单位和限幅这样设计？有哪些可替代方案？
   - `PITCH_SAFETY_LIMIT_RAD=0.3` rad 留 50% 余量。4 大类分类对应感知/执行/链路/计算四层。替代方案：用 FMEA 严重度动态调整阈值，但会增加状态机复杂度且难以测试。

3. 你能用哪三份证据证明结果可复现？
   - 结果契约 `engineering_46.json`（含 9 种故障的 metrics）、故障演练 JSON `engineering_46_fault_drill.json`、实验报告 `fault_drill_46.md`（含根因分析和纠正动作）。

4. 如果指标退化 20%（如检测延迟从 0ms 升到 40ms），你先查模型、数据、控制还是部署？为什么？
   - 先查部署。检测延迟取决于状态机纯函数的执行时间，正常应接近 0ms。退化到 40ms 说明 CPU 调度或内存分配异常，属于部署环境问题，而非模型或控制逻辑问题。

## 下一关

下一关 `47` 会把本关的故障演练结果作为输入，而不是重新开始。
