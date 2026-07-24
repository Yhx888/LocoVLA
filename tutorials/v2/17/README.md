# 17 LQR 与 Riccati 方程

> 建设状态：可执行
> 阶段：经典控制
> 作品集目录：`outputs/portfolio/17`

## 岗位任务

你的交付物是一份"LQR 控制器设计与验证报告"：从 Upkie 的线性化模型出发，推导 LQR 增益矩阵 K，在仿真中验证闭环稳定性，并分析 Q 和 R 矩阵对控制性能的影响。面试官会问："LQR 的最优是什么意思？它比手动调的 PD 好在哪里？在什么条件下会失效？"

具体交付：

1. 完整的 LQR 推导过程：从线性化状态空间到代数 Riccati 方程到增益矩阵 K。
2. 一段代码，用 `scipy.linalg.solve_continuous_are` 求解 Riccati 方程并计算 K。
3. 一张 Q/R 敏感性分析图：展示不同 Q/R 权重下闭环极点、收敛时间和控制量的变化。

## 学习目标

- **能理解**：解释 LQR 的代价函数 `J = integral(x^T Q x + u^T R u)` 中每一项的物理意义，以及"最优"的含义。
- **能推导**：从最优性条件出发，推导代数 Riccati 方程（ARE），不跳步。
- **能实现**：用 SciPy 求解 ARE，得到 K 矩阵，并在 MuJoCo 中实现 `u = -Kx` 控制器。

## 前置关卡

完成 `16`（状态空间与可控性）的证据验收。你需要理解：

- 状态空间模型 `dx/dt = Ax + Bu` 的含义
- 可控性矩阵 `[B, AB, A^2B, ...]` 的秩条件
- Upkie 在直立平衡点附近的线性化模型

## 先观察现象

**错误基线实验**：用关卡 12 的比例控制器尝试让 Upkie 保持直立（而不是只控制轮速）。

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import numpy as np
from upkie_mujoco_course.sim.runner import SimulationRunner

runner = SimulationRunner()
runner.reset("stand")

# 用简单比例控制尝试平衡
kp_pitch = 50.0  # 俯仰角比例增益
kd_pitch = 10.0  # 俯仰角速度微分增益

# 通过映射接口获取执行器索引
left_wheel_ctrl = runner.actuator_ids["left_wheel_motor"]
right_wheel_ctrl = runner.actuator_ids["right_wheel_motor"]

for i in range(2500):
    # 提取俯仰角偏差和俯仰角速度（使用 SimulationRunner 的内置方法）
    state = runner.posture_state()
    pitch = state["pitch_error"]
    pitch_rate = state["pitch_rate"]

    # PD 控制轮端
    torque = kp_pitch * pitch + kd_pitch * pitch_rate
    torque = np.clip(torque, -1.0, 1.0)
    action = np.zeros(runner.model.nu)
    left_dir, right_dir = runner.spec.wheel_directions
    action[left_wheel_ctrl] = left_dir * torque
    action[right_wheel_ctrl] = right_dir * torque
    runner.step(action)

runner.close()
```

> **模型加载说明**：与关卡 12 相同，这里使用 `SimulationRunner` 加载模型，而非不存在的 `assets/upkie.xml`。`runner.posture_state()` 内部使用 `sin_pitch = 2.0 * (qw * qy - qz * qx)` 从四元数提取俯仰角（其中 `qw, qx, qy, qz` 分别是四元数的标量和三个分量），这与 `np.arcsin(2 * (q[0]*q[2] - q[3]*q[1]))` 等价。

**记录三个观察**：

1. 手动调的 PD 能在短时间内维持平衡吗？（可能——但需要大量试错）
2. 增益稍微改变后还稳定吗？（很可能不稳定——手动调参没有系统性保证）
3. 这说明我们需要一个系统化的最优增益设计方法。

## 直觉与概念

<!-- upkie-animation:17-intuition -->

### LQR 的直觉：最优的"弹簧"

把 LQR 想象成一个虚拟弹簧系统：

- 状态偏差 `x`（偏离平衡点）就像一个被拉开的弹簧
- 控制输入 `u` 就像你用手推弹簧
- 代价函数 `J` 是"弹簧势能 + 你的体力消耗"的总和
- LQR 的目标：用最少的体力（R 项）让弹簧最快回到原位（Q 项）

**Q 矩阵**衡量"哪些状态偏差更重要"：

- `Q[0,0]` 大 → 躯干位置偏差很重要（不允许漂移）
- `Q[2,2]` 大 → 俯仰角偏差很重要（不允许倾斜）

**R 矩阵**衡量"控制代价有多大"：

- `R` 大 → 控制器保守，动作小但响应慢
- `R` 小 → 控制器激进，动作大但响应快

### 从 PD 到 LQR：为什么需要系统化

手动调 PD 的问题：

1. **多变量耦合**：Upkie 有 12 个状态变量和 6 个控制输入，手动找到 72 个增益（6x12 矩阵）是不现实的。
2. **没有最优保证**：你调出的增益可能"能用"，但不是"最优"的——存在另一组增益在同样的控制代价下得到更小的状态偏差。
3. **没有稳定性证明**：手动调参后你只能通过仿真观察是否稳定，不能数学证明闭环系统一定稳定。

LQR 解决这三个问题：(a) 自动计算多变量增益矩阵 K；(b) 保证在代价函数意义下最优；(c) 保证闭环稳定（只要系统可控）。

## 教科书级展开

<!-- upkie-animation:17-parameter -->

### 代价函数

**公式**：

$$
J = integral_{0}^inf (x(t)^T Q x(t) + u(t)^T R u(t)) dt
$$

**符号拆解**：

| 符号 | 含义 | 维度 | 单位 |
|---|---|---|---|
| `x(t)` | 状态偏差向量 | R^12 | 混合（m, rad, m/s, rad/s） |
| `u(t)` | 控制输入向量 | R^6 | 混合（rad, N*m） |
| `Q` | 状态权重矩阵 | 12x12 | 各项不同 |
| `R` | 控制权重矩阵 | 6x6 | 各项不同 |
| `J` | 总代价 | 标量 | 无量纲（或自定义） |

**物理意义**：`x^T Q x` 惩罚状态偏差（越大说明偏离平衡点越严重），`u^T R u` 惩罚控制量（越大说明消耗的能量越多）。LQR 寻找平衡两者的最优策略。

> **维度说明——简化模型 vs 完整模型**：上表中 `x` 是 12 维、`Q` 是 12x12、`u` 是 6 维、`R` 是 6x6，这是 Upkie 的**完整状态空间**（`nv=12` 个自由度速度 + 对应位置）。在本章的"数值算例"部分，我们使用一个**简化的 4 维教学模型**（仅含俯仰角、俯仰角速度、轮子位置、轮子速度）来演示 LQR 的推导和求解过程。简化模型能让你专注于 LQR 的核心机制，而不被 12 维矩阵淹没。"完整代码映射"部分则展示如何将同样的方法应用到完整 12 维模型。

### 代数 Riccati 方程（ARE）

**推导**（不跳步）：

1. 假设最优值函数 `V(x) = x^T P x`，其中 P 是对称正半定矩阵
2. 哈密顿-雅可比-贝尔曼（HJB）方程：

$$
0 = min_{u} [ x^T Q x + u^T R u + (dV/dx)^T (Ax + Bu) ]
$$

3. 对 u 求导并令为零：

$$
d/du [u^T R u + 2x^T P B u] = 0
2 R u + 2 B^T P x = 0
u* = -R^{-1} B^T P x
$$

4. 代入 u* 到 HJB：

$$
0 = x^T Q x + x^T P B R^{-1} B^T P x + 2 x^T P (A - B R^{-1} B^T P) x
0 = x^T [Q + P B R^{-1} B^T P + P A + A^T P - 2 P B R^{-1} B^T P] x
0 = x^T [A^T P + P A - P B R^{-1} B^T P + Q] x
$$

5. 因为 x 任意，方括号内的矩阵必须为零：

$$
A^T P + P A - P B R^{-1} B^T P + Q = 0
$$

这就是**代数 Riccati 方程（ARE）**。

6. 最优增益矩阵：

$$
K = R^{-1} B^T P
u = -K x
$$

### 数值算例

**Upkie 简化模型**（仅俯仰+轮速，4 个状态）：

> **注意**：以下 A/B 矩阵使用简化的教学数值（`g/l=50, b/I=10` 等），目的是让你快速理解 LQR 的求解流程。课程代码库中 `src/upkie_mujoco_course/classical_control/math_tools.py` 的 `wheel_pendulum_state_space()` 函数提供了基于真实物理参数的 4 维状态空间模型（状态顺序为 `[x, x_dot, pitch, pitch_dot]`），可用于更精确的计算。
>
> **两套模型差异（重要）**：本算例与代码模型不只是状态顺序不同，**物理含义与 A/B 矩阵形式也不同**：
> - 本算例的输入是**轮端等效力矩 tau**（直接作用于摆杆转轴），`B = [0, 1/(m·l²), 0, 1/I]^T`，状态包含轮子位置/速度，对应 `wheel_pos_dot=wheel_speed`、`wheel_speed_dot=-b/I·wheel_speed + 1/I·tau`；
> - 代码版（与 Ch16/Ch17 line 268 一致）的输入是**作用于基座的水平力 u**（等价于地面对轮的反作用力），`B = [0, 1/m, 0, -1/(m·l)]^T`，状态包含基座位置/速度，对应 `x_ddot = u/m`、`pitch_ddot = (g/l)·pitch - u/(m·l)`。
>
> 二者通过 `u·r = tau`（轮半径 r）可相互转换，但直接对比 K 矩阵前必须先做状态置换与单位换算，不能简单代入。

状态: x = [pitch, pitch_rate, wheel_pos, wheel_speed]
A = [[0, 1, 0, 0],
[g/l, 0, 0, 0],    # g/l 是倒立摆的不稳定项
[0, 0, 0, 1],
[0, 0, 0, -b/I]]
B = [[0], [1/(m*l^2)], [0], [1/I]]
设 g/l = 50, b/I = 10, 1/(m*l^2) = 20, 1/I = 100
- `$Q` — diag([100, 10, 1, 1])   # 俯仰角最重要
- `$R` — [0.1]                     # 力矩代价较小

用 SciPy 求解：

```python
import numpy as np
from scipy.linalg import solve_continuous_are

A = np.array([[0, 1, 0, 0],
              [50, 0, 0, 0],
              [0, 0, 0, 1],
              [0, 0, 0, -10]])
B = np.array([[0], [20], [0], [100]])
Q = np.diag([100, 10, 1, 1])
R = np.array([[0.1]])

# 求解 ARE
P = solve_continuous_are(A, B, Q, R)

# 计算增益矩阵
K = np.linalg.inv(R) @ B.T @ P
print(f"LQR 增益矩阵 K:\n{K}")
# K 应该是 1x4 矩阵

# 验证闭环稳定性
A_cl = A - B @ K
eigenvalues = np.linalg.eigvals(A_cl)
print(f"闭环极点: {eigenvalues}")
# 所有极点的实部应为负
```

### Upkie 完整代码映射

以下代码展示如何在仿真中使用 LQR 控制器。为了教学清晰，我们仍然使用简化的 4 维模型计算 LQR 增益，然后在完整 MuJoCo 仿真中仅对俯仰和轮速通道施加 LQR 控制。

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import numpy as np
from scipy.linalg import solve_continuous_are
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.classical_control.math_tools import wheel_pendulum_state_space

# ---- 第一步：用简化模型计算 LQR 增益 ----
A, B = wheel_pendulum_state_space()  # 4x4 和 4x1 矩阵

# 设计 Q 和 R（4 维简化模型）
Q = np.diag([1.0, 1.0, 100.0, 10.0])  # 俯仰角（索引2）和俯仰角速度（索引3）权重高
R = np.array([[0.1]])                   # 力矩代价较小

P = solve_continuous_are(A, B, Q, R)
K = np.linalg.inv(R) @ B.T @ P
print(f"LQR 增益矩阵 K (1x4):\n{K}")

# 验证闭环稳定性
eigenvalues = np.linalg.eigvals(A - B @ K)
print(f"闭环极点: {eigenvalues}")
assert all(e.real < 0 for e in eigenvalues), "闭环不稳定！"

# ---- 第二步：在 MuJoCo 仿真中应用 ----
runner = SimulationRunner()
runner.reset("stand")

left_wheel_ctrl = runner.actuator_ids["left_wheel_motor"]
right_wheel_ctrl = runner.actuator_ids["right_wheel_motor"]
ctrl_low = runner.model.actuator_ctrlrange[:, 0]
ctrl_high = runner.model.actuator_ctrlrange[:, 1]

for _ in range(5000):
    # 提取简化模型的 4 个状态偏差
    state = runner.posture_state()
    # wheel_pendulum_state_space 的状态顺序: [x, x_dot, pitch, pitch_dot]
    x_deviation = np.array([
        state["x_position"],
        state["forward_velocity"],
        state["pitch_error"],   # 相对于平衡点的俯仰角偏差
        state["pitch_rate"],
    ])

    # LQR 计算控制输入（单输入：轮端力矩）
    u = -K @ x_deviation  # 标量

    # 将力矩施加到两个轮端（注意方向系数）
    action = np.zeros(runner.model.nu)
    torque = float(np.clip(u, -1.0, 1.0))
    left_dir, right_dir = runner.spec.wheel_directions
    action[left_wheel_ctrl] = left_dir * torque
    action[right_wheel_ctrl] = right_dir * torque
    runner.step(action)

runner.close()
```

关键行设计原因：

- `wheel_pendulum_state_space()`：从 `math_tools.py` 获取 4 维线性化模型，不需要加载预计算的 `.npy` 文件。该函数使用 `mass_kg=10.0, com_length_m=0.5` 等默认物理参数。
- `state["pitch_error"]`：使用 `SimulationRunner.posture_state()` 返回的俯仰角偏差（已减去平衡点 `equilibrium_pitch_rad`），而不是手动从四元数计算。
- `R = np.array([[0.1]])`：简化模型只有 1 个控制输入（轮端力矩），所以 R 是 1x1 矩阵。
- `np.clip(u, -1.0, 1.0)`：LQR 理论假设无限控制能力，实际执行器有限制（`[-1.0, 1.0] N*m`）。裁剪不是最优的，但保证安全。

> **关于完整 12 维 LQR**：如果你要为 Upkie 的全部 12 个自由度设计 LQR 控制器，需要构建 12x12 的 A 矩阵和 12x6 的 B 矩阵（对应 6 个执行器），并设计 12x12 的 Q 和 6x6 的 R。此时 `R = np.diag([10, 10, 10, 10, 0.1, 0.1])`：腿部 position actuator 有内置 PD，代价设高一些让它们保守；轮端需要精确控制，代价设低一些允许更大力矩。完整模型的线性化需要使用 MuJoCo 的 `mjd_transitionFD` 数值线性化功能，这超出了本章范围。

## 从变分法到 HJB 与 Pontryagin：同一个标量算例

下面让三种方法解决同一个问题，避免用三个互不相干的例子堆术语。

### 第一层：直觉

设 `x(t)` 是归一化位置误差，`u(t)=x_dot(t)` 是修正速度。初始误差为 1，希望 2 秒后接近 0；动作太大会消耗能量，终点仍有误差也要付代价：

$$
x_{\text{dot}}=u, x(0)=1, T=2 s
J=integral_{0}^T 0.5 \cdot u(t)^2 dt + 0.5 \cdot q_{f}*x(T)^2, q_{f}=4
$$

变分法研究整条曲线，HJB 研究每个状态的最小剩余代价，Pontryagin 研究状态、控制与协态的必要条件。

### 第二层：符号与单位

| 符号 | 含义 | 本算例单位 |
|---|---|---|
| `x` | 归一化位置误差 | 1 |
| `u=x_dot` | 误差修正速度 | 1/s |
| `T` | 终止时间 | s |
| `q_f` | 终端误差权重 | 1/s |
| `V(t,x)` | 最小剩余代价 | 1/s |
| `lambda` | 协态 | 1/s |

这里把物理位置和速度按允许范围归一化。映射回 Upkie 时必须恢复 m、rad、N*m 的尺度，不能直接复制 `q_f=4`。

### 第三层：物理意义

`0.5*u^2` 是动作能量的代理，`0.5*q_f*x(T)^2` 惩罚终点误差。有限 `q_f` 是软约束，因此最优 `x(T)` 接近 0 但不必严格等于 0。

### 第四层：设计动机

- 变分法是 Euler-Lagrange 方程的入口；
- HJB 给出反馈值函数，是 LQR 和动态规划的理论入口；
- Pontryagin 形成状态与协态的两点边值问题，并连接第 24 关打靶法。

三者在这个光滑凸问题上必须一致。若结果不同，先查符号、终端条件和离散化。

### 第五层：不跳步推导

**Euler-Lagrange。** 因为 `u=x_dot`，`L=0.5*x_dot^2`：

$$
d/dt(partial L/partial x_{\text{dot}})-partial L/partial x=0
x_{\text{ddot}}=0
x=a+b \cdot t, u=b
$$

软终端代价给出横截条件：

$$
x_{\text{dot}}(T)+q_{f}*x(T)=0
b+q_{f}*(x_{0}+b \cdot T)=0
b=-q_{f}*x_{0}/(1+q_{f}*T)
$$

**HJB。** 设 `V(t,x)=0.5*P(t)*x^2`，且 `P(T)=q_f`：

$$
0=V_{t}+min_{u}[0.5 \cdot u^2+V_{x}*u]
u*=-P \cdot x
P_{\text{dot}}=P^2
P(t)=q_{f}/[1+q_{f}*(T-t)]
$$

**Pontryagin。** Hamiltonian 为 `H=0.5*u^2+lambda*u`：

$$
lambda_{\text{dot}}=-partial H/partial x=0
partial H/partial u=u+\lambda=0
\lambda(T)=q_{f}*x(T)
$$

所以协态为常数，`u=-lambda`，最终仍得到 `u=-q_f*x_0/(1+q_f*T)`。

### 第六层：手算复核

代入 `x_0=1, T=2, q_f=4`：

$$
u*=-\frac{4}{9}
x(t)=1-4t/9
x(T)=\frac{1}{9}
J=0.5 \cdot (16/81) \cdot 2+0.5 \cdot 4 \cdot (1/81)=\frac{2}{9}
$$

Euler-Lagrange 的 `x_ddot`、HJB PDE、PMP 的 `lambda_dot`、`u+lambda` 和终端横截残差都应接近机器精度。

### 第七层：代码映射与边界

```python
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_euler_lagrange
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_hjb
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_pontryagin

euler = solve_scalar_euler_lagrange(initial_state=1.0, horizon=2.0, terminal_weight=4.0)
hjb = solve_scalar_hjb(initial_state=1.0, horizon=2.0, terminal_weight=4.0)
pmp = solve_scalar_pontryagin(initial_state=1.0, horizon=2.0, terminal_weight=4.0)
```

实现位于 `classical_control/math_tools.py`。本算例假设动力学连续、控制无硬限幅、代价凸且模型准确。轮端饱和、接触切换或终端硬约束出现时，解析解不再直接成立，需要第 23、24 关的约束优化。

## 动手检查点

### 检查点 1：Riccati 方程求解

```powershell
python -c "
from scipy.linalg import solve_continuous_are
import numpy as np
A = np.array([[0,1,0,0],[50,0,0,0],[0,0,0,1],[0,0,0,-10]])
B = np.array([[0],[20],[0],[100]])
Q = np.diag([100,10,1,1])
R = np.array([[0.1]])
P = solve_continuous_are(A, B, Q, R)
K = np.linalg.inv(R) @ B.T @ P
eigs = np.linalg.eigvals(A - B @ K)
print(f'K = {K}')
print(f'闭环极点实部: {eigs.real}')
assert all(e.real < 0 for e in eigs), '闭环不稳定!'
print('闭环稳定')
"
```

预期：所有极点实部为负。

### 检查点 2：LQR 控制仿真

```powershell
python scripts/03_run_lqr_balancer.py --duration 10 --no-viewer
python scripts/run_classical_control_lab.py --chapter 17
python scripts/course_checkpoint.py --chapter 17
```

预期输出：

LQR 平衡完成: sim_time=10.000s pitch=+0.14xx x=+0.xxxxm

> **说明**：`03_run_lqr_balancer.py` 使用内置的 `LQRBalanceController`，支持 `--duration`（仿真时长，秒）和 `--no-viewer`（不打开可视化窗口）两个参数。Upkie 应保持直立至少 10 秒，俯仰角偏差 < 5 度。

## 可视化证据

<!-- upkie-animation:17-evidence -->

运行第 17 关实验后检查：

- `outputs/plots/classical_17.png`：左列是 PD/LQR MuJoCo 对照，右列是 Euler-Lagrange、HJB、Pontryagin 的状态、控制和方程残差；
- `outputs/logs/classical_17.json`：保存三种方法的完整轨迹、代价和必要条件残差；
- `outputs/results/classical_17.json`：对每项方程残差与跨方法一致性执行硬门槛；
- `outputs/portfolio/17/evidence.json`：作品集证据索引。

图中应看到：

1. **左图**：俯仰角 vs 时间——从初始扰动收敛到零。
2. **右图**：控制力矩 vs 时间——初始力矩大，随后衰减。
3. **右列**：三种最优控制方法的轨迹重合，残差处于机器精度量级。

## 故障诊断挑战

<!-- upkie-animation:17-comparison -->

**破坏**：把 LQR 增益矩阵 K 的某一行符号取反（比如把轮端对应的行乘以 -1）。

**第一处异常**：闭环极点中出现正实部极点，系统不稳定——Upkie 在几十毫秒内倒下，轮子朝错误方向加速。

**根因假设**：K 的符号决定了反馈方向。某一行取反意味着该控制通道变成正反馈。

**最小修复**：恢复正确的 K 矩阵。

**验证**：闭环极点全部回到左半平面，Upkie 重新稳定。

## 三档任务

### 基础任务

- 用 SciPy 求解 ARE，打印 K 矩阵和闭环极点。
- 在仿真中运行 LQR 控制器，记录 10 秒的状态轨迹。

### 岗位挑战

- 设计三组 Q/R 参数（保守/平衡/激进），对比它们的阶跃响应、控制能量和鲁棒性。
- 分析 LQR 在模型误差下的鲁棒性：把 A 矩阵中的 g/l 增大 20%，测试闭环是否仍稳定。

### 开放探索

- 研究离散时间 LQR（DLQR），比较它与连续时间 LQR 在 dt=0.002s 下的差异。
- 写一段 200 字分析：为什么 LQR 在机器人控制中如此重要？它的"最优"在实际工程中意味着什么？

## 复盘与面试

1. **LQR 的"最优"是什么意思？** 在代价函数 `J = int(x^T Q x + u^T R u) dt` 意义下最优——不是绝对最优，而是针对你选择的 Q 和 R 的最优。换一组 Q/R 就得到不同的"最优"。

2. **ARE 的解 P 必须满足什么条件？** P 必须是对称正半定矩阵。如果 P 有负特征值，说明代价函数可以无限减小（问题无界），通常是系统不可控导致的。

3. **LQR 比手动调 PD 好在哪里？** (a) 系统化计算多变量增益；(b) 保证最优性和稳定性；(c) 可以通过调整 Q/R 直观地改变行为。但 LQR 假设线性模型和二次代价，对大偏差和非线性效应无能为力。

4. **LQR 失效的第一个信号是什么？** 当状态偏差大到线性化假设不成立时（比如俯仰角 > 30 度），LQR 的增益不再最优，可能无法恢复。这时需要切换到非线性控制或 RL 策略。

## 下一关

关卡 `18`（速度、偏航、高度与动作接口）会假设你已经理解 LQR 如何稳定 Upkie 的平衡。本关产出的 LQR 增益矩阵将成为下一关"动作接口"的基础层——高层指令（速度命令、偏航命令）通过修改 LQR 的参考点来实现，而不是绕过 LQR。
