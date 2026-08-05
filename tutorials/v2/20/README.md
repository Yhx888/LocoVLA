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

<!-- upkie-qa:20-q1 -->
Q 是过程噪声协方差，表达“模型预测这一步会错多少”的不确定性：离散化误差、未建模的摩擦与扰动、参数漂移都归入 Q。R 是测量噪声协方差，表达“传感器这一次读数会错多少”的不确定性：IMU 抖动、量化误差、电气噪声都归入 R。两者共同决定 Kalman 增益 K 如何分配信任：Q 相对大意味着模型不可靠，滤波器会更信测量，K 偏大；R 相对大意味着测量脏，滤波器更信预测，K 偏小。注意它们的比例才是本质——把 Q 和 R 同时放大 10 倍，K 不变，但协方差 P 的绝对值会变，影响后续融合与置信判断。本章验收要求 `final_covariance_trace <= 0.03`，就是在检查你声明的 Q/R 与实际噪声水平自洽：如果 Q/R 设置错误，协方差曲线会收敛到与真实误差不符的水平，估计看似平滑实则过度自信。这与 19 章互补滤波的系数 `alpha` 一脉相承：互补滤波用一个手调常数分配信任，Kalman 滤波把这个常数升级为由 Q、R、P 实时计算出的最优权重。
<!-- /upkie-qa -->

2. K 变大一定更好吗？

<!-- upkie-qa:20-q2 -->
不一定。K 变大意味着校正步更信任测量：`x = x- + K(z - Hx-)` 中创新项的权重更高。好处是收敛快、能迅速跟上真实状态变化；代价是测量噪声会更多地直接进入估计。极端情况 K→1（标量情形），估计几乎复制测量，滤波器退化成“原始测量曲线”，本章的 `rmse_improvement_ratio >= 1.5` 验收会直接失败——因为估计的 RMSE 和原始测量一样大，没有任何改善。反过来 K→0 则完全信模型，测量被忽略，任何模型误差都会无界累积。正确的理解是：K 不是越大或越小越好，而是应当等于由 P⁻、H、R 计算出的最优值 `K = P-Hᵀ(HP-Hᵀ+R)⁻¹`，它在“模型漂移”和“测量抖动”之间取均方误差最小的折中。本章正文的数值算例（预测 0.10 rad、测量 0.18 rad、K=0.25）展示的正是这个折中：校正后 0.12 rad，既没有全信测量也没有全信预测。工程上如果你发现需要手动调大 K 才能工作，真正该改的往往是 Q（承认模型更不准），而不是绕过增益公式。
<!-- /upkie-qa -->

3. 为什么 P 的单位不能忽略？

<!-- upkie-qa:20-q3 -->
因为 P 是状态估计误差的协方差，单位是状态单位的平方（本章俯仰角状态的 P 单位是 rad²），它直接参与增益计算 `K = P-Hᵀ(HP-Hᵀ+R)⁻¹`，单位错了 K 的数值就错了。常见错误有三类：一是把标准差当方差填（差一个平方，0.1 rad 的标准差应填 P=0.01 rad²，填成 0.1 会让初始不确定度虚高 10 倍）；二是角度用了度而噪声用了弧度，Q、R、P 单位不一致，增益分配完全失真；三是多维状态时不同分量单位不同（rad 与 rad/s），协方差矩阵对角元单位分别是 rad² 与 rad²/s²，交叉项是 rad²/s，初始化时随手填同一个数会隐式假设错误的相对不确定度。本章专业里程碑特意要求作品集包含“一次 Q/R 单位错误诊断”，就是因为这类 bug 不报错、不崩溃，只表现为协方差曲线收敛到不合理的水平或 RMSE 改善不达标，必须靠单位检查才能定位。检查方法很朴素：把每个矩阵元素的单位手写出来，验证 `HP-Hᵀ` 与 R 单位一致（都是测量单位的平方），否则相加本身就是非法运算。
<!-- /upkie-qa -->

4. Joseph 形式解决什么数值问题？

<!-- upkie-qa:20-q4 -->
它解决协方差更新在浮点运算下丢失对称性和半正定性的问题。教科书简式 `P = (I-KH)P-` 在数学上与 Joseph 形式等价，但它是两个矩阵的单边乘积，浮点舍入误差会让结果逐渐失去对称性；当 K 接近最优值且测量很准时，`(I-KH)` 接近奇异，小的舍入误差可能让 P 的某个特征值变成负数。协方差一旦非半正定，物理上等价于“方差为负”，后续增益计算会产生无意义甚至发散的结果——这类故障往往在滤波器运行成千上万步之后才爆发，极难排查。Joseph 形式 `P = (I-KH)P-(I-KH)ᵀ + KRKᵀ` 把更新写成两个“合同变换”（sandwich form）之和：只要 P⁻ 和 R 半正定，两项都天然半正定，其和也半正定；同时表达式本身对称，舍入误差不会破坏对称性。代价是多几次矩阵乘法，对本章的低维状态完全可以忽略。工程启示与 23 章的 `2e-15` 数值违例讨论同源：数值稳定性不是数学正确性的赠品，要靠算法形式主动保证。长时间运行的实机估计器（如 21 章的 301 步闭环 EKF/UKF）尤其应默认使用 Joseph 形式。
<!-- /upkie-qa -->

5. 哪些接触事件会破坏本章线性假设？

<!-- upkie-qa:20-q5 -->
本章 Kalman 滤波假设状态转移和观测都是线性的、噪声是高斯的、参数在运行中不变。轮足机器人上至少四类接触事件会破坏这些假设。第一，轮胎打滑：轮编码器与地面速度的线性关系瞬间失效，观测模型 H 隐含的“轮转速正比于前进速度”不再成立，测量残差不再是零均值高斯。第二，碰撞与冲击（如 10 章 slip demo 中的场景）：冲击力是持续时间极短的大幅非高斯扰动，过程噪声的高斯假设被打破，滤波器会把冲击误解释为缓慢的状态漂移。第三，接触模式切换：轮子离地再落地（跳跃、越障、跌倒边缘）时，系统动力学在“有接触”和“无接触”两套方程间切换，单一线性模型 A 无法同时描述两者。第四，静摩擦-滑动摩擦切换：低速时轮端处于粘滞区，力矩与加速度的关系强非线性。工程对策分层次：轻度非线性用 21 章的 EKF/UKF（局部线性化或 sigma 点传播）；模式切换需要交互多模型（IMM）或接触检测后重置协方差；冲击类事件常配合创新门限（innovation gating）把异常测量拒之门外。识别“当前假设何时失效”正是本章与 21 章的分界线。
<!-- /upkie-qa -->

## 下一关

21 章接入 MuJoCo 原生 IMU 与轮编码器，用同一组非线性观测比较 EKF/UKF，并让 UKF 估计进入平衡控制闭环。
