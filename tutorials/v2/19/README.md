# 19 传感器误差与互补滤波

> 建设状态：可执行
> 阶段：状态估计与优化
> 作品集目录：`outputs/portfolio/19`

## 岗位任务

你的交付物是一份"传感器融合验证报告"：给 Upkie 的 IMU 数据注入已知噪声，用互补滤波器融合加速度计和陀螺仪，并证明融合后的角度估计比单一传感器更准确。面试官会问："为什么不能只用加速度计或只用陀螺仪？互补滤波器的 alpha 怎么选？"

具体交付：

1. 一段代码，生成带噪声的 IMU 仿真数据（加速度计 + 陀螺仪）。
2. 一张三行图：真实角度、加速度计估计、陀螺仪积分估计、互补滤波估计。
3. 一段分析，解释 alpha 从 0.9 到 0.99 变化时，高频噪声和低频漂移的权衡。

## 学习目标

- **能理解**：解释加速度计的高频噪声和陀螺仪的低频漂移，以及互补滤波如何利用两者互补的频谱特性。
- **能推导**：从互补滤波公式出发，推导其传递函数，证明它是高通和低通的加权组合。
- **能实现**：在仿真数据上实现互补滤波器，并用 RMSE 评估估计精度。

## 前置关卡

完成 `18`（速度、偏航、高度与动作接口）的证据验收。你需要理解：

- IMU 传感器的输出（加速度计 3 轴 + 陀螺仪 3 轴）
- 角度和角速度的关系（积分/微分）
- 采样频率和时间步长 dt

## 先观察现象

**错误基线实验**：只用加速度计或只用陀螺仪估计 Upkie 的俯仰角。

```python
import numpy as np

# 模拟 10 秒数据，dt = 0.002 s
seed = 19
rng = np.random.default_rng(seed)
dt = 0.002
t = np.arange(0, 10, dt)
true_angle = 0.1 * np.sin(2 * np.pi * 0.5 * t)  # 0.5 Hz 正弦

# 加速度计：真实角度 + 高频噪声
accel_angle = true_angle + rng.normal(0, 0.05, len(t))

# 陀螺仪：积分角速度 + 低频漂移
gyro_rate = np.gradient(true_angle, dt) + 0.001  # 0.001 rad/s 偏差
gyro_angle = np.cumsum(gyro_rate * dt)

print(f"加速度计 RMSE: {np.sqrt(np.mean((accel_angle - true_angle)**2)):.4f}")
print(f"陀螺仪 RMSE: {np.sqrt(np.mean((gyro_angle - true_angle)**2)):.4f}")
```

**记录观察**：加速度计的 RMSE 受噪声影响大（约 0.05），陀螺仪的 RMSE 随时间增长（漂移累积）。

## 直觉与概念

<!-- upkie-animation:19-intuition -->

### 两个不完美的传感器

**加速度计**：通过测量重力方向来推断倾斜角。

- 优点：长期准确（重力方向不变）
- 缺点：对振动和加速度极其敏感（高频噪声大）
- 类比：像一个总是说真话但说话很大声的人——信息对但噪音大

**陀螺仪**：测量旋转角速度，通过积分得到角度。

- 优点：短期精确（对角速度变化敏感）
- 缺点：积分会累积偏差（低频漂移）
- 类比：像一个走得很准但方向稍微偏的人——短时间没问题，走远了就偏了

**互补滤波**：把两者的优点结合——短期信任陀螺仪（精确），长期用加速度计校正（准确）。

### 互补滤波公式

$$
theta_{k} = \alpha \cdot (theta_{k-1} + omega_{k} * dt) + (1 - \alpha) \cdot theta_{\text{accel},k}
$$
- `theta_k` — 第 k 步的融合角度估计
- `theta_{k-1}` — 第 k-1 步的融合角度估计
- `omega_k` — 陀螺仪测量的角速度 (rad/s)
- `theta_accel_k` — 加速度计估计的角度 (rad)
- `dt` — 采样周期 (s)
- `alpha` — 融合系数，通常 0.95-0.99

**直觉**：alpha 接近 1 时更信任陀螺仪（短期精确），alpha 接近 0 时更信任加速度计（长期准确）。

## 教科书级展开

<!-- upkie-animation:19-parameter -->

### 传递函数分析

**公式**（z 域）：

H_gyro(z) = alpha * z / (z - alpha)      # 高通滤波器
H_accel(z) = (1 - alpha) / (z - alpha)   # 低通滤波器
验证: H_gyro(z) + H_accel(z) = (alpha*z + 1 - alpha) / (z - alpha)
当 z=1 (DC): H_gyro(1) + H_accel(1) = 1  → 全通（信号无损失）

**符号拆解**：

| 符号 | 含义 | 典型值 |
|---|---|---|
| `alpha` | 融合系数 | 0.95-0.99 |
| `z` | z 变换变量 | 复数 |
| `dt` | 采样周期 | 0.002 s |

**截止频率**：

f_c ≈ (1 - alpha) / (2 * pi * dt)        # 一阶近似，alpha 接近 1 时成立
$$
\alpha = 0.98, dt = 0.002:
f_{c} \approx  0.02 / (2 * \pi \cdot 0.002) \approx  1.59 Hz
$$

> **精确公式**：上式是 `(1 - alpha)` 对 `-ln(alpha)` 的一阶泰勒近似。精确截止频率为 `f_c = -ln(alpha) / (2 * pi * dt)`。当 alpha = 0.98 时两者差异不到 1%（近似 1.59 Hz vs 精确 1.61 Hz），但 alpha 远离 1 时（如 0.9）差异会变大。

高于 1.59 Hz 的信号主要由陀螺仪贡献（加速度计的高频噪声被低通滤掉），低于 1.59 Hz 的信号主要由加速度计贡献（陀螺仪的低频漂移被高通滤掉）。

**设计动机**：alpha 的选择就是在"截止频率"上做一个权衡——太高（alpha 大）则截止频率低，加速度计的校正来得慢，漂移校正不及时；太低（alpha 小）则截止频率高，加速度计的噪声泄漏进来。

### 数值算例

dt = 0.002 s, alpha = 0.98
初始: theta_0 = 0, true = 0
第 1 步:
gyro_pred = 0 + 0.0 * 0.002 = 0.0
- `$accel_est` — 0.01 (有噪声)
theta_1 = 0.98 * 0.0 + 0.02 * 0.01 = 0.0002
第 2 步:
gyro_pred = 0.0002 + 0.001 * 0.002 = 0.000202
accel_est = -0.008
theta_2 = 0.98 * 0.000202 + 0.02 * (-0.008) = 0.000198 + (-0.00016) = 0.000038

可以看到：每一步的修正量很小（0.02 倍），这意味着滤波器对加速度计的突变不敏感（抗噪），但需要约 `1/(1-alpha) = 50` 步（0.1 秒）才能完成一次大的校正。

### Upkie 代码映射

```python
import sys
sys.path.insert(0, 'src')
import numpy as np
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.sim.sensors import read_sensors
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController

runner = SimulationRunner()
runner.reset("stand")
controller = WheelBalancerController(standup_duration=0.2)

alpha = 0.98
seed = 19
rng = np.random.default_rng(seed)
theta_est = runner.spec.equilibrium_pitch_rad
dt = runner.model.opt.timestep * runner.spec.frame_skip

estimates = []
true_angles = []
survived = True

try:
    for step in range(1000):
        runner.step(controller.compute_action(runner, runner.time))

        # posture_state 只用于练习后的误差评分
        state = runner.posture_state()
        if state["base_height"] <= -0.35 or abs(state["pitch"]) >= 0.5:
            survived = False
            break
        true_pitch = state["pitch"]
        true_angles.append(true_pitch)

        # 按名称读取 MuJoCo sensordata，不能依赖数组位置
        readings = read_sensors(runner.data, runner.sensor_map)
        gyro_y = readings["imu_gyroscope"][1] + 0.001 + rng.normal(0, 0.001)
        accel = readings["imu_accelerometer"]
        accel_pitch = np.arctan2(-accel[0], np.hypot(accel[1], accel[2])) + rng.normal(0, 0.05)

        # 互补滤波
        theta_est = alpha * (theta_est + gyro_y * dt) + (1 - alpha) * accel_pitch
        estimates.append(theta_est)
finally:
    runner.close()

# 评估
true_angles = np.array(true_angles)
estimates = np.array(estimates)
rmse = np.sqrt(np.mean((estimates - true_angles)**2))
summary = {
    "seed": seed,
    "steps": len(estimates),
    "survived": survived,
    "rmse_rad": float(rmse),
}
print(summary)
```

关键行设计原因：

- `alpha * (theta_est + gyro_y * dt)`：先做陀螺仪积分预测，再与加速度计融合。这是"预测-校正"的简化形式。
- `np.arctan2(-accel[0], np.hypot(accel[1], accel[2]))`：从加速度计估算俯仰角。在静态条件下，加速度计测量的是重力向量 `g`，通过 `atan2(-ax, hypot(ay, az))` 可以提取倾斜角。但在动态条件下（有运动加速度），这个估计有误差。

## 动手检查点

### 检查点 1：互补滤波效果

```powershell
python scripts/course_checkpoint.py --chapter 19
```

预期输出：

关卡 19 自动验收通过，证据见: outputs/results/checkpoint_19.json

> checkpoint 脚本运行 `tests/test_estimation.py`，生成自动测试 result、日志和状态图。本章示例的 RMSE 属于学习者实验记录，不应伪装成仓库内不存在的专属 result。

### 检查点 2：Alpha 敏感性

```powershell
python -c "
import numpy as np

seed = 19
rng = np.random.default_rng(seed)
dt = 0.002
t = np.arange(0, 10, dt)
true_angle = 0.1 * np.sin(2 * np.pi * 0.5 * t)

accel_angle = true_angle + rng.normal(0, 0.05, len(t))
gyro_rate = np.gradient(true_angle, dt) + 0.001
gyro_angle = np.cumsum(gyro_rate * dt)

for alpha in [0.9, 0.95, 0.98, 0.99, 0.999]:
    est = np.zeros(len(t))
    for i in range(1, len(t)):
        est[i] = alpha * (est[i-1] + gyro_rate[i] * dt) + (1-alpha) * accel_angle[i]
    rmse = np.sqrt(np.mean((est - true_angle)**2))
    print(f'alpha={alpha:.3f}: RMSE = {rmse:.6f} rad')
"
```

预期：在本关默认参数下（gyro bias = 0.001 rad/s，仿真 10 s），alpha 越高 RMSE 越小——alpha=0.999 最优。这是因为陀螺仪偏差极小，漂移累积远慢于加速度计噪声，所以"尽量信任陀螺仪"总是更好的策略。

> **alpha = 0.98 什么时候最优？** 当 gyro bias 较大（如 0.01 rad/s）或仿真时间较长时，漂移累积才变得显著，此时 RMSE 关于 alpha 呈 U 形曲线——alpha 太小则加速度计噪声泄漏，alpha 太大则漂移失控，最优值出现在 0.98~0.99 附近。你可以把上面代码中的 `0.001` 改成 `0.01` 验证这一点。

## 可视化证据

<!-- upkie-animation:19-evidence -->

checkpoint 的三重自动证据为：

- `outputs/plots/checkpoint_19.png`：自动测试通过比例状态图；
- `outputs/logs/checkpoint_19.log`：`tests/test_estimation.py` 的真实 pytest 输出；
- `outputs/results/checkpoint_19.json`：退出码、checks 与源码摘要。

互补滤波角度曲线由本章示例生成，学习者应将自己的图和 RMSE 说明保存到 `outputs/portfolio/19`，不要把 checkpoint 状态图描述成三行实验曲线。

## 故障诊断挑战

<!-- upkie-animation:19-comparison -->

**破坏**：把互补滤波公式中的加速度计项和陀螺仪项交换：

```python
# 错误：交换了
theta_est = (1 - alpha) * (theta_est + gyro_y * dt) + alpha * accel_pitch
# 正确应该是：
# theta_est = alpha * (theta_est + gyro_y * dt) + (1 - alpha) * accel_pitch
```

**第一处异常**：滤波器变得更信任加速度计（因为 alpha 接近 1 时加速度计项的权重反而大了），估计值跟随加速度计的高频噪声剧烈振荡。

**根因假设**：alpha 的含义被反转了。原本 alpha=0.98 表示"98% 信任陀螺仪"，交换后变成"98% 信任加速度计"。

**最小修复**：恢复正确的公式。

**验证**：RMSE 恢复到预期水平，振荡消失。

## 三档任务

### 基础任务

- 实现互补滤波器，比较三种 alpha（0.9, 0.95, 0.99）的 RMSE。
- 绘制真实角度和三种估计的对比图。

### 岗位挑战

- 在 Upkie 仿真中加入真实扰动（水平推力），比较互补滤波在有动态加速度时的性能退化。
- 设计一个自适应 alpha：当加速度计测量的总加速度偏离 g 很远时（说明有运动加速度），自动减小加速度计的权重。

### 开放探索

- 研究 Madgwick 滤波器和 Mahony 滤波器，它们如何处理三轴姿态估计（不仅是一维角度）。
- 写一段 200 字分析：互补滤波和 Kalman 滤波在什么条件下给出相同的结果？

## 复盘与面试

1. **为什么不能只用加速度计？** 加速度计对运动加速度敏感——当 Upkie 加速前进时，加速度计测量的不只是重力，还有运动加速度，导致角度估计错误。

2. **为什么不能只用陀螺仪？** 陀螺仪有偏差（bias），积分后偏差会线性增长。即使偏差只有 0.001 rad/s，10 秒后角度误差就有 0.01 rad（约 0.57 度），1 分钟后有 3.4 度。

3. **alpha 的物理意义是什么？** 它决定了截止频率 `f_c ≈ (1-alpha)/(2*pi*dt)`（精确式为 `-ln(alpha)/(2*pi*dt)`）。高于 f_c 的信号用陀螺仪，低于 f_c 的信号用加速度计。

4. **互补滤波的局限是什么？** 它假设加速度计的长期平均等于重力方向——这在长时间加速（如匀速圆周运动）时不成立。对于这种情况需要 Kalman 滤波（关卡 20）。

## 下一关

关卡 `20`（Kalman Filter）会假设你已经理解传感器融合的动机和基本方法。互补滤波是 Kalman 滤波的特例（当噪声协方差取特定值时），下一关将用概率框架系统化地推导最优融合权重，不再需要手动选择 alpha。
