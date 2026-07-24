# 09 执行器、传感器与单位

> 建设状态：可执行
> 阶段：机器人仿真
> 作品集目录：`outputs/portfolio/09`

## 岗位任务

你的交付物是一份"执行器与传感器契约文档"：用表格和代码明确 Upkie 每个执行器的输入类型、单位、范围和物理效果，每个传感器的输出维度和含义。面试官会问："你发给电机的值是角度还是力矩？单位是什么？如果搞混了会怎样？"

具体交付：

1. 一张执行器映射表：`ctrl[i]` 对应哪个关节，输入是 rad 还是 N*m，范围是多少。
2. 一张传感器映射表：`sensordata[j:k]` 对应哪个传感器，输出什么物理量。
3. 一段验证代码：给每个执行器施加已知输入，测量实际输出，与预期对比。

## 学习目标

- **能理解**：区分 position actuator（角度输入，rad）和 motor actuator（力矩输入，N*m），理解两者在 MuJoCo 内部的计算路径差异。
- **能推导**：给定一个控制输入 `ctrl = [0.1, 0, 0, 0, 0.5, -0.5]`，手算每个执行器产生的实际力矩。
- **能实现**：编写代码读取传感器数据，并验证 IMU、关节编码器和力传感器的输出与 `qpos`/`qvel` 一致。

## 前置关卡

完成 `08`（自由基座与空间姿态）的证据验收。你需要理解：

- `qpos` 和 `qvel` 的维度与索引
- 四元数表示和角速度的体坐标系含义
- MJCF 中执行器标签的基本结构

## 先观察现象

**错误基线实验**：把轮端力矩控制器的输入从 N*m 误当作 rad/s 来用。

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.loader import build_mujoco_model

model = build_mujoco_model()
data = mujoco.MjData(model)

# 教学简化：这里直接用硬编码索引。实际应使用 actuator_map / joint_map：
#   left_wheel_id = runner.actuator_map.ids["left_wheel_motor"]   # → ctrl[4]
#   left_wheel_vel = runner.joint_map.dofadr["left_wheel"]        # → qvel[8]
#   right_wheel_vel = runner.joint_map.dofadr["right_wheel"]      # → qvel[11]

# 错误：想设置轮速为 10 rad/s，但 ctrl 期望的是力矩 N*m
data.ctrl[4] = 10.0   # 实际：超出 ctrlrange [-1, 1] 会被裁剪
data.ctrl[5] = 10.0

for _ in range(500):
    mujoco.mj_step(model, data)

print(f"左轮角速度: {data.qvel[8]:.4f} rad/s")    # 教学简化：硬编码索引
print(f"右轮角速度: {data.qvel[11]:.4f} rad/s")   # 教学简化：硬编码索引
# 预期：由于裁剪到 1.0 N*m，加速比预期慢得多
```

**记录三个观察**：

1. 轮子实际受到的力矩是 1.0 N*m 还是 10.0 N*m？（答：被裁剪到 1.0）
2. 如果没注意裁剪，你会误以为电机坏了或模型错了。
3. 这就是单位混淆的危害：数值对了但物理意义全错。

## 直觉与概念

<!-- upkie-animation:09-core -->

### 执行器：控制器的"手"

执行器（actuator）是控制器影响物理世界的唯一通道。你可以把它想象成机器人的"肌肉"——控制器发出电信号，执行器把它变成力或位移。

Upkie 的 6 个执行器分成两类：

ctrl[0]: left_hip_servo     → 目标角度 (rad)     → 内部 PD 产生力矩 (kp=40)
ctrl[1]: left_knee_servo    → 目标角度 (rad)     → 内部 PD 产生力矩 (kp=60)
ctrl[2]: right_hip_servo    → 目标角度 (rad)     → 内部 PD 产生力矩 (kp=40)
ctrl[3]: right_knee_servo   → 目标角度 (rad)     → 内部 PD 产生力矩 (kp=60)
ctrl[4]: left_wheel_motor   → 力矩指令 (N*m)     → 直接施加力矩 (范围 [-1, 1])
ctrl[5]: right_wheel_motor  → 力矩指令 (N*m)     → 直接施加力矩 (范围 [-1, 1])

### 传感器：控制器的"眼"

传感器（sensor）是控制器感知物理状态的通道。

> **重要说明**：当前 `configs/robot/upkie.json` 的 `sensor_names` 列出了 **7 个 MuJoCo 传感器**（3 个 IMU 通道 `imu_accelerometer`/`imu_gyroscope`/`imu_orientation`，以及左右轮的位置与速度编码器）。在此之上，`sensor_contract` 定义了控制器实际读取的 **11 类观测字段**：既包含从 MuJoCo 状态（qpos/qvel/xpos/xmat）直接推导的基座与关节量，也包含来自上述传感器的 IMU 与轮编码器读数。字段的权威定义以 `configs/robot/upkie.json` 的 `sensor_contract.fields` 为准。

| 观测字段 | 来源 | 维度 | 物理量 | 单位 |
|---|---|---|---|---|
| base_position | xpos（世界坐标） | 3 | 基座位置 | m |
| base_quaternion | xmat → quat | 4 | 基座姿态（wxyz） | 无量纲 |
| base_linear_velocity | qvel[0:3] | 3 | 基座线速度 | m/s |
| base_angular_velocity | qvel[3:6] | 3 | 基座角速度 | rad/s |
| joint_position | qpos[7:13] | 6 | 各关节角度 | rad |
| joint_velocity | qvel[6:12] | 6 | 各关节角速度 | rad/s |
| imu_accelerometer | sensordata（IMU） | 3 | 基座线加速度 | m/s^2 |
| imu_gyroscope | sensordata（IMU） | 3 | 基座角速度 | rad/s |
| imu_orientation | sensordata（IMU） | 4 | 基座姿态（wxyz） | 无量纲 |
| wheel_encoder_position | sensordata（轮编码器） | 2 | 左右轮角度 | rad |
| wheel_encoder_velocity | sensordata（轮编码器） | 2 | 左右轮角速度 | rad/s |

如果将来需要在 MJCF 中添加硬件传感器（如 IMU），可以在 `<sensor>` 标签中定义：

| 传感器类型 | 输出维度 | 物理量 | 单位 |
|---|---|---|---|
| accelerometer | 3 | 体坐标系加速度 | m/s^2 |
| gyro | 3 | 体坐标系角速度 | rad/s |
| magnetometer | 3 | 磁场方向 | T |

### 单位一致性：最容易犯也最难查的错误

单位错误不会导致程序崩溃——它们只会让数值"看起来差不多但不对"。这是最危险的 bug 类型。

常见陷阱：

1. **角度 vs 弧度**：`ctrl[0] = 30` 不是 30 度，是 30 rad（约 1719 度）。
2. **N*m vs N*cm**：真实电机的力矩常以 N*cm 或 kg*cm 标注，MuJoCo 统一用 N*m。
3. **rad/s vs RPM**：轮速常以 RPM 标注，`100 RPM = 10.47 rad/s`。

## 教科书级展开

### Position Actuator 的内部计算

**公式**：

$$
\tau = k_{p} \cdot (ctrl - q_{\text{current}}) - kv \cdot qvel_{\text{current}}
$$

**符号拆解**：

| 符号 | 含义 | 单位 |
|---|---|---|
| `tau` | 输出力矩 | N*m |
| `kp` | 位置增益 | N*m/rad |
| `kv` | 速度增益（阻尼） | N*m*s/rad |
| `ctrl` | 目标角度 | rad |
| `q_current` | 当前关节角度 | rad |
| `qvel_current` | 当前关节角速度 | rad/s |

**设计动机**：这就是一个 PD 控制器。MuJoCo 把 PD 控制内置到 position actuator 中，因为你通常不关心腿部关节的力矩细节，只关心"把腿摆到这个角度"。

**数值算例**：

假设 kp = 40 N*m/rad（left_hip_servo 的实际值）
- `$ctrl` — 0.5 rad（目标角度约 28.6 度）
q_current = 0.3 rad
qvel_current = 0.1 rad/s
$$
\tau = 40 \cdot (0.5 - 0.3) - kv \cdot 0.1
    = 40 \cdot 0.2 - kv \cdot 0.1
    = 8.0 - kv \cdot 0.1 N \cdot m
$$

> 注意：不同关节的 kp 不同——hip 为 40，knee 为 60。这是 `configs/robot/upkie.json` 中 `position_actuators` 的定义。MuJoCo 的 position actuator 中 kv（速度阻尼）默认由 kp 自动推导。

### Motor Actuator 的直接输出

**公式**：

$$
\tau = clip(ctrl, ctrlrange_{\text{min}}, ctrlrange_{\text{max}}) \cdot gain
$$

对于 Upkie 的轮端：`gain = 1`，`ctrlrange = [-1, 1]`。

- `$ctrl` — 0.5 N*m  →  tau = 0.5 N*m（直接输出）
- `$ctrl` — 2.0 N*m  →  tau = 1.0 N*m（被裁剪）
ctrl = -0.3 N*m →  tau = -0.3 N*m

**设计动机**：轮端需要精确的力矩控制（用于平衡和速度跟踪），不适合用 position actuator 的间接 PD。

### 传感器数据读取

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.runner import SimulationRunner

runner = SimulationRunner()
runner.reset("stand")

# 基座位姿/速度等观测直接从 qpos/qvel 状态向量读取；
# IMU 与轮编码器读数则来自 sensor_names 中定义的 MuJoCo 传感器。

# 方式一：直接从状态向量读取（教学简化：硬编码索引）
# 实际应使用 runner.joint_map 获取正确地址。
print(f"基座位置: {runner.data.qpos[0:3]}")
print(f"基座姿态（四元数 wxyz）: {runner.data.qpos[3:7]}")
print(f"基座线速度: {runner.data.qvel[0:3]}")
print(f"基座角速度: {runner.data.qvel[3:6]}")

# 方式二：使用 SimulationRunner 的高层接口
obs = runner.observation()  # 拼接 qpos + qvel，共 25 维
print(f"观测向量维度: {obs.shape}")

# 方式三：使用 posture_state() 获取语义化状态
state = runner.posture_state()
print(f"俯仰角: {state['pitch']:.4f} rad")
print(f"前向速度: {state['forward_velocity']:.4f} m/s")

# 读取 sensor_names 中定义的 MuJoCo 传感器可用 read_sensors()：
# from upkie_mujoco_course.sim.sensors import read_sensors
# sensor_values = read_sensors(runner.data, runner.sensor_map)
```

关键行设计原因：

- `runner.observation()`：返回 `np.concatenate([qpos, qvel])`，是最常用的观测接口。
- `runner.posture_state()`：返回语义化字典，包含 pitch、forward_velocity 等高层状态量，适合控制器使用。
- `runner.joint_map.qposadr / dofadr`：按名称查地址，避免硬编码索引。当模型关节顺序变化时，硬编码索引会指向错误的数据。

### 执行器验证代码

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.loader import build_mujoco_model

model = build_mujoco_model()
data = mujoco.MjData(model)

# 教学简化：这里直接用硬编码索引。实际应使用 actuator_map / joint_map：
#   left_wheel_ctrl = runner.actuator_map.ids["left_wheel_motor"]   # → 4
#   left_wheel_dof = runner.joint_map.dofadr["left_wheel"]           # → 8
#   right_wheel_dof = runner.joint_map.dofadr["right_wheel"]         # → 11

# 验证轮端力矩
data.ctrl[4] = 0.5   # 左轮 0.5 N*m
data.ctrl[5] = -0.5  # 右轮 -0.5 N*m

# 记录初始角速度
w_left_0 = data.qvel[8]
w_right_0 = data.qvel[11]

# 步进 1 步
mujoco.mj_step(model, data)

# 计算角加速度
dt = model.opt.timestep
alpha_left = (data.qvel[8] - w_left_0) / dt
alpha_right = (data.qvel[11] - w_right_0) / dt

print(f"左轮角加速度: {alpha_left:.4f} rad/s^2")
print(f"右轮角加速度: {alpha_right:.4f} rad/s^2")
# 预期：左右轮角加速度方向相反
```

## 动手检查点

### 检查点 1：执行器映射验证

```powershell
python scripts/01_check_model.py
```

预期输出中执行器部分：

执行器列表:
[0] left_hip_servo: position, kp=40
[1] left_knee_servo: position, kp=60
[2] right_hip_servo: position, kp=40
[3] right_knee_servo: position, kp=60
[4] left_wheel_motor: motor, range=[-1, 1]
[5] right_wheel_motor: motor, range=[-1, 1]

### 检查点 2：状态观测一致性

```powershell
python -c "
import sys; sys.path.insert(0, 'src')
import mujoco, numpy as np
from upkie_mujoco_course.sim.runner import SimulationRunner
runner = SimulationRunner()
runner.reset('stand')
print(f'XML 传感器数量: {runner.model.nsensor}  (当前配置为 0)')
print(f'观测向量维度: {runner.observation().shape[0]}  (= nq + nv = 13 + 12)')
state = runner.posture_state()
for k, v in state.items():
    print(f'  {k}: {v}')
"
```

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 09
```

## 可视化证据

在 `outputs/plots/checkpoint_09.png` 中绘制：

1. **左图**：给 left_hip 设置 `ctrl=0.5 rad`，绘制关节角度随时间的变化（应指数收敛到 0.5）。
2. **右图**：给左轮设置 `ctrl=0.5 N*m`，绘制轮子角速度随时间的变化（应线性增长）。

## 故障诊断挑战

**破坏**：把 `ctrl[4]`（左轮力矩）和 `ctrl[0]`（左髋角度）的赋值交换——把角度值发给轮端，把力矩值发给腿部。

```python
# 错误交换（教学简化：硬编码索引）
data.ctrl[0] = 0.5  # left_hip_servo: 本意是力矩，但 position actuator 当作角度
data.ctrl[4] = 0.1  # left_wheel_motor: 本意是角度，但 motor actuator 当作力矩
```

**第一处异常**：腿部关节几乎没有反应（0.5 rad 的目标角度与当前角度差很小，产生的力矩微乎其微），而轮子施加了 0.1 N*m 的力矩（比预期的力矩小得多）。

**根因假设**：position actuator 的输入是角度，0.5 rad 作为目标角度只会产生微小的 PD 力矩；motor actuator 的输入是力矩，0.1 太小不足以明显加速轮子。

**最小修复**：恢复正确的 ctrl 索引映射。

**验证**：轮子有明显加速，腿部关节运动到预期角度。

## 三档任务

### 基础任务

- 手动绘制执行器映射表和传感器映射表。
- 验证每个执行器的输入/输出关系与文档一致。

### 岗位挑战

- 设计一个"执行器指纹"测试：给每个执行器分别施加脉冲输入，记录响应曲线，证明 6 个执行器互不串扰。
- 分析 position actuator 的 kp 对响应速度的影响：绘制 `kp = 10, 50, 100, 500` 时的阶跃响应对比。

### 开放探索

- 比较 Upkie 的执行器配置与 Boston Dynamics Spot 或 Unitree Go1 的执行器配置（从公开文档中查找）。
- 写一段 200 字分析：为什么腿部用位置控制而轮端用力矩控制？如果全部用力矩控制会怎样？

## 复盘与面试

1. **position actuator 和 motor actuator 的核心区别？** position 内部有 PD 控制器，输入是目标角度；motor 直接输出力矩，输入是力矩值。混用会导致量级差几十倍的错误（hip kp=40，knee kp=60）。

2. **ctrl 值被裁剪时你怎么知道？** 检查 `data.ctrl` 和 `data.actuator_force` 的关系。如果 ctrl 请求 2.0 但 ctrlrange 是 [-1, 1]，实际力矩只有 1.0。日志中应该记录裁剪事件。

3. **观测数据和 qpos/qvel 的关系？** 当前配置通过 `sensor_contract` 直接从 qpos/qvel 读取状态，无 XML 传感器。如果将来添加 IMU 传感器（加速度计、陀螺仪），其数据是额外的物理量，不能从 qpos/qvel 直接推导（因为加速度包含重力分量和科里奥利力）。

4. **为什么轮端的 ctrlrange 是 [-1, 1] N*m？** 这是真实电机的力矩限制。超过这个范围的力矩在物理上无法产生，仿真中裁剪是为了反映这个约束。

## 下一关

关卡 `10`（轮地接触、摩擦与碰撞）会假设你已经理解执行器的输出如何变成物理力。本关确认了"力矩经过执行器变成关节力"这条路径，下一关将分析"轮子的力矩经过接触变成地面反作用力"这条更复杂的路径——如果摩擦力不够，再大的轮端力矩也无法让机器人前进。
