# 20 Kalman Filter

> 建设状态：可执行  
> 阶段：状态估计与优化  
> 作品集目录：`outputs/portfolio/20`

## 岗位任务

IMU 给出的俯仰角带有随机噪声，控制器若逐样本追随它，就会制造轮端力矩抖动。你需要构建一个两状态线性 Kalman 滤波器，结合“角度随角速度积分”的模型和“角度测量”的证据，量化估计比原始观测改善多少，以及不确定性是否收敛。

## 学习目标

- 理解预测与校正分别依赖模型和传感器；
- 写出状态、协方差、过程噪声和测量噪声的单位；
- 推导 Kalman 增益如何在模型/测量之间分配信任；
- 用固定 seed 比较原始测量与估计 RMSE；
- 通过协方差曲线发现噪声模型设置错误。

## 前置关卡

完成 19 章互补滤波。互补滤波先给直觉；本章把“相信陀螺仪多少、相信角度测量多少”变成协方差矩阵的可计算权重。

## 先观察现象

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 20
```

运行后从结构化结果读取本机本次指标，不复制旧输出中的完整浮点快照：

```python
import json
from pathlib import Path

result = json.loads(Path("outputs/results/estimation_20.json").read_text(encoding="utf-8"))
metrics = result["metrics"]
for name, value in metrics.items():
    print(f"{name}: {value:.6f}")

assert metrics["kalman_rmse_rad"] <= 0.05
assert metrics["rmse_improvement_ratio"] >= 1.5
assert metrics["final_covariance_trace"] <= 0.03
```

先看灰色测量曲线为何抖动，再看绿色估计为何没有机械地贴着每个样本走。

## 直觉与概念

<!-- upkie-animation:20-intuition -->

预测是“根据刚才的角度和角速度，我认为下一刻在哪”；校正是“传感器说它在这，应该信多少”。协方差 `P` 记录的不是机器人真实误差，而是当前模型对自己不确定性的量化。`R` 大表示测量不可靠，`Q` 大表示模型不可靠。

## 估计数据流

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 410" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="14" width="150" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="95.0" y="36" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">上一估计 x_k</text>
<rect x="250" y="14" width="180" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="340.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="340.0" dy="0">预测</tspan>
<tspan x="340.0" dy="22">x- = F x</tspan>
</text>
<rect x="20" y="72" width="150" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="95.0" y="94" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">上一协方差 P_k</text>
<rect x="250" y="72" width="210" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="355.0" y="92" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="355.0" dy="0">预测协方差</tspan>
<tspan x="355.0" dy="22">P- = F P F^T + Q</tspan>
</text>
<rect x="20" y="148" width="170" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="105.0" y="170" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">带噪角度测量 z</text>
<rect x="250" y="148" width="160" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="330.0" y="170" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">创新 z - Hx-</text>
<rect x="250" y="206" width="230" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="365.0" y="226" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="365.0" dy="0">K = P- H^T</tspan>
<tspan x="365.0" dy="22">(H P- H^T + R)^-1</tspan>
</text>
<rect x="250" y="280" width="210" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="355.0" y="300" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="355.0" dy="0">校正</tspan>
<tspan x="355.0" dy="22">x = x- + K·innovation</tspan>
</text>
<rect x="250" y="354" width="150" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="325.0" y="376" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">下一估计</text>
<line x1="95" y1="48" x2="340" y2="14" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="95" y1="106" x2="355" y2="98" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="340" y1="66" x2="330" y2="148" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="105" y1="182" x2="330" y2="148" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="355" y1="124" x2="365" y2="206" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="355" y1="258" x2="355" y2="280" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="330" y1="200" x2="365" y2="206" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="355" y1="332" x2="355" y2="354" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

## 教科书级展开

<!-- upkie-animation:20-parameter -->

### 状态、模型和单位

$$
x = [\theta, theta_{\text{dot}}]^T
F = [[1, dt], [0, 1]]
H = \begin{bmatrix}
1 & 0
\end{bmatrix}
$$

- `theta`：俯仰角，rad；
- `theta_dot`：俯仰角速度，rad/s；
- `dt=0.01 s`；
- `F`：匀角速度离散状态转移；
- `H`：传感器只直接测到角度。

预测写成：

$$
x- = F x
P- = F P F^T + Q
$$

`P` 的元素携带相应状态单位的平方或乘积，例如 `P[0,0]` 单位为 rad²。`Q` 表示模型未描述的角加速度变化，`R=0.08² rad²` 对应角度测量噪声标准差 0.08 rad。

### Kalman 增益的逐步来源

创新是测量与预测的差：

$$
innovation = z - H x-
S = H P- H^T + R
K = P- H^T S^-1
$$

`S` 是创新协方差。若 `R` 很大，`S` 大，`K` 小，估计更相信模型；若 `P-` 大，`K` 大，估计更愿意向测量修正。校正：

$$
x = x- + K innovation
P = (I-KH) P- (I-KH)^T + K R K^T
$$

最后一行是 Joseph 形式，数值上比简单的 `(I-KH)P-` 更稳健，能更好保持协方差半正定。

### 数值算例

若预测角度为 0.10 rad，测量为 0.18 rad，且标量情况下 `K=0.25`：

$$
innovation = 0.18-0.10 = 0.08 rad
\theta = 0.10 + 0.25 \cdot 0.08 = 0.12 rad
$$

估计不会跳到 0.18，也不会忽略测量；它只移动到两者之间。真正 K 由 P、Q、R 自动计算，不应手工硬编码为“看起来平滑”的常数。

### 假设与失效条件

线性 Kalman 假设状态转移和测量均线性、噪声近似零均值高斯、Q/R 反映真实不确定性。剧烈接触冲击、传感器饱和、时间戳丢失、重力方向无法代表俯仰角时，这些假设失效。此时首先看创新和协方差，而不是盲目调大增益。

## 代码映射

```python
filter_.predict()
estimate = filter_.update(np.array([measurement]))

innovation = measurement - H @ state
gain = np.linalg.solve(H @ P @ H.T + R, H @ P).T
state = state + gain @ innovation
```

输入为角度测量，内部状态包含 `[theta, theta_dot]` 和 P；输出是两状态估计。矩阵形状不符会抛出 `ValueError`，防止把关节向量误接到 IMU 模型。

## 动手检查点

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 20
python scripts/course_checkpoint.py --chapter 20
```

## 可视化证据

<!-- upkie-animation:20-evidence -->

- `outputs/plots/estimation_20.png`：真值、测量、估计和 `trace(P)`；
- `outputs/logs/estimation_20.json`：seed、采样周期与指标；
- `outputs/results/estimation_20.json`：统一验收结果；
- `outputs/portfolio/20/evidence.json`：作品集索引；
- `outputs/results/checkpoint_20.json`：自动测试。

## 故障诊断挑战

<!-- upkie-animation:20-comparison -->

把 `R` 误设为 `0.08` 而不是 `0.08²`。滤波器会把测量看得过于不可靠，曲线变慢，创新长期偏大。把 `Q` 设为零也会出问题：模型面对真实角加速度变化过度自信，协方差不再反映误差。

## 三档任务

- 基础任务：手算标量校正步骤，运行两个检查点。
- 岗位挑战：改变测量噪声标准差，固定 Q，画出 RMSE 与最终协方差关系。
- 开放探索：加入角速度测量，扩展 H 与 R，比较仅角度测量的可观性。

## 专业里程碑

你现在能用可复现数据证明估计改善，而不是只说“曲线更平滑”。作品集应包含 RMSE 对比、协方差曲线和一次 Q/R 单位错误诊断。

## 复盘与面试

1. Q 与 R 分别表达什么不确定性？
2. K 变大一定更好吗？
3. 为什么 P 的单位不能忽略？
4. Joseph 形式解决什么数值问题？
5. 哪些接触事件会破坏本章线性假设？

## 下一关

21 章接入 MuJoCo 原生 IMU 与轮编码器，用同一组非线性观测比较 EKF/UKF，并让 UKF 估计进入平衡控制闭环。
