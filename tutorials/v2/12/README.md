# 12 反馈控制与闭环直觉

> 建设状态：可执行
> 阶段：经典控制
> 作品集目录：`outputs/portfolio/12`

## 岗位任务

你的交付物是一份"闭环控制演示报告"：用最简单的比例控制器让 Upkie 的轮子跟踪一个目标速度，并记录闭环与开环行为的差异。面试官会问："反馈控制为什么能对抗未知扰动？它的极限在哪里？"

具体交付：

1. 一段代码，实现开环控制和闭环比例控制的对比实验。
2. 一张图展示两种控制下轮速跟踪同一目标曲线的差异。
3. 一段 100 字分析，解释为什么纯比例控制有稳态误差，以及如何用积分项消除。

## 学习目标

- **能理解**：区分开环（前馈）控制和闭环（反馈）控制，理解反馈为什么能对抗模型误差和外部扰动。
- **能推导**：从一阶系统 `dx/dt = ax + bu` 出发，推导比例控制 `u = -kx` 下的闭环时间常数和稳态误差。
- **能实现**：在 MuJoCo 仿真中实现一个简单的比例控制器，让 Upkie 轮速跟踪阶跃目标。

## 前置关卡

完成 `11`（可替换机器人模型契约）的证据验收。你需要理解：

- Upkie 的执行器类型和单位（关卡 09）
- MuJoCo 的状态步进流程（关卡 06）
- 轮地接触和摩擦力（关卡 10）

## 先观察现象

**错误基线实验**：不给任何控制输入，观察 Upkie 的自然行为。

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

from upkie_mujoco_course.sim.runner import SimulationRunner

runner = SimulationRunner()
runner.reset("stand")

# 零控制，观察 5 秒
for i in range(2500):
    action = runner.data.ctrl.copy()  # 保持当前控制（默认零）
    runner.step(action)
    if i % 500 == 0:
        state = runner.posture_state()
        height = state["base_height"]
        print(f"t={runner.time:.1f}s: 高度={height:.4f}m")
```

> **模型加载说明**：本教程使用 `SimulationRunner` 加载模型，它内部从 `configs/robot/upkie.json` 指定的 URDF 路径（`assets/upkie/upkie_description/urdf/upkie.urdf`）构建 MuJoCo 模型，并自动添加地面、灯光和执行器。不要直接使用 `mujoco.MjModel.from_xml_path("assets/upkie.xml")`——该文件不存在。

**记录三个观察**：

1. Upkie 是否在几秒内倒下？（是——倒立摆是开环不稳定系统）
2. 倒下的方向是否每次相同？（取决于数值精度，但总是倒向某个方向）
3. 这说明"零控制"不是一个可行的策略——必须有反馈。

## 直觉与概念

<!-- upkie-animation:12-intuition -->

### 开环 vs 闭环：盲人 vs 看见的人

**开环控制**像盲人走路：你预先计划好"向前走 10 步，左转，再走 5 步"，但如果你被推了一下或者路有坡度，你就偏了，而且你不知道自己偏了。

**闭环控制**像看着路标走路：你每走一步都看一下目标方向，发现偏了就纠正。即使被推了一下，你也能看到偏差并修正。

在 Upkie 的场景中：

- **开环**：给轮子固定力矩 `ctrl = 0.5 N*m`，不管机器人当前状态
- **闭环**：每步测量当前轮速，计算误差 `e = target_speed - current_speed`，按比例调整力矩 `ctrl = kp * e`

### 为什么倒立摆必须闭环

倒立摆的线性化模型有一个正实部极点（不稳定极点），这意味着：

$$
dx/dt = a \cdot x,  a > 0
$$
解: x(t) = x(0) * exp(a * t)

即使初始偏差 `x(0)` 只有 0.001 rad（约 0.057 度），如果 `a = 5`（典型的倒立摆不稳定极点），1 秒后偏差变成 `0.001 * e^5 = 0.148 rad`（约 8.5 度），2 秒后变成 `0.001 * e^10 = 22 rad`——已经完全倒了。

**闭环控制的目标**：用反馈把正极点变成负极点，使系统稳定。

### 比例控制的核心公式

**公式**：

$$
u = k_{p} \cdot e = k_{p} \cdot (r - y)
$$
- `$u` — 控制输出
- `$kp` — 比例增益
- `$e` — 误差（目标 - 实际）
- `$r` — 参考输入（目标值）
- `$y` — 系统输出（实际值）

**物理意义**：误差越大，纠正动作越大。误差为零时，动作也为零。

**Upkie 轮速控制的例子**：

目标轮速: r = 2.0 rad/s
当前轮速: y = 1.5 rad/s
kp = 0.5
$$
u = 0.5 \cdot (2.0 - 1.5) = 0.5 \cdot 0.5 = 0.25 N \cdot m
$$

## 教科书级展开

<!-- upkie-animation:12-parameter -->

### 一阶系统的闭环分析

**开环系统**：

$$
I \cdot dw/dt = \tau - b \cdot w
$$
- `$I` — 轮子转动惯量 (kg*m^2)
- `$w` — 角速度 (rad/s)
- `$tau` — 电机力矩 (N*m)
- `$b` — 粘性摩擦系数 (N*m*s/rad)

**符号拆解**：

| 符号 | 含义 | Upkie 典型值 | 单位 |
|---|---|---|---|
| `I` | 轮子转动惯量 | ~0.001 | kg*m^2 |
| `w` | 角速度 | 0-10 | rad/s |
| `tau` | 电机力矩 | [-1, 1] | N*m |
| `b` | 粘性摩擦 | ~0.01 | N*m*s/rad |

**开环时间常数**：

$$
tau_{\text{open}} = \frac{I}{b} = 0.001 / 0.01 = 0.1 s
$$

意思是：不施加力矩时，轮速在 0.1 秒内衰减到初始值的 37%（1/e）。

**加入比例控制** `tau = kp * (r - w)`：

$$
I \cdot dw/dt = k_{p} \cdot (r - w) - b \cdot w
I \cdot dw/dt = k_{p} \cdot r - (k_{p} + b) \cdot w
$$
闭环时间常数: tau_closed = I / (kp + b)
稳态值:       w_ss = kp * r / (kp + b)

**设计动机**：增大 kp 有两个效果：(a) 响应更快（tau_closed 变小）；(b) 稳态误差变小（w_ss 接近 r）。但 kp 不能无限增大——执行器有力矩上限。

**数值算例**：

kp = 0.5, I = 0.001, b = 0.01, r = 2.0
$$
tau_{\text{closed}} = 0.001 / (0.5 + 0.01) = 0.00196 s
w_{ss} = 0.5 \cdot 2.0 / (0.5 + 0.01) = 1.961 rad/s
$$
稳态误差 = r - w_ss = 2.0 - 1.961 = 0.039 rad/s（约 2%）

### 稳态误差的来源

纯比例控制的稳态误差不为零，因为：

稳态时: dw/dt = 0
所以:   kp * (r - w_ss) = b * w_ss
解出:   w_ss = kp * r / (kp + b)
误差:   e_ss = r - w_ss = b * r / (kp + b)

只要 `b > 0`（总是成立的），纯比例控制就有稳态误差。要消除它，需要积分项（关卡 13 的内容）。

### Upkie 代码映射

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import numpy as np
from upkie_mujoco_course.sim.runner import SimulationRunner

runner = SimulationRunner()
runner.reset("stand")

kp = 0.5           # 比例增益
target_speed = 2.0  # 目标轮速 (rad/s)

# 获取左轮角速度和左轮力矩的索引（来自 runner 的映射接口）
left_wheel_dof = runner.joint_map.dofadr["left_wheel"]
left_wheel_ctrl = runner.actuator_ids["left_wheel_motor"]

speeds = []
for step in range(2000):
    # 读取当前轮速（左轮）
    current_speed = runner.data.qvel[left_wheel_dof]
    speeds.append(current_speed)

    # 比例控制
    error = target_speed - current_speed
    torque = kp * error

    # 裁剪到执行器范围
    torque = np.clip(torque, -1.0, 1.0)
    action = runner.data.ctrl.copy()
    action[left_wheel_ctrl] = torque
    runner.step(action)

print(f"最终轮速: {speeds[-1]:.4f} rad/s")
print(f"目标轮速: {target_speed} rad/s")
print(f"稳态误差: {target_speed - speeds[-1]:.4f} rad/s")
```

关键行设计原因：

- `np.clip(torque, -1.0, 1.0)`：执行器有物理限制。如果 kp 很大且误差很大，计算出的力矩可能超出范围。裁剪是安全措施，但会导致响应变慢（力矩饱和）。
- `runner.joint_map.dofadr["left_wheel"]`：通过名称查找左轮角速度在 qvel 中的索引，而不是硬编码数字。
- `runner.actuator_ids["left_wheel_motor"]`：通过名称查找左轮力矩在 ctrl 中的索引。

> **关于硬编码索引**：为了教学简洁，你在其他资料中可能看到 `data.qvel[8]`、`data.ctrl[4]` 这样的硬编码写法。在本课程中推荐使用 `SimulationRunner` 的映射接口（`joint_map.dofadr`、`actuator_ids`）通过名称查找索引。硬编码索引在模型结构变化时容易出错，映射接口则自动适应模型变更。如果你选择硬编码，务必在代码注释中标注索引来源并添加断言校验。

## 动手检查点

### 检查点 1：PD 平衡控制器运行

```powershell
python scripts/02_run_pd_balancer.py --duration 10 --no-viewer
```

预期输出：

传统平衡 demo 完成: sim_time=10.000s pitch=+0.1424 contact=True

> **说明**：`02_run_pd_balancer.py` 运行的是内置的 `WheelBalancerController`，它使用预设的 PD 增益进行轮端力矩平衡。该脚本支持 `--duration`（仿真时长，秒）和 `--no-viewer`（不打开可视化窗口）两个参数。如果你想自定义比例增益和目标速度，请在上面的"Upkie 代码映射"代码中修改 `kp` 和 `target_speed` 变量。

### 检查点 2：开环 vs 闭环对比

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import numpy as np
from upkie_mujoco_course.sim.runner import SimulationRunner

# 开环
runner_open = SimulationRunner()
runner_open.reset("stand")
wheel_dof = runner_open.joint_map.dofadr["left_wheel"]
wheel_ctrl = runner_open.actuator_ids["left_wheel_motor"]
action = np.zeros(runner_open.model.nu)
action[wheel_ctrl] = 0.5  # 固定力矩
for _ in range(500):
    runner_open.step(action)
print(f'开环 1s 后轮速: {runner_open.data.qvel[wheel_dof]:.4f} rad/s')
runner_open.close()

# 闭环
runner_closed = SimulationRunner()
runner_closed.reset("stand")
wheel_dof2 = runner_closed.joint_map.dofadr["left_wheel"]
wheel_ctrl2 = runner_closed.actuator_ids["left_wheel_motor"]
for _ in range(500):
    e = 2.0 - runner_closed.data.qvel[wheel_dof2]
    action2 = np.zeros(runner_closed.model.nu)
    action2[wheel_ctrl2] = np.clip(0.5 * e, -1, 1)
    runner_closed.step(action2)
print(f'闭环 1s 后轮速: {runner_closed.data.qvel[wheel_dof2]:.4f} rad/s')
runner_closed.close()
```

预期：闭环轮速接近 2.0 rad/s，开环轮速持续加速（没有反馈限制）。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 12
```

## 可视化证据

<!-- upkie-animation:12-evidence -->

在 `outputs/plots/checkpoint_12.png` 中绘制：

1. **上图**：开环控制的轮速 vs 时间——持续上升或下降（不稳定或无目标跟踪）。
2. **下图**：闭环控制的轮速 vs 时间——快速收敛到目标值，有小稳态误差。
3. 在两图中叠加目标值水平线，直观展示误差。

## 故障诊断挑战

<!-- upkie-animation:12-comparison -->

**破坏**：把比例增益的符号写反——`u = -kp * e` 而不是 `u = kp * e`（正反馈而不是负反馈）。

```python
# 错误：正反馈
error = target_speed - current_speed
torque = -kp * error  # 应该是 +kp * error
```

**第一处异常**：轮速不但不收敛到目标值，反而远离目标值——如果初始速度小于目标值，力矩方向反而让速度进一步减小（或变成负方向加速）。

**根因假设**：负反馈变为正反馈，误差被放大而不是纠正。

**最小修复**：去掉负号，恢复 `torque = kp * error`。

**验证**：轮速重新收敛到目标值。

## 三档任务

### 基础任务

- 实现比例控制器，让轮速跟踪 0.5、1.0、2.0 rad/s 三个目标值。
- 绘制三个目标值下的阶跃响应曲线，标注稳态误差。

### 岗位挑战

- 在仿真中加入外部扰动：在第 500 步给躯干施加一个水平方向的冲击力，记录闭环控制器的恢复时间。
- 分析 kp 从 0.1 到 2.0 变化时，稳态误差和收敛时间的权衡曲线。

### 开放探索

- 研究 Bang-bang 控制（继电器控制）：当误差为正时输出最大力矩，误差为负时输出最小力矩。
- 比较比例控制和 Bang-bang 控制在轮速跟踪上的精度和能耗（力矩积分）。

## 复盘与面试

1. 反馈控制为什么能对抗扰动？

<!-- upkie-qa:12-q1 -->
因为反馈不关心扰动来自哪里——它只看误差。无论扰动是风、坡度、负载变化还是建模误差，只要它们让状态偏离目标、产生了误差，反馈律就会自动产生反方向的纠正力。这是反馈与前馈/开环的本质区别：开环控制必须提前知道所有扰动才能补偿，反馈控制对未建模的扰动天然有抵抗能力——代价是必须先出现误差才能纠正，永远慢半拍。
<!-- /upkie-qa -->

2. 比例控制的两个核心限制？

<!-- upkie-qa:12-q2 -->
(a) 稳态误差不为零：比例控制器只有在误差非零时才有输出，面对持续扰动（如坡度）时系统会停在一个「误差×kp 正好抵消扰动」的非零平衡点上，需要积分项才能消除；(b) 增益太大会振荡甚至不稳定：kp 越大响应越快，但超过临界值后系统开始超调、振荡，需要微分项提供阻尼或改用更高级方法。这两个限制分别引出了 PID 的 I 和 D，是下一关的入口。
<!-- /upkie-qa -->

3. 正反馈和负反馈的区别？

<!-- upkie-qa:12-q3 -->
负反馈的纠正力方向与误差相反，会减小误差，让系统稳定；正反馈的输出与误差同向，会放大误差，让系统失控。工程上最常见的正反馈事故不是故意设计，而是符号错误：传感器方向、电机方向或误差定义中某一处符号写反，负反馈就变成了正反馈。在倒立摆这种本身不稳定的系统上，正反馈会让它在毫秒级时间内倒下，比完全不控制倒得更快。
<!-- /upkie-qa -->

4. 如果 kp 设为零会怎样？

<!-- upkie-qa:12-q4 -->
控制器输出恒为零，系统回到开环状态——相当于没有控制器。Upkie 是倒立摆结构，直立是不稳定平衡点：任何微小扰动（传感器噪声、地面不平）都会让偏角指数增长，机器人在几秒内倒下。这个实验的价值在于它把「反馈是维持不稳定平衡的必要条件」变成了可观察的事实：对稳定系统（如水平面上的小车）kp=0 只是慢，对倒立摆 kp=0 是必倒。
<!-- /upkie-qa -->

## 下一关

关卡 `13`（PID 控制与抗饱和）会假设你已经理解比例控制的原理和稳态误差问题。本关产出的比例控制器是 PID 的"P"部分，下一关将加入积分项（消除稳态误差）和微分项（抑制超调），并解决积分饱和这个实际工程中最重要的问题。
