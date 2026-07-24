# 21 EKF/UKF 原生传感器融合闭环

> 建设状态：可执行  
> 阶段：状态估计与优化  
> 作品集目录：`outputs/portfolio/21`

## 岗位任务

Upkie 的平衡控制不能直接读取仿真真值。你要从 MuJoCo `sensordata` 读取基座 IMU 和轮编码器，为相同观测分别运行 EKF 与 UKF，再把 UKF 的状态估计送入轮式平衡控制器。

本关交付物不是一条离线合成曲线，而是一条可追踪的闭环证据链：

1. 原生传感器：`imu_orientation`、`imu_accelerometer`、`imu_gyroscope`、左右轮位置与速度编码器；
2. 固定噪声：相同 seed 下生成可复现的姿态、角速度和轮速扰动；
3. 同源对照：raw、EKF、UKF 接收同一时刻的同一组观测；
4. 控制闭环：UKF 估计的俯仰、俯仰角速度、前向速度和积分位置进入 `WheelBalancerController`；
5. 独立评分：真值只用于 RMSE、最大俯仰角和存活判定。

## 学习目标

- **理解**：说明 IMU 四元数、加速度、角速度和轮编码器各约束哪个状态；
- **推导**：写出四维状态转移、六维非线性观测和 EKF Jacobian；
- **比较**：解释 EKF 局部线性化与 UKF sigma 点传播的差别；
- **实现**：从 `mujoco_sensordata` 读取观测，固定噪声并复现指标；
- **验收**：证明估计优于 raw，并证明 UKF 状态真正进入 301 步控制闭环。

## 前置关卡

完成 `20`。你应能解释 Kalman Filter 的预测、创新、增益和校正，并知道 `Q` 是过程噪声、`R` 是测量噪声。本关保留这个骨架，但状态和测量函数不再只用常数矩阵表示。

## 先观察现象

在项目根目录运行：

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 21
```

运行后从结构化结果读取本机本次指标，并按六位小数展示：

```python
import json
from pathlib import Path

result = json.loads(Path("outputs/results/estimation_21.json").read_text(encoding="utf-8"))
metrics = result["metrics"]
for name, value in metrics.items():
    print(f"{name}: {value:.6f}")

assert metrics["ekf_pitch_rmse_rad"] <= 0.15
assert metrics["ukf_pitch_rmse_rad"] <= 0.15
assert metrics["ekf_rmse_improvement_ratio"] >= 1.2
assert metrics["ukf_rmse_improvement_ratio"] >= 1.2
assert metrics["ukf_to_ekf_rmse_ratio"] <= 1.1
assert metrics["closed_loop_survived"] == 1.0
assert metrics["closed_loop_max_abs_pitch_rad"] <= 0.5
```

先打开 `outputs/plots/estimation_21.png`。灰线是带固定噪声的 raw IMU 俯仰角，紫线和绿线分别是 EKF、UKF，黑线是真值评分曲线。黑线不是滤波器输入。

错误基线是把 `runner.posture_state()` 直接传给控制器。这样曲线会很好看，却没有证明传感器、估计器和控制器的接口能闭环工作。

## 直觉与概念

<!-- upkie-animation:21-intuition -->

### 四类传感器各回答一个问题

- `imu_orientation`：基座朝向哪里，给俯仰角提供直接但带噪的参考；
- `imu_accelerometer`：重力和运动加速度在机身坐标系中的投影，静态时能校正倾角，急加速时可信度下降；
- `imu_gyroscope`：基座转得多快，短期变化灵敏，但积分会累积偏差；
- `left_wheel_velocity`、`right_wheel_velocity`：轮子转得多快，用轮半径和方向映射为前向速度观测，打滑时不等于机身真实速度。

位置编码器 `left_wheel_position`、`right_wheel_position` 也被记录在传感器契约中，用于检查通道完整性；本关状态位置由融合后的前向速度积分得到。

### 为什么同一组数据同时跑 EKF 和 UKF

如果 EKF 和 UKF 使用不同轨迹、不同 seed 或不同噪声，就无法判断差异来自算法还是数据。本关每一步只读取一次 `sensordata`，构造一个六维测量，再把同一个向量交给两个滤波器。

### 闭环数据流

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 430" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="165" y="8" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="280.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="280.0" dy="0">MuJoCo sensordata</tspan>
<tspan x="280.0" dy="22">IMU + wheel encoders，100 Hz</tspan>
</text>
<rect x="165" y="74" width="230" height="68" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="280.0" y="91" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="280.0" dy="0">fixed-seed noise</tspan>
<tspan x="280.0" dy="22">orientation 0.035 rad, gyro 0.03 rad/s</tspan>
<tspan x="280.0" dy="22">wheel speed 0.03 m/s</tspan>
</text>
<rect x="165" y="158" width="230" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="280.0" y="176" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="280.0" dy="0">shared measurement z</tspan>
<tspan x="280.0" dy="22">6 dimensions</tspan>
</text>
<rect x="5" y="222" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="120.0" y="242" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="120.0" dy="0">EKF</tspan>
<tspan x="120.0" dy="22">Jacobian linearization</tspan>
</text>
<rect x="295" y="222" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="410.0" y="242" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="410.0" dy="0">UKF</tspan>
<tspan x="410.0" dy="22">sigma-point propagation</tspan>
</text>
<rect x="295" y="292" width="240" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="415.0" y="312" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="415.0" dy="0">WheelBalancerController</tspan>
<tspan x="415.0" dy="22">estimated theta, rate, v, x</tspan>
</text>
<rect x="295" y="362" width="240" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="415.0" y="380" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="415.0" dy="0">6-D actuator command</tspan>
<tspan x="415.0" dy="22">wheel torque limited to ±1 N·m</tspan>
</text>
<rect x="5" y="292" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="120.0" y="312" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="120.0" dy="0">metrics only</tspan>
<tspan x="120.0" dy="22">RMSE, survival, max pitch</tspan>
</text>
<rect x="5" y="362" width="190" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="100.0" y="384" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">posture_state truth</text>
<line x1="280" y1="60" x2="280" y2="74" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="280" y1="142" x2="280" y2="158" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="165,206 165,232 120,232 120,222" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="395,206 395,232 380,232 380,222" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="120" y1="274" x2="120" y2="292" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="410" y1="274" x2="410" y2="292" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="410" y1="344" x2="410" y2="362" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="525,386 550,386 550,34 395,34" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="100" y1="396" x2="100" y2="340" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

## 教科书级展开

<!-- upkie-animation:21-parameter -->

### 第一层：直觉

EKF 在当前估计附近画切线，用切线近似非线性观测；UKF 在均值周围放置一组 sigma 点，让这些点通过原始非线性函数，再由传播后的点重建均值和协方差。

EKF 更直接、计算量较小，但依赖 Jacobian 正确；UKF 不要求手写 Jacobian，但每一步要传播多个点，计算量更高。UKF 并不天然更准确，本关只要求它与 EKF 同源比较且不明显退化。

### 第二层：状态、符号和形状

$$
x = [\theta, \omega, v, p]^T
$$

| 符号 | 含义 | SI 单位 |
|---|---|---|
| `theta` | 基座俯仰角 | rad |
| `omega` | 基座俯仰角速度 | rad/s |
| `v` | 前向速度 | m/s |
| `p` | 前向位置，由速度积分 | m |
| `dt` | 控制与估计周期 | 0.01 s |

六维测量为：

$$
z = [\sin(theta_{o}), \cos(theta_{o}), omega_{g}, v_{w},
     \sin(theta_{a}), \cos(theta_{a})]^T
$$

`theta_o` 来自带固定噪声的 IMU orientation，`omega_g` 来自 gyroscope，`v_w` 来自轮编码器，`theta_a` 由 accelerometer 的重力方向计算。用正弦和余弦成对表达角度，是为了避免角度跨越边界时发生数值跳变；它们不是离线生成的正弦轨迹。

### 第三层：物理意义和噪声单位

实验使用 `np.random.default_rng(21)`。噪声标准差固定为：

orientation_rad:       0.035 rad
gyroscope_rad_s:       0.03 rad/s
wheel_velocity_m_s:    0.03 m/s

加速度计还受到 MuJoCo 动力学中的真实运动加速度影响，因此其角度通道在 `R` 中使用更大的 `0.25^2` 方差。这个权重表达“急加速时少信加速度倾角”，不是把加速度计从融合中删除。

不同单位的测量不能共用一个方差。`R` 的对角元素分别是对应测量标准差的平方。

### 第四层：设计动机

状态转移使用最小的常速度模型：

$$
theta_{k+1} = theta_{k} + dt \cdot omega_{k}
omega_{k+1} = omega_{k}
v_{k+1}     = v_{k}
p_{k+1}     = p_{k} + dt \cdot v_{k}
$$

它不假装知道完整轮足动力学，只表达一个采样周期内的连续性。IMU 和编码器负责校正模型漂移。若过程噪声太小，滤波器会过度相信该简化模型；太大则估计会追随测量噪声。

### 第五层：EKF 推导与 UKF 对照

状态转移 Jacobian 为：

$$
F = [[1, dt, 0, 0],      [0,  1, 0, 0],      [0,  0, 1, 0],      [0,  0, dt,1]]
$$

预测：

$$
x_{\text{minus}} = f(x)
P_{\text{minus}} = F P F^T + Q
$$

观测函数把同一个 `theta` 映射到 orientation 和 accelerometer 两对通道：

$$
h(x) = [\sin(\theta), \cos(\theta), \omega, v,
        \sin(\theta), \cos(\theta)]^T
$$

逐行求偏导得到 EKF 测量 Jacobian：

$$
H = [[ \cos(\theta), 0, 0, 0],      [-\sin(\theta), 0, 0, 0],      [          0, 1, 0, 0],      [          0, 0, 1, 0],      [ \cos(\theta), 0, 0, 0],      [-\sin(\theta), 0, 0, 0]]
$$

创新和校正仍沿用 Kalman 骨架：

$$
y = z - h(x_{\text{minus}})
S = H P_{\text{minus}} H^T + R
K = P_{\text{minus}} H^T S^-1
x = x_{\text{minus}} + K y
$$

UKF 不构造 `F`、`H`。它由当前 `x,P` 产生 `2n+1` 个 sigma 点；本关 `n=4`，所以每次传播 9 个点。每个点经过相同 `f()` 和 `h()`，再用权重恢复均值、协方差和状态-测量交叉协方差。

### 第六层：数值算例和闭环指标

不要把某次运行的完整浮点值写成长期契约。EKF 改善比由结构化结果实时计算：

```python
ekf_improvement = metrics["raw_pitch_rmse_rad"] / metrics["ekf_pitch_rmse_rad"]
print(f"EKF improvement: {ekf_improvement:.6f}")
```

UKF 使用相同 raw 基准：

```python
ukf_improvement = metrics["raw_pitch_rmse_rad"] / metrics["ukf_pitch_rmse_rad"]
print(f"UKF improvement: {ukf_improvement:.6f}")
```

只有 `ukf_to_ekf_rmse_ratio <= 1.1` 才表示 UKF 在同源实验中没有明显退化，这不应推广为“UKF 总是更好”。闭环还必须满足存活、至少 100 个样本和最大绝对俯仰角不超过 `0.5 rad`；以 result 的 checks 为最终判据。

### 第七层：代码映射

传感器只按名称读取，不能假设 `sensordata` 前三个元素永远是加速度计：

```python
readings = read_sensors(runner.data, runner.sensor_map)
measurement, raw_pitch = _sensor_measurement(readings, runner, rng)
ekf_state = _update_pitch_estimator(ekf, measurement, dt)
ukf_state = _update_pitch_estimator(ukf, measurement, dt)
```

UKF 状态进入控制器：

```python
estimated_state = {
    "pitch_error": ukf_state[0] - runner.spec.equilibrium_pitch_rad,
    "pitch_rate": ukf_state[1],
    "forward_velocity": ukf_state[2],
    "x_position": ukf_state[3],
}
controller.compute_action(runner, runner.time, estimated_state=estimated_state)
```

本实验把位置增益设为 `0.2`、前向速度增益设为 `0.1`。轮编码器在打滑时不等于机身速度，因此不能沿用理想真值反馈下的激进增益。

### 假设与失效条件

- MuJoCo IMU site 与基座刚性连接，四元数顺序为 `wxyz`；
- 传感器和控制器同为 100 Hz，本关不模拟时间戳乱序；
- 固定噪声近似零均值高斯，不覆盖偏置随机游走、饱和或丢包；
- 加速度倾角仅在重力占主导时可信，持续水平加速会破坏该假设；
- 轮速仅在接触且滑移有限时近似前向速度；
- EKF 依赖 Jacobian 与状态顺序一致，UKF 依赖 sigma 点协方差保持正定；
- 真值直连控制器、旧结果文件或空日志都不能替代本章闭环验收。

## 动手检查点

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 21
python scripts/course_checkpoint.py --chapter 21
```

实验结果必须同时满足：

- EKF、UKF RMSE 均不超过 `0.15 rad`；
- EKF、UKF 相对 raw 的改善比均至少 `1.2`；
- `ukf_to_ekf_rmse_ratio <= 1.1`；
- `closed_loop_survived == 1.0`；
- `closed_loop_max_abs_pitch_rad <= 0.5`。

常见失败一：`sensor_backend` 不是 `mujoco_sensordata`。检查是否又回到了手工生成测量。

常见失败二：RMSE 很低但闭环样本数为 0。检查是否只做离线滤波，没有把估计状态传给控制器。

常见失败三：固定 seed 仍不能复现。检查是否调用了全局随机函数，或每个滤波器各自重新采样噪声。

常见失败四：轮速反馈导致缓慢发散。检查轮方向、轮半径、滑移以及速度/位置增益。

## 可视化证据

<!-- upkie-animation:21-evidence -->

四类产物证据必须同时存在：

- **视觉**：`outputs/plots/estimation_21.png`，展示 truth、raw、EKF、UKF 同一时间轴；
- **日志**：`outputs/logs/estimation_21.json`，其中 `sensor_backend=mujoco_sensordata`、`truth_usage=metrics_only`，并保存传感器名、固定噪声和 301 个样本；
- **自动结果**：`outputs/results/estimation_21.json`，保存指标、阈值、checks 和源码摘要；
- **作品集**：`outputs/portfolio/21/evidence.json`，索引本章 result、plot、log 与 metrics。

## 验证命令

四类产物是实验交付，测试命令是对实现和产物契约的独立验证：

```powershell
python -m pytest tests/test_estimation.py tests/test_estimation_optimization_labs.py tests/test_sensor_mapping.py tests/test_controller_outputs.py -q
```

## 故障诊断挑战

<!-- upkie-animation:21-comparison -->

### 挑战一：偷偷接回真值

把控制调用中的 `estimated_state=estimated_state` 删除。第一处异常不是必然跌倒，而是证据链断开：控制器重新读取 `posture_state()`，即使曲线仍稳定也不再证明估计闭环。检查日志中的 `closed_loop_controller_observation` 和控制器调用签名定位根因。

### 挑战二：让两个滤波器使用不同噪声

在 EKF 和 UKF 更新前分别重新采样。此时比较不再同源。最小修复是每一步只构造一次 `measurement`，将同一个数组交给两个滤波器。

### 挑战三：过度相信加速度计

把 accelerometer 两个通道方差从 `0.25^2` 改成 `0.01^2`。机器人急加速时，平动加速度会被误判为倾角，创新和控制力矩出现尖峰。应恢复与动态加速度风险相匹配的测量协方差。

## 三档任务

- **基础任务**：运行固定实验，从日志逐项确认 7 个传感器名、噪声单位和 301 个样本。
- **岗位挑战**：只改变 orientation 噪声标准差，保持 seed 和其他参数不变，比较 raw/EKF/UKF RMSE 与闭环最大俯仰角。
- **开放探索**：加入陀螺仪 bias 状态，比较五维 EKF/UKF 的可观性、收敛时间和计算代价。

## 复盘与面试

1. 为什么本章必须按传感器名读取，而不能切 `sensordata[:3]`？
2. 为什么 accelerometer 通道的 `R` 大于 orientation 通道？
3. EKF 的 Jacobian 写错一行会先影响创新、增益还是执行器输出？
4. UKF 不写 Jacobian，为什么仍不能称为无模型方法？
5. 为什么同源数据是算法对比的必要条件？
6. `truth_usage=metrics_only` 对可信验收意味着什么？
7. UKF 的 RMSE 略低，为什么不能得出“UKF 总是优于 EKF”？
8. 301 步存活为什么比离线 RMSE 单独通过更强？

## 下一关

`22` 将从状态估计转向参数辨识：使用训练/测试分离的样本恢复局部动力学系数，并检查辨识模型是否能在未参与拟合的数据上泛化。
