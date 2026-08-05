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

<!-- upkie-qa:22-q1 -->
因为拟合好训练集只证明“模型记住了这批样本”，不证明“模型恢复了物理关系”。最小二乘的目标是让训练残差最小，而训练目标 y 里含噪声：当参数自由度相对样本信息量偏大、或设计矩阵列接近共线时，模型会把一部分噪声也“拟合”进参数，训练误差看似很小，参数却偏离真值。本章的防线是训练/测试分离：500 个样本用于拟合，200 个独立样本只用于预测评估。独立测试集的噪声与训练集不相关，模型记住的那部分噪声在测试集上帮不上忙，只有真正恢复了 `theta_ddot = alpha*theta + beta*tau` 这层关系的参数才能在未见过的数据上给出小的预测 RMSE。所以验收同时卡三道门：`alpha_relative_error <= 0.01`、`beta_relative_error <= 0.05`（参数本身准）和 `test_prediction_rmse_rad_s2 <= 0.03`（泛化能力够）。对控制而言这不是学究洁癖：控制器运行时遇到的永远是“新数据”，一个只会背训练集的模型接入 23 章 QP 或 24 章 MPC 后，预测误差会直接变成控制误差。
<!-- /upkie-qa -->

2. 条件数大说明什么？

<!-- upkie-qa:22-q2 -->
条件数衡量设计矩阵 Phi 的列之间“接近共线的程度”，它大说明参数辨识对噪声极度敏感：观测数据里一点点噪声，会被放大成参数估计里很大的偏差。直觉上，当两列接近共线（比如角度与力矩总按同一比例变化）时，alpha 多一点、beta 少一点可以产生几乎相同的预测，数据无法区分这两种解释，参数互相补偿、估计方差极大；极限情况是某列全零（所有力矩都为 0），beta 完全不可辨识。这就是持续激励（persistent excitation）条件的含义：输入必须“各个方向都动过”，参数才能被数据区分开。本实验 `cond(Phi)=3.9045`，说明角度列和力矩列方向充分分离，验收门槛是 `design_condition_number <= 5.0`。工程上条件数大的常见成因有：激励信号太单调（只用一个频率的正弦）、采样区间太窄（图中“窄激励/共线列→不可辨识”的那条虚线）、或回归量之间存在物理约束（闭环控制下力矩本身就是角度的函数，两列天然相关）。所以看到条件数大，第一反应不应该是换求解器或加正则化，而是先问：激励设计是否让每个参数都留下了独立可辨的痕迹？
<!-- /upkie-qa -->

3. alpha 与 beta 的单位如何检查？

<!-- upkie-qa:22-q3 -->
用量纲方程两边对齐。本章模型是 `theta_ddot = alpha*theta + beta*tau`，左边 theta_ddot 的单位是 rad/s²。第一项中 theta 的单位是 rad，所以 alpha 必须是 1/s²，才能让 `alpha*theta` 给出 rad/s²；对照物理含义 `alpha = g/l = 19.62 1/s²`，重力加速度 g 的 m/s² 除以摆长 l 的 m，量纲恰好是 1/s²，自洽。第二项中 tau 的单位是 N·m，所以 beta 必须是 (rad/s²)/(N·m)；对照 `beta = -1/(m l²) = -0.4`，而 1/(kg·m²) 正是转动惯量的倒数，力矩除以转动惯量得到角加速度，量纲同样自洽（rad 在 SI 中是无量纲的）。这个检查有两层实用价值：其一，拓展回归项时（比如加入阻尼项 `gamma*theta_dot`）能立刻写出新参数应有的单位（gamma 应为 1/s），拒绝量纲不合的项；其二，能发现隐藏的单位事故——如果采集管线里角度用了度而非弧度，辨识出的 alpha 会偏离 19.62 约 57.3 倍，单位检查一眼就能定位，而纯看拟合残差反而发现不了（因为线性缩放不影响拟合优度）。这与 20 章“P 的单位不能忽略”是同一类纪律：单位是最便宜的静态检查器。
<!-- /upkie-qa -->

4. 为什么不能把大角度数据直接混进本线性模型？

<!-- upkie-qa:22-q4 -->
因为本章的线性模型是真实动力学在小角度附近的局部近似：真正的重力项是 `(g/l)sin(theta)`，只有在 `sin(theta)≈theta` 成立的范围内才能写成 `alpha*theta`。本实验数据覆盖 `theta∈[-0.25, 0.25] rad`，在这个区间 sin 近似误差小于 1%；到 0.5 rad 误差约 4%，到 1.0 rad 超过 15%。把大角度样本直接混进来，最小二乘不会报错，它会用一个‘折中的’ alpha 同时迎合小角度和大角度样本：结果是参数不再等于 g/l，在小角度区域的预测反而变差，而且这个偏差是系统性的、换 seed 也不会消失。更隐蔽的后果是参数失去物理可解释性：你无法再把辨识出的 alpha 拿去验证摆长或重心高度，也不能把它外推到任何工作点。正确的做法有两条路：要么把回归基改成非线性特征（用 `sin(theta)` 作回归量，仍是参数线性问题），要么分段辨识、每个工作点一套局部参数并声明适用范围。本章“适用范围与失效条件”小节把范围写进交付物，就是要求你像对待传感器标定一样对待辨识结果：参数必须附带它的有效域。
<!-- /upkie-qa -->

5. 真实系统怎样设计安全持续激励？

<!-- upkie-qa:22-q5 -->
核心矛盾是：辨识要求‘动得够丰富’，安全要求‘动得不要太大’，工程设计就是在两者之间找可验证的平衡。可操作的做法分四层。第一层，限幅限域：激励幅值预先限在安全包络内（如本章的 `theta∈[-0.25,0.25] rad, tau∈[-1,1] N*m`，后者正是 11 章模型契约中轮端执行器的物理限幅），并从小幅值开始逐步放大。第二层，频域设计：用多正弦叠加或 chirp 扫频覆盖关心的频段，而不是单一频率（单频只能辨识两个参数，且条件数差）；避开结构共振频率。第三层，闭环保护下激励：不关闭稳定控制器，而是在平衡控制器的参考或输出上叠加小激励信号，同时保留跌倒终止、限幅和急停；代价是闭环会引入输入与状态的相关性（推高条件数），需要更精心的激励设计或间接辨识方法。第四层，在线监控与记录：实时监视俯仰角、轮速和电流，越限立即中止；同时按本章要求记录时间戳、软件版本、激励安全边界和参数置信区间，让每次辨识都可审计、可复现。验收标准也双重：既看条件数（激励够不够），也看安全指标（边界是否被碰过），两者任一不达标都重新设计而不是降低门槛。
<!-- /upkie-qa -->

## 下一关

23 章在模型和动作都受限时，不再直接取“最优无约束动作”，而是用二次规划显式满足轮端和耦合约束。
