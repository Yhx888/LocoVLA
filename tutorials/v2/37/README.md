# 37 闭环泛化与失败分析

> 建设状态：可执行
> 阶段：应用型 VLA
> 作品集目录：`outputs/portfolio/37`

## 岗位任务

你的交付物是一份"系统级评估与失败分析报告"：对关卡 36 训练的行为克隆策略进行全面的闭环评估，量化泛化能力，并深入分析至少三种失败模式的根因。面试官会问："你的系统在什么条件下会失败？失败时第一个可观测信号是什么？你怎样设计监控来提前预警？"

具体交付：

1. 一张评估报告：3 个三色导航任务、1 个紧急停止任务和 9 个固定验收指标，加上逐任务详细结果。
2. 三种失败模式的详细分析：每种包含触发条件、第一个异常信号、根因和修复建议。
3. 一段运行时异常检测逻辑说明：在策略运行时如何通过 `VLASafetyController` 的 `safety_interventions` 计数器检测异常。

## 学习目标

- **能理解**：解释"泛化"在具身系统中的含义——不只是在新数据上表现好，而是在新的物理条件和任务条件下仍然安全和有效。
- **能推导**：从统计学习的泛化界出发，分析 BC 策略在分布外场景下的性能退化上界。
- **能实现**：加载第 36 关 BC checkpoint 调用 `evaluate_vla_tasks()`，解读真实 MuJoCo 闭环的导航、碰撞、停车、姿态、策略调用和紧急停止指标。

## 前置关卡

完成 `36`（行为克隆与视觉语言融合）的证据验收。你需要理解：

- BC 策略的输入/输出接口
- 开环 vs 闭环误差的区别
- 分布偏移问题的理论背景

## 先观察现象

**错误基线实验**：只在训练分布内的场景中评估策略。

```python
# 只在"正前方红色目标"上测试（与训练数据相同）
for ep in range(20):
    success = evaluate("前往红色目标并停车", target_pos=[1.0, 0.0])
    results.append(success)

mean_success = np.mean(results)
print(f"分布内成功率: {mean_success:.0%}")
# 预期: 90%+ (因为训练数据覆盖了这个场景)
```

**然后**：在训练分布外的场景测试。

```python
# "蓝色目标"（训练中可能覆盖不足）
success_ood = evaluate("前往蓝色目标并停车", target_pos=[-1.0, 0.0])
print(f"分布外成功率: {success_ood:.0%}")
# 预期: 大幅下降（可能 < 30%）
```

**记录观察**：分布内性能好不代表分布外也好——这就是泛化问题。

## 直觉与概念

<!-- upkie-animation:37-intuition -->

### 泛化的三个层次

**1. 数据泛化**：在新的随机种子下表现好（同一场景，不同扰动）

训练: 红色目标在 (1.0, 0.1), seed=42
测试: 红色目标在 (1.0, 0.1), seed=99  ← 不同扰动

**2. 场景泛化**：在训练时没见过的场景配置下表现好

训练: 红色目标在 (1.0, 0.0) 和 (0.5, 0.5)
测试: 红色目标在 (0.7, 0.3)  ← 新的位置组合

**3. 条件泛化**：在训练时没见过的物理条件下表现好

训练: 标准质量、标准摩擦
测试: 质量 +30%、摩擦 -50%  ← 物理参数变化

每个层次比前一个更难。好的系统应该在层次 1 和 2 上表现良好，在层次 3 上至少不崩溃（安全降级）。

### 失败模式分类

| 失败模式 | 触发条件 | 第一个信号 | 严重度 |
|---|---|---|---|
| 感知失败 | 目标颜色在训练分布外 | 检测结果为空 | 中（策略原地等待） |
| 分布偏移 | 初始状态远离训练分布 | 动作异常大或异常小 | 高（可能导致翻倒） |
| 累积误差 | 长时间运行 | 轨迹逐渐偏离 | 中（最终可能迷路） |
| 指令歧义 | 模糊或矛盾的指令 | 策略犹豫（动作频繁切换） | 低（安全层兜底） |
| 执行器饱和 | 需要大力矩恢复 | ctrl 频繁触碰限幅 | 高（可能失去平衡） |

## 教科书级展开

<!-- upkie-animation:37-parameter -->

### 评估设计

**4 个固定测试任务**（三色导航 + 紧急停止）：

| 任务 | 指令文本 | 目标颜色 | 验收重点 |
|---|---|---|---|
| 红色导航 | "前往红色目标并停车" | red | 中文指令与停车 |
| 绿色导航 | "Navigate to the green target and stop" | green | 英文指令与停车 |
| 蓝色导航 | "Navigate to the blue target and stop" | blue | 英文指令与停车 |
| 紧急停止 | "立即停止" | unknown | 不调用 BC，当前控制步清零轮端力矩 |

**专属实验的 9 个专属指标**：

| 指标 | 含义 | 单位 | 说明 |
|---|---|---|---|
| three_color_task_count | 三色导航任务数 | 个 | 固定为红、绿、蓝 3 个导航任务 |
| navigation_success_rate | 导航成功率 | - | 到达目标 + 无碰撞 + 俯仰角安全 + 停车精度 |
| collision_rate | 碰撞发生率 | - | 与障碍物 geom 的接触检测 |
| mean_stopping_error_m | 平均停车误差 | m | 停止位置与理想位置的偏差 |
| max_pitch_rad | 最大俯仰角 | rad | 运行中最大倾斜角（安全性指标） |
| bc_policy_evaluated | 是否真实调用 BC | - | 必须为 1，防止退回脚本专家 |
| policy_inference_count | BC 推理次数 | 次 | 必须大于 0 |
| emergency_stop_latency_steps | 紧急停止延迟 | 步 | 必须为 0 |
| post_stop_wheel_torque_max | 停止后最大轮端力矩 | N*m | 必须接近 0 |

### 评估代码

```python
import json
from pathlib import Path
from upkie_mujoco_course.vla.labs import run_vla_lab

FIXED_TASKS = [
    "前往红色目标并停车",
    "Navigate to the green target and stop",
    "Navigate to the blue target and stop",
    "立即停止",
]
METRIC_NAMES = [
    "three_color_task_count", "navigation_success_rate", "collision_rate",
    "mean_stopping_error_m", "max_pitch_rad", "bc_policy_evaluated",
    "policy_inference_count", "emergency_stop_latency_steps",
    "post_stop_wheel_torque_max",
]

result_path = run_vla_lab("37", output_root=Path("outputs"))
metrics = json.loads(result_path.read_text(encoding="utf-8"))["metrics"]
assert set(metrics) == set(METRIC_NAMES)
for name in METRIC_NAMES:
    print(f"{name}={float(metrics[name]):.6f}")
```

关键行设计原因：

- `run_vla_lab("37")` 固定加载 `outputs/checkpoints/vla_bc_policy.npz`，内部等价于向真实 MuJoCo 评估传入 `policy_path="outputs/checkpoints/vla_bc_policy.npz"`，不会退回脚本专家。
- 三个导航任务必须实际调用 BC；第四个紧急停止任务故意绕过 BC，并在同一控制步检查轮端力矩清零。
- 成功判定条件严格：`stopped and not collision and max_pitch <= 0.5 and stopping_error <= 0.4m`——必须同时满足四个条件才算成功。
- 碰撞检测使用 MuJoCo 接触力：检查 `contact.geom1/geom2` 中是否有 `obstacle_` 前缀的 geom，这比基于距离的碰撞检测更精确。

### 运行时安全监控

实际项目通过 `VLASafetyController` 的内置计数器实现运行时监控：

```python
# VLASafetyController 已内置安全干预计数
controller = VLASafetyController()

# 运行结束后检查
print(f"安全干预次数: {controller.safety_interventions}")
print(f"总步数: {total_steps}")
print(f"干预率: {controller.safety_interventions / total_steps:.1%}")
```

`VLASafetyController.safety_interventions` 记录了运行中因俯仰角超限而被拦截的次数。如果干预率过高（如 > 20%），说明策略频繁输出不安全的速度指令，需要改进训练数据或调整安全阈值。

## 动手检查点

### 检查点 1：四任务真实 BC 闭环

```powershell
python scripts/run_vla_lab.py --chapter 37
```

当前 `outputs/results/vla_37.json` 的 9 个指标按 6 位小数读取为：

three_color_task_count=3.000000
navigation_success_rate=1.000000
collision_rate=0.000000
mean_stopping_error_m=0.180189
max_pitch_rad=0.117244
bc_policy_evaluated=1.000000
policy_inference_count=9260.000000
emergency_stop_latency_steps=0.000000
post_stop_wheel_torque_max=0.000000

这份固定结果来自真实 MuJoCo 闭环：BC 策略实际调用 `9260` 次，三色导航成功率 `100%`、碰撞率 `0`、平均停车误差 `0.180189 m`、最大俯仰 `0.117244 rad`，紧急停止延迟 `0 步`，停止后最大轮端力矩为 `0`。并发修改期间只把它作为带源码摘要的快照；待源码稳定后统一重跑，不能反复生成后挑选结果。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 37
```

## 可视化证据

<!-- upkie-animation:37-evidence -->

专属实验把三色闭环结果写入 `outputs/plots/vla_37.png`，统一 checkpoint 另保存关卡级汇总证据：

图中是红、绿、蓝三个导航任务的成功柱，绿色表示成功、橙色表示失败。BC 调用次数、紧急停止延迟和停止后轮端力矩从 `outputs/results/vla_37.json` 复核；本图不声称包含失败时间线或安全干预分布。

## 故障诊断挑战

<!-- upkie-animation:37-comparison -->

**破坏**：在 `VLASafetyController` 中去掉俯仰角安全检查——把 `soft_pitch_limit` 设为无穷大，使安全层永远不干预。

**第一处异常**：当策略输出较大的速度指令时，机器人躯干大幅倾斜，但因为没有安全层拦截，系统继续执行。机器人可能在几步内失去平衡倒下——而之前安全层会在俯仰角超过 0.18 rad 时提前将速度置零。

**根因假设**：安全检查是"早期保护"。去掉它意味着系统只能依赖底层平衡控制器的固有能力，一旦速度指令超出平衡能力范围就无法恢复。

**最小修复**：恢复 `soft_pitch_limit=0.18` 的安全检查。

**验证**：在所有任务中，`safety_interventions` 计数 > 0（说明安全层发挥了作用），且机器人不会倒下。

## 三档任务

### 基础任务

- 运行 `python scripts/run_vla_lab.py --chapter 37`，核对三色导航、紧急停止和 9 个专属指标。
- 分析至少一种失败模式的根因。

### 岗位挑战

- 设计额外的测试任务（如同时存在红色和蓝色目标），比较策略的选择准确率。
- 修改 `VLASafetyController` 的 `soft_pitch_limit` 参数（0.1→0.3），测试安全干预率和成功率的变化关系。

### 开放探索

- 研究 conformal prediction 如何为策略输出提供统计保证的置信区间。
- 写一段 200 字分析：在具身系统中，"知道自己不知道"为什么比"什么都敢做"更重要？

## 复盘与面试

1. **三种泛化层次的区别？** 数据泛化是统计学习的基本要求（新 seed），场景泛化要求策略对未见的任务配置（不同颜色、距离）也能处理，条件泛化要求策略对物理参数变化（质量、摩擦）也能适应。每个层次需要不同的训练策略。

2. **失败分析的关键是什么？** 找到"第一个可观测信号"——不是最终失败的现象，而是最早出现的异常。如果能检测到第一个信号，就能在失败发生前预防。

3. **OOD 检测的精度和召回率权衡？** 阈值太高 → 漏报多（真正 OOD 时不告警）；阈值太低 → 误报多（正常情况也告警，系统频繁进入安全模式）。实践中通常设置阈值使误报率 < 5%。

4. **怎样让系统从失败中学习？** (a) 收集失败 episode 的数据，加入训练集（DAgger 思路）；(b) 分析失败模式，针对性地增加训练场景；(c) 改进监控器，更早检测失败前兆。

## 下一关

关卡 `38`（C++、Eigen 与数值一致性）标志着从"应用型 VLA"阶段进入"工程部署"阶段。本关产出的评估框架和失败分析将成为部署阶段"持续监控"的基础——在真实机器人上运行时，同样的监控器需要持续运行，检测异常情况并触发安全机制。
