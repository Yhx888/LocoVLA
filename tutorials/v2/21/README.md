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

<!-- upkie-qa:21-q1 -->
因为 `sensordata` 是一个扁平数组，各传感器的起始偏移和长度完全由 MJCF 里传感器的声明顺序决定，而声明顺序不是接口契约的一部分。切 `sensordata[:3]` 隐式假设“前三个元素永远是加速度计”，但只要有人在模型里新增、删除或调整一个传感器，偏移就会整体错位：四元数被当成加速度、轮速被当成角速度，滤波器不会报错，只会安静地输出错误估计。这正是 11 章模型契约（`sensor_contract`）的核心思想：代码与模型之间的接口应当基于具名字段（`imu_orientation`、`imu_accelerometer`、`imu_gyroscope`、左右轮编码器），而不是魔术下标。本章代码用 `read_sensors(runner.data, runner.sensor_map)` 先把名字解析成地址再取数，并在日志里保存 `sensor_backend=mujoco_sensordata` 和完整传感器名单，任何人都能审计每路观测的来源。实机上这个原则同样成立：ROS 话题名、CAN ID 都是“按名读取”的对应物，硬编码字节偏移在固件升级后就是事故隐患。
<!-- /upkie-qa -->

2. 为什么 accelerometer 通道的 `R` 大于 orientation 通道？

<!-- upkie-qa:21-q2 -->
R 的大小表达“这路观测相对于它约束的状态有多可信”。orientation 通道来自 IMU 四元数，它直接观测俯仰角本身，噪声主要是测量抖动，与状态的关系干净直接。accelerometer 通道则是间接证据：把重力方向在机体坐标系的投影当作俯仰角的观测，这个换算只在机器人准静态时才严格成立。平衡控制中机体持续加减速，加速度计读到的是重力加速度与运动加速度的叠加，还叠加轮子震动、接触冲击带来的高频分量——这些都是相对于“俯仰角观测”的模型误差，必须计入 R 才能诚实反映它的可信度。把 accelerometer 的 R 设得跟 orientation 一样小，滤波器会把运动加速度误读为姿态变化，估计在加减速时系统性地偏斜；19 章互补滤波里“加速度计只能信低频、陀螺仪只能信高频”的直觉，在这里升级为两路通道不同的 R 数值。更一般的工程原则是：R 不只包含传感器自身噪声，还包含“把读数解释为观测方程”时的建模误差，解释链路越长、假设越多，R 应该越大。
<!-- /upkie-qa -->

3. EKF 的 Jacobian 写错一行会先影响创新、增益还是执行器输出？

<!-- upkie-qa:21-q3 -->
先影响增益。沿着 EKF 的数据流梳理：创新 `nu = z - h(x-)` 用的是原始非线性观测函数 h 本身，不用 Jacobian，所以 Jacobian 写错的第一拍，创新仍然是对的；Jacobian H 第一次被使用是在创新协方差 `S = HP-Hᵀ + R` 和增益 `K = P-HᵀS⁻¹` 里，所以错误首先体现为增益矩阵的数值和结构错误——某路观测被错误地分配给不相干的状态分量，或权重大小失真。接着错误增益乘以（正确的）创新得到错误的状态校正，估计偏离真值；下一拍起，预测基于错误估计展开，创新也开始变异常，错误开始自我放大。最后才传到执行器：本章闭环中 UKF/EKF 的俯仰估计进入 `WheelBalancerController`，错误估计会让控制器对并不存在的倾角做出补偿，轮端力矩持续偏置，严重时触发 `0.5 rad` 俯仰限制导致存活失败。这个传播链（增益→估计→后续创新→执行器）也给出了调试顺序：怀疑 Jacobian 时应先用数值差分验证解析 Jacobian（逐元素比较 `(h(x+eps)-h(x))/eps`），而不是直接盯着控制输出猜。UKF 的优势之一正是消除了这一整类手写 Jacobian 错误。
<!-- /upkie-qa -->

4. UKF 不写 Jacobian，为什么仍不能称为无模型方法？

<!-- upkie-qa:21-q4 -->
因为 UKF 只是免去了“对模型求导”，没有免去“模型本身”。UKF 的每一步都在显式调用两个用户提供的函数：状态转移函数 f（本章的四维俯仰—角速度—速度—位置递推）和非线性观测函数 h（六维测量映射）。sigma 点方法的本质是：不对 f、h 做切线近似（EKF 的做法），而是在均值周围按协方差确定性地撺一组点，把这些点逐个送进原始的 f 和 h，再用传播后的点重建均值和协方差。换句话说，UKF 改变的是“不确定度如何穿过非线性函数”的近似方式，而不是对系统知识的依赖量。如果 f 的动力学写错（比如重力项符号反了）、h 的几何关系弄错（比如轮半径错一倍），UKF 会和 EKF 一样产生系统性错误估计，而且同样不报错。真正的无模型方法（如纯数据驱动的回归）不需要你写出 f 和 h。本章还提醒了另一个对称的误区：UKF 也不天然更准，验收只要求 `ukf_to_ekf_rmse_ratio <= 1.1`（同源对比不明显退化），而不是要求 UKF 必须获胜。选择 EKF 还是 UKF，是在“Jacobian 正确性风险”与“多倍 sigma 点计算量”之间做工程权衡。
<!-- /upkie-qa -->

5. 为什么同源数据是算法对比的必要条件？

<!-- upkie-qa:21-q5 -->
因为对比实验的结论只有在“唯一变量是算法”时才成立。如果 EKF 和 UKF 各跑一条轨迹、各用一套 seed 或各自重新采样噪声，那么最终 RMSE 的差异里同时混杂着三种来源：算法近似方式的差异、轨迹本身的差异、噪声实现（realization）的差异，你无法把功劳或锅归因到算法头上。本章的做法是每个控制步只读取一次 `sensordata`，构造一个六维测量向量，再把同一个向量同时交给 raw、EKF、UKF 三条处理链路；噪声在固定 seed 下生成一次，三者共享。这样任何指标差异都只能来自算法内部的近似方式。这个原则在课程后续章节反复出现：30 章残差 RL 与经典控制的对比用同一 10 N 推力、相同 seed 的配对回合；31 章 Sim2Real 评估用同 seed 配对差而非两组独立均值。它们都是同一个统计思想：控制共同随机性，让差异只反映你声称在比较的那个因素。常见失败三（固定 seed 仍不能复现）的排查点——是否调用了全局随机函数、每个滤波器各自重新采样——本质上就是同源性被破坏的症状。
<!-- /upkie-qa -->

6. `truth_usage=metrics_only` 对可信验收意味着什么？

<!-- upkie-qa:21-q6 -->
它声明了一条不可跨越的边界：仿真真值（`posture_state truth`）只允许出现在事后评分环节——计算 RMSE、最大俯仰角和存活判定，绝不允许流入滤波器或控制器的输入。如果没有这条边界，最隐蔽的作弊方式是：滤波器内部“不小心”用真值初始化、用真值重置发散的协方差，或控制器直接读真值俯仰角——指标会非常好看，但整条证据链在真实机器人上一文不值，因为实机根本没有真值可读。本章把这个字段写进 `outputs/logs/estimation_21.json`，与 `sensor_backend=mujoco_sensordata` 一起构成可审计的双重声明：观测只来自原生传感器，真值只用于评分。审计者不需要信任口头承诺，可以从日志字段和源码交叉验证。这也是课程实验约定“作业产物不得隐藏失败、不得绕过通过条件”的具体化：可信验收不仅要求指标达标，还要求指标的产生过程经得起检查。实机开发中对应的实践是：把动作捕捉系统或高精度外部定位仅用作离线评估基准，而不接入控制回路，除非部署环境里它真实存在。
<!-- /upkie-qa -->

7. UKF 的 RMSE 略低，为什么不能得出“UKF 总是优于 EKF”？

<!-- upkie-qa:21-q7 -->
因为单次实验的结论被它的全部实验条件限定：本章的轨迹分布（小角度平衡附近）、噪声水平、四维状态模型、六维观测函数、固定 seed 和滤波器调参，每一项都参与决定了最终 RMSE。换一条更非线性的轨迹、换一组 sigma 点参数、或把观测噪声改大，优劣完全可能反转。统计上，一次固定 seed 的运行只是一个样本点，没有方差信息，无法支撑带量词“总是”的全称命题——这与 31 章强调“用配对差加 bootstrap 置信区间说话，区间跨零就报告证据不足”是同一个纪律。理论上也不存在普适结论：EKF 的一阶线性化在非线性轻微时损失极小，而 UKF 的 sigma 点近似优势要在非线性显著时才体现；两者都不处理模型本身错误。正因如此，本章验收条件故意设计成非对称的：要求 `ukf_to_ekf_rmse_ratio <= 1.1`，即“UKF 在同源实验中没有明显退化”，而不是“UKF 必须更好”。能把结论限定在证据覆盖的范围内，是面试中区分“跑过算法”和“理解实验方法论”的关键信号。
<!-- /upkie-qa -->

8. 301 步存活为什么比离线 RMSE 单独通过更强？

<!-- upkie-qa:21-q8 -->
因为离线 RMSE 只证明“估计在事后看起来准”，而 301 步闭环存活证明“估计好到足以支撑控制”，后者是严格更强的性质。关键区别在于误差的反馈放大：离线滤波中，估计误差不影响轨迹，一步估错下一步可以纠回；闭环中，估计误差会立即变成错误的轮端力矩，力矩改变真实状态，新状态又产生新观测，估计器的系统性偏差（如相位滞后、轮速符号错、缓慢漂移）会在回路里被反复放大。本章常见失败四（轮速反馈导致缓慢发散）就是典型：离线看 RMSE 很小的估计，接入控制后因轮半径或方向约定的小错误而逐步积累、最终跌倒。反之，存活 301 步（约 3 秒，100 Hz）且最大绝对俯仰角不超 `0.5 rad`，说明估计的相位、符号、尺度在控制器真正依赖的四个通道（俯仰、俯仰角速度、前向速度、积分位置）上都过关。当然存活也不能单独作为证据——一个极保守的控制器可能容忍很差的估计——所以本章要求 RMSE、改善比、同源比较、存活、最大俯仰角五类 checks 同时满足，互相交叉验证。
<!-- /upkie-qa -->

## 下一关

`22` 将从状态估计转向参数辨识：使用训练/测试分离的样本恢复局部动力学系数，并检查辨识模型是否能在未参与拟合的数据上泛化。
