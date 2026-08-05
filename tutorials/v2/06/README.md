# 06 MuJoCo 状态与时间步进

> 建设状态：可执行
> 阶段：机器人仿真
> 作品集目录：`outputs/portfolio/06`

## 岗位任务

你的交付物是一份"仿真状态审计报告"：给定 Upkie 的 MuJoCo 模型，你需要用代码读取状态向量、执行一个时间步进、并验证能量守恒。面试官会问："你怎样确认仿真结果是物理正确的，而不是看起来像在动但其实是错的？"

具体交付：

1. 一段 Python 脚本，输出 Upkie 在重力作用下自由跌落 1 秒的 `qpos`、`qvel` 时间序列。
2. 一张势能-动能-总能量随时间变化的图（总能量应近似守恒）。
3. 一段 50 字以内的结论，说明为什么能量漂移超过 0.1% 就意味着仿真有问题。

## 学习目标

- **能理解**：区分 MuJoCo 中 `qpos`（广义坐标）、`qvel`（广义速度）、`ctrl`（控制输入）三个数组的含义、维度和单位。
- **能推导**：从 `mj_step` 的输入/输出关系出发，解释一个时间步内发生了什么，包括欧拉积分的误差来源。
- **能实现**：用 `mujoco.mj_step()` 循环推进 1000 步，记录并绘图状态轨迹。

## 前置关卡

完成 `05`（概率、噪声与数字信号）的证据验收，或通过先修诊断。你需要理解：

- NumPy 数组操作（索引、切片、形状）
- 基本的物理概念（位置、速度、力、力矩）
- 什么是采样周期（dt）

## 先观察现象

**错误基线实验**：在运行正式脚本之前，先做一个"零控制"实验。

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.loader import build_mujoco_model

# build_mujoco_model() 会读取 configs/robot/upkie.json 中的 URDF 路径，
# 并自动补充地面、灯光和执行器，返回编译好的 MjModel。
model = build_mujoco_model()
data = mujoco.MjData(model)

# 不给任何控制输入，直接步进 1000 步
for _ in range(1000):
    mujoco.mj_step(model, data)

# 教学简化：这里直接用硬编码索引。实际项目中应使用 joint_map 映射接口：
#   runner = SimulationRunner()
#   hip_adr = runner.joint_map.qposadr["left_hip"]  # 等价于 7
print(f"躯干高度: {data.qpos[2]:.4f} m")
print(f"躯干倾角: {data.qpos[3:7]}")  # 四元数
```

**记录三个观察**：

1. 躯干高度 `qpos[2]` 是多少？如果 Upkie 倒了，高度会接近 0。
2. 四元数 `qpos[3:7]` 的模长是否接近 1.0？如果偏离 1.0 说明数值积分出了问题。
3. `qvel` 中的角速度分量是否在持续增大？这表示机器人在自由跌倒。

**不要先读结论。** 写下你看到的三个现象，再猜测原因。

## 直觉与概念

<!-- upkie-animation:06-core -->

### 状态向量：仿真的"快照"

把 MuJoCo 的仿真状态想象成一张照片——它记录了某一瞬间机器人的所有物理信息：

| 数组 | 含义 | Upkie 维度 | 单位 |
|---|---|---|---|
| `qpos` | 广义坐标（位置） | 13 | m / rad / 无量纲（四元数） |
| `qvel` | 广义速度 | 12 | m/s / rad/s |
| `ctrl` | 控制输入 | 6 | rad（腿部）/ N*m（轮端） |
| `time` | 仿真时间 | 1 | s |

**关键区别**：`qpos` 混合了不同单位——前 3 个元素是平移位置（m），接下来 4 个是四元数（无量纲），后面 6 个是关节角度（rad）。这是新手最容易出错的地方。

### 时间步进：从"照片"到"视频"

`mj_step(model, data)` 做的事情本质上是一个数值积分：

已知：当前状态 (q_k, v_k)，控制输入 u_k，时间步长 dt
计算：下一步状态 (q_{k+1}, v_{k+1})

物理直觉：

1. **力计算**：根据当前位置和速度，算出所有力（重力、弹簧力、接触力、控制力）。
2. **加速度**：用牛顿第二定律 `F = Ma`（这里 M 是质量矩阵，不是标量）算出加速度 `a = M^{-1} F`。
3. **速度更新**：`v_{k+1} = v_k + a * dt`
4. **位置更新**：`q_{k+1} = q_k + v_{k+1} * dt`（注意 MuJoCo 默认用半隐式欧拉）

### 为什么 nq ≠ nv

这是关卡 00 留下的悬念，这里正式解释。

四元数 `q = [w, x, y, z]` 有 4 个分量，但角速度 `ω = [ωx, ωy, ωz]` 只有 3 个分量。这是因为四元数必须满足归一化约束 `|q| = 1`，实际上只有 3 个自由度。MuJoCo 在内部用角速度更新四元数时，会自动重新归一化。

所以 Upkie 的维度拆解是：

qpos (13维):
[0:3]  = 根部平移位置 (x, y, z)，单位 m
[3:7]  = 根部姿态四元数 (w, x, y, z)，无量纲
[7]    = left_hip 角度，单位 rad
[8]    = left_knee 角度，单位 rad
[9]    = left_wheel 角度，单位 rad
[10]   = right_hip 角度，单位 rad
[11]   = right_knee 角度，单位 rad
[12]   = right_wheel 角度，单位 rad
qvel (12维):
[0:3]  = 根部平移速度 (vx, vy, vz)，单位 m/s
[3:6]  = 根部角速度 (ωx, ωy, ωz)，单位 rad/s
[6]    = left_hip 角速度，单位 rad/s
[7]    = left_knee 角速度，单位 rad/s
[8]    = left_wheel 角速度，单位 rad/s
[9]    = right_hip 角速度，单位 rad/s
[10]   = right_knee 角速度，单位 rad/s
[11]   = right_wheel 角速度，单位 rad/s

## 教科书级展开

### 半隐式欧拉积分（MuJoCo 默认）

MuJoCo **默认**的积分器是半隐式欧拉（semi-implicit Euler），也叫辛欧拉（symplectic Euler）。理解它是理解其他积分器的基础。

> **课程选择**：本课程的 `build_mujoco_model()` 将积分器切换为 **RK4**（四阶 Runge-Kutta），见 `sim/loader.py` 中的 `spec.option.integrator = mujoco.mjtIntegrator.mjINT_RK4`。RK4 精度更高（O(dt^4)），能量守恒更好，适合机器人仿真。但理解默认的半隐式欧拉仍然重要——它是 MuJoCo 的基线行为，也是多数开源项目的默认设置。

**公式**：

$$
v_{k+1} = v_{k} + M(q_{k})^{-1} * F(q_{k}, v_{k}, u_{k}) \cdot dt
q_{k+1} = q_{k} + v_{k+1} * dt
$$

**符号拆解**：

| 符号 | 含义 | 单位 |
|---|---|---|
| `q_k` | 第 k 步的广义坐标 | m / rad |
| `v_k` | 第 k 步的广义速度 | m/s / rad/s |
| `u_k` | 第 k 步的控制输入 | rad / N*m |
| `dt` | 时间步长 | s |
| `M(q)` | 质量矩阵（与位形相关） | kg / kg*m^2 |
| `F(q,v,u)` | 广义力向量 | N / N*m |

**物理意义**：先更新速度（用当前位置算出的力），再用新速度更新位置。这比显式欧拉（先更新位置再更新速度）更稳定，因为它是辛结构（symplectic），能近似保持系统的哈密顿量（总能量）。

**设计动机**：半隐式欧拉是辛结构（symplectic），能量误差有界，适合长时间仿真。但它的精度只有 O(dt^2)。RK4 精度更高（O(dt^4)），在课程使用的 dt=0.002 s 下能量漂移更小，但代价是每步需要 4 次力计算，且不是辛积分器（长时间运行可能有缓慢能量漂移）。课程选择 RK4 是因为教学仿真时间短（通常 < 30 秒），精度优势大于辛结构的长期优势。

### 数值算例

假设 Upkie 直立在地面上，初始状态：

- `$q` — [0, 0, 0.3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]  （直立，高度 0.3m）
- `$v` — [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]         （静止）
- `$u` — [0, 0, 0, 0, 0, 0]                              （零控制）
- `$dt` — 0.002 s（MuJoCo 默认 500 Hz）

第一步的物理过程：

1. 重力产生向下的力 `F_z = -mg`（假设 m ≈ 5 kg，`F_z ≈ -49 N`）
2. 如果轮子在地面上，接触力 `F_contact` 向上平衡重力
3. 净力决定加速度，加速度乘以 dt 得到速度增量

如果 Upkie 悬浮在空中（无接触），则：

$$
a_{z} = -g = -9.81 \frac{m}{s}^2
v_{z}(1) = 0 + (-9.81) \cdot 0.002 = -0.01962 \frac{m}{s}
z(1) = 0.3 + (-0.01962) \cdot 0.002 = 0.29996 m
$$

**与代码对齐**：运行一步后检查 `data.qpos[2]` 和 `data.qvel[2]`，应与上述手算一致（误差 < 1e-6）。

### Upkie 代码映射

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.loader import build_mujoco_model

# 加载模型（内部读取 configs/robot/upkie.json → URDF → 编译为 MjModel）
model = build_mujoco_model()
data = mujoco.MjData(model)

# 验证维度
assert model.nq == 13, f"期望 nq=13, 实际 {model.nq}"
assert model.nv == 12, f"期望 nv=12, 实际 {model.nv}"
assert model.nu == 6, f"期望 nu=6, 实际 {model.nu}"

# 读取时间步长（来自 upkie.json 中的 timestep: 0.002）
dt = model.opt.timestep
print(f"时间步长: {dt} s, 仿真频率: {1/dt:.0f} Hz")

# 确认积分器为 RK4（课程配置，非 MuJoCo 默认）
print(f"积分器: {model.opt.integrator}  (4 = RK4)")

# 单步步进
mujoco.mj_step(model, data)
print(f"步进后时间: {data.time:.6f} s")
# 教学简化：这里直接用硬编码索引。实际应使用 joint_map 映射接口。
print(f"躯干位置: {data.qpos[:3]}")
print(f"躯干速度: {data.qvel[:3]}")
```

关键行设计原因：

- `assert model.nq == 13`：维度错误是最常见的仿真 bug 来源。如果模型被修改过但代码没同步，后续的索引操作全部错位。
- `model.opt.timestep`：永远从模型读取 dt，不要硬编码。如果配置文件改了 dt 但代码没改，积分精度和控制器时序都会出错。

## 动手检查点

### 检查点 1：自由落体步进

```powershell
python scripts/02_mujoco_step_demo.py
```

预期输出：

步进完成: sim_time=3.000s, obs_dim=25

脚本使用 `SimulationRunner` 加载模型，以零控制输入步进 3 秒（默认时长），最后输出仿真结束时间和观测维度。可通过 `--duration` 参数调整仿真时长，`--no-viewer` 跳过可视化窗口。

> **扩展练习**：脚本本身不绘制能量守恒图。如果你希望验证能量守恒，可以参考"可视化证据"部分的代码框架，自行修改脚本记录 `qpos`/`qvel` 时间序列并绘制势能-动能-总能量曲线。能量漂移 > 1% 时，检查：
> 1. 是否修改了 `model.opt.timestep` 但没重新计算理论值
> 2. 是否启用了阻尼但没有在能量计算中包含耗散项

### 检查点 2：状态向量索引

```powershell
python -c "
import sys; sys.path.insert(0, 'src')
import mujoco
from upkie_mujoco_course.sim.loader import build_mujoco_model
m = build_mujoco_model()
print('关节名称:', [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(m.njnt)])
print('执行器名称:', [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(m.nu)])
"
```

预期输出 6 个关节名和 6 个执行器名，顺序与 `qpos[7:]` 和 `ctrl` 一致。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 06
```

## 可视化证据

> 以下内容为选做扩展练习，不是检查点的预期输出。`scripts/02_mujoco_step_demo.py` 本身不记录状态轨迹也不绘图。如果你想验证能量守恒，需要自行修改脚本或使用 `SimulationRunner` API 记录每步的 `qpos`/`qvel`，然后绘制下图。

在 `outputs/plots/checkpoint_06.png` 中绘制：

1. **上图**：`qpos[2]`（躯干高度）vs 时间——自由落体应为抛物线。
2. **中图**：`qvel[2]`（躯干垂直速度）vs 时间——应为线性下降。
3. **下图**：势能 + 动能 vs 时间——总能量应为水平线（漂移 < 0.1%）。

```python
import matplotlib.pyplot as plt

# 假设 heights, velocities, times 已记录
KE = 0.5 * mass * np.array(velocities)**2
PE = mass * 9.81 * np.array(heights)
TE = KE + PE

fig, axes = plt.subplots(3, 1, figsize=(8, 10))
axes[0].plot(times, heights); axes[0].set_ylabel('高度 (m)')
axes[1].plot(times, velocities); axes[1].set_ylabel('速度 (m/s)')
axes[2].plot(times, KE, label='动能'); axes[2].plot(times, PE, label='势能')
axes[2].plot(times, TE, 'k--', label='总能量'); axes[2].legend()
plt.savefig('outputs/plots/checkpoint_06.png', dpi=150)
```

## 故障诊断挑战

**破坏**：把 `model.opt.timestep` 从 0.002 改成 0.05（25 倍放大），然后仿真 100 步。

**第一处异常**：四元数模长偏离 1.0 超过 0.01，或者总能量剧烈振荡甚至发散（负能量出现）。

**根因假设**：dt 太大导致数值积分不稳定——无论是半隐式欧拉还是 RK4，过大的时间步长都会让每一步的增量过大，误差被放大甚至发散。

**最小修复**：恢复 `model.opt.timestep = 0.002`。课程已经使用 RK4 积分器（`model.opt.integrator = mujoco.mjtIntegrator.mjINT_RK4`），它在正常 dt 下精度更高；但如果 dt 被改得太大，即使是 RK4 也会不稳定。

**验证**：重新运行后四元数模长偏差 < 1e-6，能量漂移 < 0.1%。

## 三档任务

### 基础任务

- 运行 `scripts/02_mujoco_step_demo.py`，观察输出并理解各字段含义。
- 手写一个表格，列出 `qpos` 和 `qvel` 每个元素的物理含义和单位。

### 岗位挑战

- 给 Upkie 施加一个水平方向的初始速度 `data.qvel[0] = 1.0`，仿真 2 秒，记录运动轨迹。
- 解释为什么 Upkie 会跌倒而不是像小车一样滑出去（提示：倒立摆是不稳定平衡）。
- 改变初始速度从 0.1 到 2.0 m/s，绘制"存活时间 vs 初始速度"曲线。

### 开放探索

- 比较 `timestep = 0.001, 0.002, 0.005, 0.01` 四种设置下的能量漂移和计算时间。
- 写一段 100 字的分析：在什么场景下你会选择更小的 dt？什么场景下可以接受更大的 dt？

## 复盘与面试

1. `qpos` 和 `qvel` 为什么维度不同？

<!-- upkie-qa:06-q1 -->
因为四元数用 4 个数表示 3 自由度的旋转，而角速度只需要 3 个分量。自由基座在 `qpos` 中占 7 维（3 平移 + 4 四元数），在 `qvel` 中只占 6 维（3 线速度 + 3 角速度），所以整个模型 nq 比 nv 多 1。面试时画一个单位球面就能解释：四元数被「模长等于 1」的约束限制在球面上，真正的旋转自由度只有 3 个。
<!-- /upkie-qa -->

2. 半隐式欧拉和显式欧拉的区别是什么？

<!-- upkie-qa:06-q2 -->
更新顺序不同：半隐式欧拉先算新速度 $v_{t+1} = v_t + a \cdot dt$，再用**新速度**更新位置 $x_{t+1} = x_t + v_{t+1} \cdot dt$；显式欧拉用**旧速度**更新位置。半隐式欧拉是辛（symplectic）积分器，长时间仿真能量有界、只在真实值附近小幅振荡；显式欧拉每一步都往系统里注入一点能量，摆动幅度会越摆越大，最终发散。MuJoCo 默认使用半隐式欧拉，就是为了保证长时间仿真的稳定性。
<!-- /upkie-qa -->

3. 怎样判断仿真结果是物理正确的？

<!-- upkie-qa:06-q3 -->
用已知物理定律做三个检查：(a) 自由落体轨迹与解析解 `z = z_0 - 0.5*g*t^2` 一致（逐点误差在积分精度范围内）；(b) 四元数模长在整个仿真过程中保持 1.0（旋转表示没有被数值误差破坏）；(c) 无外力、无接触时系统总能量（动能 + 势能）守恒。这三个检查各自覆盖平动积分、姿态表示和积分器能量行为，任何一项失败都说明仿真配置或步进代码有问题。
<!-- /upkie-qa -->

4. dt 太小有什么问题？

<!-- upkie-qa:06-q4 -->
计算量与 dt 成反比线性增长。如果 dt = 0.0001 s，仿真 10 秒需要 100000 步，每一步都要组装并求解一次线性方程组 `M^{-1}F`（正向动力学），在关节多、接触多的复杂模型上会非常慢。而精度收益是递减的：dt 小到一定程度后，浮点舍入误差反而开始累积。所以 dt 的选择是精度与速度的权衡，MuJoCo 默认的 0.002 s 对多数机器人模型已经足够。
<!-- /upkie-qa -->

## 下一关

关卡 `07`（URDF、MJCF 与模型审计）会假设你已经理解 `qpos`/`qvel` 的维度和索引含义。本关产出的状态向量索引表将成为下一关审计模型文件时的对照基准——如果 XML 中定义的关节顺序与你的索引表不一致，你需要在下一关发现并修复。
