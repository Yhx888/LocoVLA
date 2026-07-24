# 22 参数辨识与模型验证

> 建设状态：可执行  
> 阶段：状态估计与优化  
> 作品集目录：`outputs/portfolio/22`

## 岗位任务

控制器用的局部动力学系数不应只来自猜测。你需要从带噪激励数据辨识轮式倒立摆的重力系数和轮端力矩系数，并在独立测试集上验证预测。仅在训练数据上误差小，不能证明模型能用于控制。

## 学习目标

- 将动力学写成线性回归 `y=Phi w+noise`；
- 理解持续激励、条件数和参数可辨识性；
- 使用最小二乘恢复已知系数；
- 采用训练/测试分离，报告测试 RMSE；
- 知道辨识模型适用范围而不把局部参数称为完整物理真值。

## 前置关卡

完成 14 章简化动力学和 21 章估计。参数辨识不是“再做一种滤波”，而是估计不随时间快速变化的模型常数。

## 先观察现象

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 22
```

从结构化结果读取本机本次指标，并用验收容差而不是旧浮点快照判断：

```python
import json
from pathlib import Path

result = json.loads(Path("outputs/results/estimation_22.json").read_text(encoding="utf-8"))
metrics = result["metrics"]
for name, value in metrics.items():
    print(f"{name}: {value:.6f}")

assert metrics["alpha_relative_error"] <= 0.01
assert metrics["beta_relative_error"] <= 0.05
assert metrics["test_prediction_rmse_rad_s2"] <= 0.03
assert metrics["design_condition_number"] <= 5.0
```

散点图横轴是真实测试加速度，纵轴是模型预测；点靠近对角线才说明没有只记住训练样本。

## 直觉与概念

<!-- upkie-animation:22-intuition -->

辨识像用多次不同推法感受一扇门的铰链：只在同一角度、同一力矩下试一次，无法分清“重力大”还是“输入力小”。角度和力矩都要有足够变化，设计矩阵才不会列几乎平行。

## 数据流

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 0 550 360" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="155" y="8" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="240.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="240.0" dy="0">固定 seed 激励</tspan>
<tspan x="240.0" dy="22">theta, tau</tspan>
</text>
<rect x="155" y="74" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="240.0" y="94" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="240.0" dy="0">设计矩阵 Phi</tspan>
<tspan x="240.0" dy="22">theta, tau</tspan>
</text>
<rect x="335" y="8" width="170" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="420.0" y="30" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">测得 theta_ddot</text>
<rect x="155" y="140" width="130" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="220.0" y="162" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">最小二乘</text>
<rect x="155" y="190" width="170" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="240.0" y="212" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">w_hat: alpha, beta</text>
<rect x="155" y="238" width="160" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="235.0" y="260" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">独立测试集预测</text>
<rect x="155" y="286" width="200" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="255.0" y="315" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">RMSE、相对误差、条件数</text>
<rect x="-15" y="74" width="150" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="60.0" y="96" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">窄激励 / 共线列</text>
<line x1="135" y1="91" x2="155" y2="91" stroke="#d36b27" stroke-width="1.5" stroke-dasharray="5,3.5" marker-end="url(#ad)"/>
<text x="65" y="82" text-anchor="middle" fill="#d36b27" font-size="13" font-family="inherit">不可辨识</text>
<line x1="240" y1="60" x2="240" y2="74" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="420,25 420,64 325,64 325,140" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="420,42 420,64 325,64" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="325,100 410,100 410,157 305,157" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="240" y1="174" x2="240" y2="190" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="240" y1="224" x2="240" y2="238" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="240" y1="272" x2="240" y2="286" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

## 教科书级展开

<!-- upkie-animation:22-parameter -->

### 局部模型

14 章线性化给出：

$$
theta_{\text{ddot}} = \alpha * \theta + \beta * \tau
\alpha = \frac{g}{l} = 19.62 \frac{1}{s}^2
\beta = -1/(m l^2) = -0.4 (rad/s^2)/(N \cdot m)
$$

这里 `theta` 用 rad，`tau` 用 N*m，`theta_ddot` 用 rad/s²。写成第 k 行数据：

$$
y_{k} = [theta_{k}, tau_{k}] [\alpha, \beta]^T + epsilon_{k}
$$

堆叠 N 个样本：

$$
y = \Phi w + \epsilon
w_{\text{hat}} = argmin \lVert \Phi w-y\lVert ^2
$$

这里 `w=[alpha, beta]^T` 是待估参数向量，与角度 `theta`（pitch angle）是不同的量。代码中统一使用 `parameters` 表示待估参数，避免混淆。

### 最小二乘推导

目标函数：

$$
J = (\Phi w-y)^T(\Phi w-y)
$$

对参数求导并令零：

$$
2 \Phi^T(\Phi w-y)=0
\Phi^T \Phi w = \Phi^T y
$$

若 `Phi^T Phi` 可逆，`w_hat=(Phi^T Phi)^-1 Phi^T y`。代码使用 `np.linalg.lstsq`，它通过更稳定的分解处理矩形矩阵，避免显式求逆。

### 为什么要训练/测试分离

本实验 500 个训练样本用于拟合，200 个独立样本用于预测。若把含噪训练目标当评估对象，模型可以通过吸收噪声看似很好；独立测试集才检查系数是否恢复了关系本身。

### 条件数与持续激励

`cond(Phi)=3.9045`，较小，说明两列没有接近共线。若所有力矩都为 0，第二列全零，beta 无法辨识；若角度与力矩总按同一比例变化，alpha/beta 会互相补偿，参数方差很大。

### 适用范围与失效条件

数据覆盖 `theta∈[-0.25,0.25] rad, tau∈[-1,1] N*m`，结论只适用于这个局部范围、固定腿形和本噪声模型。大角度、接触切换、轮胎打滑或电机温升都会改变有效参数。真实辨识还应记录时间戳、版本、激励安全边界和置信区间。

## 代码映射

```python
design = np.column_stack([train_angle, train_torque])
parameters, _, _, _ = np.linalg.lstsq(design, train_acceleration, rcond=None)
prediction = np.column_stack([test_angle, test_torque]) @ parameters
test_rmse = np.sqrt(np.mean((prediction-test_truth)**2))
```

输入是训练/测试两个独立数据集，输出为两个物理系数与测试预测。`lstsq` 不会替你证明样本激励充分，因此日志同时保存条件数。

## 动手检查点

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 22
python scripts/course_checkpoint.py --chapter 22
```

## 可视化证据

<!-- upkie-animation:22-evidence -->

- `outputs/plots/estimation_22.png`：测试集预测散点与系数对照；
- `outputs/logs/estimation_22.json`：真实/辨识参数和条件数；
- `outputs/results/estimation_22.json`：验收门槛；
- `outputs/portfolio/22/evidence.json`：作品集；
- `outputs/results/checkpoint_22.json`：自动测试。

## 故障诊断挑战

<!-- upkie-animation:22-comparison -->

令所有训练力矩为零，重新拟合。第一处异常是设计矩阵秩下降或条件数急剧增大，而不是先看测试曲线。再把训练/测试数据混在一起，观察为什么指标会虚高。

## 三档任务

- 基础任务：写出 Phi 的一行并解释每列单位。
- 岗位挑战：固定角度范围，逐步缩小力矩激励幅度，画出 beta 方差或条件数变化。
- 开放探索：加入偏置项与正则化，说明何时需要、怎样避免掩盖模型错误。

## 专业里程碑

你能给控制模型提供可追溯参数证据，并能说明它在哪些激励范围内可信。作品集应包含训练/测试划分、散点验证和一次不可辨识故障。

## 复盘与面试

1. 为什么最小二乘拟合好训练集仍不够？
2. 条件数大说明什么？
3. alpha 与 beta 的单位如何检查？
4. 为什么不能把大角度数据直接混进本线性模型？
5. 真实系统怎样设计安全持续激励？

## 下一关

23 章在模型和动作都受限时，不再直接取“最优无约束动作”，而是用二次规划显式满足轮端和耦合约束。
