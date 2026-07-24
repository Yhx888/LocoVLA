# 10 轮地接触、摩擦与碰撞

> 建设状态：可执行
> 阶段：机器人仿真
> 作品集目录：`outputs/portfolio/10`

## 岗位任务

你的交付物是一份"接触模型验证报告"：证明 Upkie 的轮地接触在仿真中产生的摩擦力、法向力和滚动行为与物理预期一致。面试官会问："你怎么知道仿真里的轮子没有打滑？如果摩擦系数改了一半，机器人还能站稳吗？"

具体交付：

1. 一段代码，测量轮子在静止时的法向接触力，验证 `F_n = mg/2`（两轮分担体重）。
2. 一张"摩擦锥"可视化图：在不同摩擦系数下，切向力与法向力的关系。
3. 一组实验数据，展示轮端力矩从小到大时，从纯滚动到打滑的转变点。

## 学习目标

- **能理解**：解释 Coulomb 摩擦模型 `|F_t| <= mu * F_n` 的物理意义，区分静摩擦和动摩擦在仿真中的实现。
- **能推导**：从接触力公式出发，计算 Upkie 在斜坡上不滑动所需的最大坡度角。
- **能实现**：用 MuJoCo 的 `data.contact` 读取接触点信息，提取法向力和切向力。

## 前置关卡

完成 `09`（执行器、传感器与单位）的证据验收。你需要理解：

- 轮端力矩的单位是 N*m，范围是 [-1, 1]
- 执行器输出力矩和接触力之间的因果关系
- MuJoCo 模型中 geom 标签定义碰撞几何

## 先观察现象

**错误基线实验**：把地面摩擦系数设为 0（完全光滑），然后尝试让 Upkie 用轮子前进。

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
from upkie_mujoco_course.sim.loader import build_mujoco_model

model = build_mujoco_model()
data = mujoco.MjData(model)

# 教学简化：这里直接修改地面摩擦系数。
# 实际配置中地面摩擦为 [1.2, 0.05, 0.01]（滑动、扭转、滚动）。

# 找到地面 geom 并修改摩擦系数
floor_geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
model.geom_friction[floor_geom_id] = [0.0, 0.0, 0.0]

# 教学简化：硬编码索引。实际应使用 actuator_map / joint_map。
# 给轮子施加力矩
data.ctrl[4] = 1.0  # left_wheel_motor
data.ctrl[5] = 1.0  # right_wheel_motor

for _ in range(500):
    mujoco.mj_step(model, data)

print(f"机器人位移: {data.qpos[0]:.4f} m")
print(f"轮子角速度: {data.qvel[8]:.4f} rad/s")  # left_wheel dofadr
# 预期：轮子高速旋转但机器人原地不动（打滑）
```

**记录三个观察**：

1. 轮子是否在高速旋转？（是——力矩全部变成了轮子的角加速度）
2. 机器人躯干是否水平移动？（否——没有摩擦力提供水平推力）
3. 这和现实中的冰面行为一致吗？

## 直觉与概念

<!-- upkie-animation:10-core -->

### 摩擦力：轮子与地面的"握手"

想象你穿溜冰鞋站在冰面上推墙——你的手对墙施加力，但脚底太滑，力无法传递到地面，你只是向后滑。轮子也一样：轮端力矩想推动机器人前进，但如果摩擦力不够，轮子只会空转。

**Coulomb 摩擦模型**：

$$
|F_{t}| \le  \mu \cdot F_{n}
$$
- `$F_t` — 切向力（平行于接触面）
- `$F_n` — 法向力（垂直于接触面）
- `$mu` — 摩擦系数

- 静摩擦：`|F_t| < mu_s * F_n`，轮子不滑动，纯滚动
- 动摩擦：`|F_t| = mu_d * F_n`，轮子打滑，力被限制

### MuJoCo 的接触模型

MuJoCo 使用基于约束的接触模型：

1. **碰撞检测**：检查哪些 geom 对相互穿透
2. **接触生成**：为每对碰撞的 geom 创建接触点（contact point）
3. **约束求解**：用优化方法（默认为 Newton 法）求解接触力，使得不穿透约束和摩擦锥约束同时满足

data.ncon     → 当前接触点数量
data.contact  → 接触点数组
.geom1, .geom2   → 接触的 geom 对
.pos             → 接触点位置 (3D)
.frame           → 接触坐标系 (法向 + 两个切向)
.friction        → 摩擦系数
.efc_address     → 约束在 efc 数组中的起始索引

### 滚动 vs 滑动

**纯滚动条件**：轮子边缘线速度 = 躯干前进速度

$$
v_{\text{body}} = omega_{\text{wheel}} * r_{\text{wheel}}
$$
- `$v_body` — 躯干 X 方向速度 (m/s)
- `$omega_wheel` — 轮子角速度 (rad/s)
- `$r_wheel` — 轮子半径 (m)

当轮端力矩过大导致 `|F_t| > mu * F_n` 时，纯滚动条件被破坏，轮子开始打滑。

## 教科书级展开

### 法向力计算

**假设**：Upkie 静止直立，两个轮子均匀分担体重。

$$
F_{n,\text{left}} = F_{n,\text{right}} = m \cdot \frac{g}{2}
$$
- `$m` — 5.0 kg（Upkie 总质量，从配置读取）
g = 9.81 m/s^2
$$
F_{n} = 5.0 \cdot 9.81 / 2 = 24.525 N
$$

**验证方法**：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.loader import build_mujoco_model

model = build_mujoco_model()
data = mujoco.MjData(model)

# 静止状态
mujoco.mj_forward(model, data)

# 读取接触力
for i in range(data.ncon):
    c = data.contact[i]
    # 获取接触力（法向 + 两个切向）
    force = np.zeros(6)
    mujoco.mj_contactForce(model, data, i, force)
    fn = force[0]  # 法向力
    ft1 = force[1]  # 切向力 1
    ft2 = force[2]  # 切向力 2
    print(f"接触 {i}: F_n={fn:.3f} N, F_t1={ft1:.3f} N, F_t2={ft2:.3f} N")

# 验证总法向力 ≈ mg
total_fn = 0.0
for i in range(data.ncon):
    force = np.zeros(6)
    mujoco.mj_contactForce(model, data, i, force)
    total_fn += force[0]
total_mass = sum(model.body(i).mass[0] for i in range(model.nbody))
print(f"总法向力: {total_fn:.3f} N")
print(f"重力: {total_mass * 9.81:.3f} N")
```

### 摩擦锥与打滑临界点

**公式**：

不打滑条件: tau / r <= mu * F_n
- `$tau` — 轮端力矩 (N*m)
- `$r` — 轮子半径 (m)
- `$mu` — 摩擦系数
- `$F_n` — 法向力 (N)
临界力矩: tau_max = mu * F_n * r

**数值算例**：

- `$mu` — 1.2（Upkie 地面滑动摩擦系数，来自 loader.py 中 floor.friction = [1.2, 0.05, 0.01]）
F_n = 24.525 N
- `$r` — 0.06 m（轮子半径，来自 upkie.json 的 wheel_radius_fallback）
$$
tau_{\text{max}} = 1.2 \cdot 24.525 \cdot 0.06 = 1.766 N \cdot m
$$

因为 Upkie 轮端 `ctrlrange = [-1, 1]` N*m，最大力矩 1.0 < 1.766，所以在正常摩擦条件下**不会打滑**。高摩擦系数（1.2）是有意选择的，确保轮子在各种控制输入下都能保持纯滚动。

### 斜坡最大坡度

**推导**：

在坡度角 alpha 的斜坡上:
重力分量: mg * sin(alpha)（沿坡向下）
法向力:   mg * cos(alpha) / 2（每个轮子）
最大摩擦: mu * mg * cos(alpha) / 2 * 2 = mu * mg * cos(alpha)
不打滑条件: mg * sin(alpha) <= mu * mg * cos(alpha)
化简: tan(alpha) <= mu
即:   alpha <= arctan(mu)

**数值算例**：

- `$mu` — 1.2（Upkie 默认地面） → alpha_max = arctan(1.2) = 50.2 度
- `$mu` — 0.3（湿滑地面）     → alpha_max = arctan(0.3) = 16.7 度

## 动手检查点

### 检查点 1：静止法向力验证

```powershell
python -c "
import sys; sys.path.insert(0, 'src')
import mujoco, numpy as np
from upkie_mujoco_course.sim.loader import build_mujoco_model
m = build_mujoco_model()
d = mujoco.MjData(m)
mujoco.mj_forward(m, d)
print(f'接触点数量: {d.ncon}')
total_fn = 0.0
for i in range(d.ncon):
    f = np.zeros(6)
    mujoco.mj_contactForce(m, d, i, f)
    total_fn += f[0]
    print(f'  接触 {i}: F_n = {f[0]:.3f} N')
print(f'总法向力: {total_fn:.3f} N')
mass = sum(m.body(i).mass[0] for i in range(m.nbody))
print(f'总质量: {mass:.3f} kg, 重力: {mass*9.81:.3f} N')
"
```

预期：总法向力 ≈ 总重力，误差 < 1%。

### 检查点 2：打滑实验

请在 Python 中执行以下代码，观察不同摩擦系数和力矩下的打滑行为：

```python
import sys
sys.path.insert(0, 'src')
import mujoco
import numpy as np
from upkie_mujoco_course.sim.loader import build_mujoco_model

model = build_mujoco_model()

# 测试不同摩擦系数
for mu in [1.2, 0.3]:
    # 重新加载模型以重置状态
    model = build_mujoco_model()
    data = mujoco.MjData(model)

    # 修改地面摩擦系数
    floor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
    model.geom_friction[floor_id] = [mu, 0.05, 0.01]

    tau_critical = mu * (5.0 * 9.81 / 2) * 0.06
    print(f"摩擦系数 = {mu}, 临界力矩 = {tau_critical:.3f} N*m")

    for ctrl_val in [0.5, 0.8, 1.0]:
        data = mujoco.MjData(model)
        model.geom_friction[floor_id] = [mu, 0.05, 0.01]
        data.ctrl[4] = ctrl_val
        data.ctrl[5] = ctrl_val
        for _ in range(500):
            mujoco.mj_step(model, data)
        print(f"  ctrl = {ctrl_val}: x = {data.qpos[0]:.4f} m")
    print()
```

预期输出：

摩擦系数 = 1.2, 临界力矩 = 1.766 N*m（超过 ctrlrange [-1, 1]，所以不会打滑）
ctrl = 0.5: x = 0.xx m
ctrl = 0.8: x = 0.xx m
- `$ctrl` — 1.0: x = 0.xx m（最大力矩仍在摩擦锥内）
摩擦系数 = 0.3, 临界力矩 = 0.441 N*m
- `$ctrl` — 0.5: x = 0.xx m（超过临界力矩，轮子打滑）
ctrl = 0.8: x = 0.xx m
ctrl = 1.0: x = 0.xx m

注意：摩擦系数 1.2 时最大力矩 1.0 N*m 仍在摩擦锥内，不会打滑；降低到 0.3 后临界力矩仅 0.441 N*m，ctrl=0.5 以上即出现打滑。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 10
```

## 可视化证据

在 `outputs/plots/checkpoint_10.png` 中绘制：

1. **左图**：法向力 vs 时间——静止时应为恒定值，步进后可能有微小波动。
2. **中图**：轮端力矩 vs 前进速度——展示线性区（纯滚动）和饱和区（打滑）。
3. **右图**：不同摩擦系数下的摩擦锥可视化（切向力 vs 法向力的散点图）。

## 故障诊断挑战

**破坏**：把两个轮子的 geom 半径从正确值缩小 10 倍（比如从 0.06 改成 0.006）。

**第一处异常**：机器人静止时高度显著降低（轮子变小了），且轮端力矩产生的加速度异常增大（因为 `a = tau / (I/r) = tau * r / I`，r 缩小后力矩臂变短但转动惯量也变了）。更关键的异常：轮子角速度远大于预期，因为纯滚动条件 `v = omega * r` 中 r 变小了。

**根因假设**：轮子半径影响接触点位置、力矩臂和纯滚动条件，三者同时改变。

**最小修复**：恢复正确的轮子半径。

**验证**：静止高度、法向力、前进速度均恢复到预期值。

## 三档任务

### 基础任务

- 验证静止时总法向力 = 重力，截图保存。
- 手动计算打滑临界力矩，与仿真结果对比。

### 岗位挑战

- 在斜坡上（修改地面 geom 的倾斜角）测量最大不打滑坡度，与 `arctan(mu)` 的理论值对比。
- 设计一个"摩擦系数估计器"：通过施加不同力矩并观察是否打滑，反推当前摩擦系数。

### 开放探索

- 研究 MuJoCo 的三种接触求解器（PGS、CG、Newton），比较它们在不同接触场景下的精度和速度。
- 写一段 200 字分析：为什么 MuJoCo 选择"软约束"（允许微小穿透）而不是"硬约束"（严格不穿透）？

## 复盘与面试

1. **摩擦锥是什么？** 法向力和切向力的比值约束。切向力不能超过 `mu * F_n`，否则接触点滑动。在 3D 中，这个约束在 `F_t1-F_t2-F_n` 空间中形成一个锥。

2. **打滑时第一个可观测信号是什么？** 轮子角速度远大于 `v_body / r_wheel`。如果你监控这个比值，就能实时检测打滑。

3. **为什么仿真中法向力不完全等于 mg/2？** 因为数值积分的误差和接触模型的"软约束"特性。每次步进后接触力可能有微小振荡，这是正常的。

4. **摩擦系数设错了对控制器的影响？** 如果仿真中 mu 远大于真实值，控制器会以为有更大的力矩裕量，在真实机器人上可能打滑摔倒。这就是域随机化（关卡 29）要解决的问题之一。

## 下一关

关卡 `11`（可替换机器人模型契约）会假设你已经理解接触模型对控制的影响。本关产出的摩擦力分析将成为下一关设计"模型替换后接触行为一致性验证"的基础——如果你换一个不同轮子尺寸的机器人模型，摩擦锥约束会完全不同。
