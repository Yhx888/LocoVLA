# 43 部署、安全与故障恢复

> 建设状态：可执行  
> 阶段：工程部署  
> 作品集目录：`outputs/portfolio/43`

## 岗位任务

实现五状态安全状态机（BOOT→SELF_CHECK→DISARMED→ARMED→FAULT）纯函数，集成 /estop、/arm、/reset 服务和 /safety_state 话题，通过 15 个安全状态机 gtest 和 5 种故障注入演练验证安全状态转换和力矩门控。你需要交付的不只是运行截图，而是可解释设计、固定配置、量化指标和失败分析。

## 学习目标

- 能理解：用自己的话说明"安全状态机"解决什么工程问题——故障不可避免，关键在于检测和恢复。
- 能推导：从五状态转换规则和 PITCH_SAFETY_LIMIT_RAD=0.3 出发，解释力矩门控为什么只在 ARMED 状态输出力矩。
- 能实现：运行检查点，保存测试、日志、图表三类证据，并能解释 5 种故障注入的检测路径。

## 前置关卡

完成 `42` 的证据验收，或通过先修诊断。第 42 关建立了统一日志契约（含 `safety_flag` 字段），本关把该字段升级为完整的五状态安全状态机。

## 先观察现象

先看错误基线：关闭或故意破坏本关关键环节，记录机器人姿态、接触、动作和日志最先出现的异常。不要先读结论；先写下三个观察，再提出一个可被数据推翻的原因假设。

**观察示例**：
1. 注入 IMU 断流故障后，状态机从 ARMED 直接跳到 FAULT，力矩立即归零。
2. 注入左右轮符号互换故障后，pitch 发散到 0.5 rad（超过 0.3 rad 安全阈值），状态机进入 FAULT。
3. FAULT 状态只能通过 /reset 服务人工复位，不能自动恢复——这是安全设计的刻意选择。

## 直觉与概念

<!-- upkie-animation:43-core -->

工程部署关注接口、时间、故障和复现。平均能跑不等于最坏情况安全。

本关核心问题是：**如何用可测量证据判断"安全状态机"已经达到岗位可用，而不是只在一次演示中碰巧工作？**

### 为什么需要安全状态机

机器人控制系统在真实运行中会遭遇各种故障：传感器断流、通信失联、CPU 过载、俯仰超限、急停触发。如果没有系统化的安全状态机：

- **故障不可检测**：IMU 停止发布数据后，控制节点继续用旧数据计算力矩，机器人失控翻倒。
- **故障不可恢复**：一次 CPU 过载导致通信中断后，系统卡死在故障状态，无法通过标准流程复位。
- **力矩不可门控**：即使检测到故障，控制节点仍输出力矩，可能导致更严重的机械损坏。

安全状态机的本质是：**把"故障检测、力矩门控、人工复位"从临时补丁变成可测试的纯函数**。五状态不是随便选的，而是覆盖了"上电自检、待命、工作、故障、复位"的完整生命周期。

## 教科书级展开

### 五状态转换规则

BOOT ──> SELF_CHECK ──> DISARMED ──> ARMED
↓
(故障检测)
↓
FAULT
↑
(人工复位 /reset)
|
BOOT ──> SELF_CHECK ──> ...

各状态语义：

1. **BOOT（上电）**：节点刚启动，尚未读取任何传感器。仅做初始化，不输出力矩。
2. **SELF_CHECK（自检）**：检查传感器是否新鲜、姿态是否在安全范围。传感器就绪后推进到 DISARMED。
3. **DISARMED（待命）**：系统就绪但未激活。等待 /arm 服务指令，收到后推进到 ARMED。
4. **ARMED（激活）**：唯一允许输出 PD 力矩的状态。控制循环正常运行，力矩正常输出。
5. **FAULT（故障）**：检测到任何故障后进入。力矩立即归零（力矩门控关闭）。只能通过 /reset 服务人工复位到 BOOT。

阅读状态机时按七层顺序检查：

1. **直觉**：五个状态覆盖"启动→自检→待命→工作→故障"全生命周期，FAULT 是单点汇聚。
2. **符号**：`SafetyState` 枚举值 0-4 分别对应 BOOT/SELF_CHECK/DISMARED/ARMED/FAULT，与 C++ `SafetyState` 枚举一一对应。
3. **物理意义**：BOOT 对应"刚通电"、SELF_CHECK 对应"传感器预热"、DISARMED 对应"等待操作员指令"、ARMED 对应"控制律运行"、FAULT 对应"紧急停止"。
4. **设计动机**：FAULT 只能人工复位，避免"自动恢复后立即再次故障"的振荡。力矩门控只在 ARMED 开启，确保任何非工作状态都不会意外输出力矩。
5. **逐步推导**：转换优先级自顶向下——(1) reset 优先：FAULT + reset → BOOT；(2) 故障触发：NaN/通信失联/急停/俯仰超限 → FAULT；(3) 传感器断流：非 BOOT 状态下 sensor_fresh=False → FAULT；(4) 正常推进：BOOT→SELF_CHECK→DISARMED→ARMED。
6. **数值算例**：起始状态 ARMED，注入 pitch=0.5 rad（超过 PITCH_SAFETY_LIMIT_RAD=0.3）→ `abs(0.5) > 0.3` 为真 → 进入 FAULT，力矩归零。
7. **代码映射**：`scripts/tools/run_safety_fault_injection.py` 的 `transition` 函数复现 C++ `safety_state_machine.cpp` 的纯函数逻辑，`is_armed` 函数实现力矩门控。

### PITCH_SAFETY_LIMIT_RAD = 0.3

俯仰安全阈值 0.3 rad（约 17.2°）。当 `abs(pitch_rad) > 0.3` 时，状态机进入 FAULT。

选择 0.3 rad 的原因：
- Upkie 的 PD 控制器在小角度（<0.2 rad）下线性化有效，0.3 rad 留 50% 余量。
- 超过 0.3 rad 时，机器人已接近失控边缘，继续输出力矩可能加剧发散。
- 与 C++ `PITCH_SAFETY_LIMIT_RAD` 常量一致，确保 Python 故障演练和 C++ 测试用同一阈值。

### 力矩门控

```python
def is_armed(state: SafetyState) -> bool:
    """是否允许输出 PD 力矩（仅 ARMED 状态允许）。"""
    return state == SafetyState.ARMED
```

力矩门控是安全状态机的物理执行层：只有 `is_armed(state)` 返回 True 时，控制节点才将 PD 力矩写入 `/wheel_torque` 话题；否则输出零力矩。这确保了：

- BOOT/SELF_CHECK/DISARMED 状态下机器人不会意外移动。
- FAULT 状态下力矩立即归零，即使 PD 控制器仍在计算（计算结果被门控丢弃）。
- 故障检测到力矩归零的延迟为 0ms（同一帧内完成状态转换和门控）。

### /estop、/arm、/reset 服务和 /safety_state 话题

/estop   (服务)  触发急停：任意状态 → FAULT
/arm     (服务)  激活控制：DISARMED + arm_requested → ARMED
/reset   (服务)  人工复位：FAULT + reset_requested → BOOT
/safety_state (话题)  发布当前安全状态（100Hz，与控制循环同频），供监控和日志记录

服务接口的设计原则：
- /estop 优先级最高，任何状态都能触发 FAULT。
- /arm 只在 DISARMED 状态有效，防止从 BOOT/SELF_CHECK 直接跳到 ARMED。
- /reset 只在 FAULT 状态有效，防止正常运行时误触发复位。

适用范围是当前关卡声明的平衡点、约束和数据分布。接触丢失、传感器过期、动作饱和、输入超出训练分布或公式假设不成立时，必须进入诊断/安全路径，不能继续外推。

## 动手检查点

### 1. 运行安全故障演练实验

```powershell
python scripts/run_engineering_lab_43.py --output-root outputs --seed 0
```

该命令调用 `scripts/tools/run_safety_fault_injection.py` 注入 5 种故障（IMU 断流、时间戳倒退、左右轮符号互换、CPU 过载、高层命令失联），生成故障演练 JSON，合并 C++ 端 GoogleTest 统计，最终写出结果契约 `outputs/results/engineering_43.json` 和 portfolio 报告 `outputs/portfolio/43/engineering_43_report.md`。

### 2. 运行关卡自动验收

```powershell
python scripts/course_checkpoint.py --chapter 43
```

命令必须从项目根目录运行，原始输出写入 `outputs/`，不能手工改写成"更好看"的结果。

### 3. 运行 Python 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_safety.py
```

测试覆盖：故障演练脚本可运行、全部 5 种故障最终进入 FAULT、故障数为 5、平均检测延迟 ≤ 200ms、非 ARMED 状态制动延迟为 0、编排脚本写出结果契约、portfolio 报告存在。

## 可视化证据

本关的 portfolio 报告 `outputs/portfolio/43/engineering_43_report.md` 包含：

1. **安全分析表**：5 种故障的检测信号、状态机动作、起始状态、最终状态。
2. **故障树**：从任意工作状态到 FAULT 的 5 条路径，以及 FAULT 通过 /reset 复位的路径。
3. **故障演练记录**：5 种故障的检测延迟（ms）、制动延迟（ms）、安全标记（✓/✗）。

故障时间线回答"每种故障多久被检测到、检测后力矩多久归零"。本关 5 种故障全部安全（最终状态均为 FAULT），平均检测延迟 0ms（纯函数状态转换无延迟），平均制动延迟 0ms（非 ARMED 状态即制动）。

视觉只回答"发生了什么"，日志给出时间与数值，测试负责可重复判定；三者缺一不可。

## 故障诊断挑战

**场景**：注入 IMU 断流故障，确认状态机进入 FAULT。

**现象**：IMU 在 500ms 内停止发布数据，控制节点继续运行但状态机输出 FAULT。

**第一处异常证据**：`sensor_fresh=False`，状态机扩展规则触发：非 BOOT 状态下 sensor_fresh=False → FAULT。

**根因假设**：`transition` 函数第 3 优先级规则——传感器断流扩展规则（对应 control_node 的传感器新鲜度监控）在非 BOOT 状态下将 sensor_fresh=False 映射为 FAULT。

**最小验证**：运行 `tests/test_safety.py::test_all_faults_safe`，确认 `imu_dropout` 故障的 `final_state` 为 `FAULT`，`safe` 为 `True`。

**修复后对比**：恢复 IMU 数据发布后，状态机需要通过 /reset 服务人工复位到 BOOT，再经 SELF_CHECK → DISARMED → ARMED 重新激活。

按"现象 -> 第一处异常证据 -> 根因假设 -> 最小验证 -> 修复后对比"记录，不允许通过放宽阈值隐藏失败。

## 三档任务

- **基础任务**：在固定 seed 下通过本关检查点（`tests/test_safety.py` 全部通过 + 15 个 gtest 零失败），并解释五状态转换规则的优先级。
- **岗位挑战**：运行 5 种故障注入演练（IMU 断流、时间戳倒退、左右轮符号互换、CPU 过载、高层命令失联），报告每种故障的检测延迟、制动延迟和最终状态。本关 5 种故障全部安全，平均检测延迟 0ms。
- **开放探索**：添加一种新故障类型（如 `battery_low`），先写假设"该故障应触发 WARNING 而非 FAULT"，再修改 `SafetyInput` 和 `transition` 函数，用同一评估协议验证假设。

## 复盘与面试

1. 本关最关键的假设是什么？失效时第一个可观测信号是什么？
   - 关键假设：五状态机能覆盖所有故障场景且 FAULT 是单点汇聚。失效时第一个信号是 /safety_state 话题发布 FAULT（力矩门控关闭）。

2. 为什么当前接口、单位和限幅这样设计？有哪些可替代方案？
   - PITCH_SAFETY_LIMIT_RAD=0.3 rad 留 50% 余量。替代方案：用动态阈值（根据速度调整），但会增加状态机复杂度且难以测试。

3. 你能用哪三份证据证明结果可复现？
   - 结果契约 `engineering_43.json`（含 5 种故障的 metrics）、故障演练 JSON `engineering_43_fault_injection.json`、portfolio 报告（安全分析表 + 故障树 + 演练记录）。

4. 如果指标退化 20%（如检测延迟从 0ms 升到 40ms），你先查模型、数据、控制还是部署？为什么？
   - 先查部署。检测延迟取决于状态机纯函数的执行时间，正常应接近 0ms。退化到 40ms 说明 CPU 调度或内存分配异常，属于部署环境问题。

## 下一关

下一关 `44` 会把本关的安全状态机和第 42 关的日志契约集成到系统设计中，进入岗位毕业项目阶段。
