# 05 概率、噪声与数字信号

> 建设状态：可执行  
> 阶段：数学与工具  
> 作品集目录：`outputs/portfolio/05`

## 岗位任务

IMU 的俯仰角在机器人静止时仍会抖动。直接把测量送进高增益控制器，轮端力矩会追逐噪声；滤波太强，机器人真实倾倒时又反应过慢。

本关要用固定 seed 生成带噪俯仰角，设计一阶低通滤波器，量化 RMSE 改善与滞后，并形成参数选择记录。

## 学习目标

- **理解**：区分真实状态、测量值、随机噪声、均值、方差和采样率。
- **推导**：从加权平均得到一阶低通递推式，并解释 `alpha` 的作用。
- **实现**：在 100 Hz 信号上把固定测试集 RMSE 降低至少 1.5 倍。

## 前置关卡

完成 `04`，理解连续状态、离散采样和模型近似误差。噪声不是模型误差的同义词：一个来自随机测量波动，一个来自动力学假设不准确。

## 先观察现象

假设真实俯仰角始终为 0，但传感器依次读到：

[0.04, -0.06, 0.03, -0.02, 0.05] rad

若控制器使用 `tau=-10*theta`，它会输出方向不断变化的力矩。平均值可能接近 0，但每个瞬时样本都在驱动执行器。先观察抖动，再讨论滤波；不要把“均值正确”误解为“每一帧都可靠”。

## 直觉与概念

<!-- upkie-animation:05-core -->

### 随机变量与分布

随机变量是一次测量可能取得的数值。分布描述大量重复测量的整体规律：

- **均值 `mu`**：长期中心位置；
- **方差 `sigma^2`**：围绕均值的分散程度；
- **标准差 `sigma`**：方差开根号，与原变量单位相同。

本关测量模型：

$$
y_{k} = x_{k} + n_{k}
n_{k} ~ N(0, \sigma^2)
$$

`x_k` 是真实俯仰角，`y_k` 是测量值，`n_k` 是零均值高斯噪声。`N(0,sigma^2)` 是教学假设；真实 IMU 还可能有偏置、漂移、温度相关误差和离群点。

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 890 110" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="30" width="134" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="87.2" y="52" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">真实俯仰角 x_k</text>
<line x1="154" y1="47" x2="174" y2="47" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="174" y="30" width="120" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="234.4" y="52" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">传感器</text>
<line x1="294" y1="47" x2="314" y2="47" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="184" y="-16" width="100" height="30" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="234.4" y="4" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">噪声 n_k</text>
<line x1="234" y1="14" x2="234" y2="30" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="314" y="30" width="120" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="374.4" y="52" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">测量 y_k</text>
<line x1="434" y1="47" x2="454" y2="47" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="454" y="30" width="120" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="514.4" y="52" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">低通滤波</text>
<line x1="574" y1="47" x2="594" y2="47" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="594" y="30" width="124" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="656.4" y="52" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">估计 x_hat_k</text>
<line x1="718" y1="47" x2="738" y2="47" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="738" y="30" width="120" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="798.5" y="52" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">控制器</text>
</svg></div>

## 教科书级展开

### 1. 均值与方差

对 `N` 个样本 `y_1,...,y_N`，样本均值为：

$$
y_{\text{bar}} = (\frac{1}{N}) sum(y_{k})
$$

样本方差常写成：

$$
s^2 = [1/(N-1)] sum((y_{k}-y_{\text{bar}})^2)
$$

分母使用 `N-1` 是为了在从样本估计总体方差时修正偏差。本关重点不是背公式，而是知道均值不能描述抖动强弱，必须同时报告标准差或 RMSE。

### 2. 采样率与离散时间

采样周期 `Delta t=0.01 s`，采样率：

$$
f_{s} = 1 / \Delta t = 100 Hz
$$

100 Hz 表示每秒 100 个样本，不表示能可靠观察 100 Hz 的物理振动。根据 Nyquist 原则，不混叠的最高理论频率小于 `f_s/2=50 Hz`，工程上还需要抗混叠滤波和余量。

### 3. 一阶低通滤波器

希望新估计既保留上一时刻的稳定趋势，又吸收当前测量：

$$
x_{\text{hat},k} = \alpha y_{k} + (1-\alpha) x_{\text{hat}}_{k-1}
$$

| 符号 | 含义 | 单位 |
|---|---|---|
| `y_k` | 当前俯仰角测量 | rad |
| `x_hat_k` | 当前滤波估计 | rad |
| `x_hat_(k-1)` | 上一次估计 | rad |
| `alpha` | 当前测量权重，`0<alpha<=1` | 1 |

权重之和为 1，所以输入为常量时，估计最终会收敛到同一常量。

- `alpha=1`：完全相信当前测量，几乎不滤波；
- `alpha` 较小：曲线更平滑，但跟随真实变化更慢；
- `alpha=0`：永远保留初值，不能接受新信息，因此本实现拒绝。

### 4. 为什么会产生滞后

展开递推式：

$$
x_{\text{hat},k} = \alpha y_{k}
          + \alpha(1-\alpha)y_{k-1}
          + \alpha(1-\alpha)^2 y_{k-2}
          + \dots
$$

旧测量的权重按几何级数衰减。`alpha` 越小，旧数据保留越久，降噪更强，也更容易让快速真实运动被延迟。

### 5. RMSE 指标

本关仿真中知道真实信号，因此可计算：

$$
RMSE = \sqrt[(\frac{1}{N}) sum((x_{\text{hat},k}-x_{k})^2)]
$$

单位仍是 `rad`。真实运行 `seed=0`、噪声标准差 `0.08 rad`、`alpha=0.2` 得到：

noisy_rmse_rad          = 0.08015535824058248
filtered_rmse_rad       = 0.030415822135269246
rmse_improvement_ratio = 2.6353178251800995
sample_rate_hz          = 100.0

改善倍数定义为 `noisy_rmse/filtered_rmse`，大于 1 表示滤波后更接近真实信号。本结果只适用于当前频率、噪声和 seed；必须在多 seed 与不同运动频率上继续评估。

### 6. 代码映射

```python
filtered[0] = samples[0]
for index in range(1, samples.size):
    filtered[index] = (
        alpha * samples[index]
        + (1.0 - alpha) * filtered[index - 1]
    )
```

滤波器有内部状态 `filtered[index-1]`，因此 episode 重置或传感器重新初始化时必须明确重置初值。

### 假设与失效条件

- 噪声在本实验中为独立、零均值、高斯分布；
- 真实信号为 `0.7 Hz`、幅值 `0.1 rad` 的正弦；
- 固定采样率 100 Hz，无丢帧和时间戳抖动；
- 低通滤波不能校正固定偏置，也不能识别传感器失效；
- 突发冲击和离群点可能穿过滤波器，需要限幅、鲁棒统计或故障检测；
- 控制闭环中必须同时评估相位滞后，不能只优化 RMSE。

## 动手检查点

```powershell
python scripts/run_foundation_lab.py --chapter 05 --seed 0
python scripts/course_checkpoint.py --chapter 05
```

验收要求：`filtered_rmse_rad<=0.05`、改善倍数至少 `1.5`、采样率严格为 `100 Hz`。

应生成：

- `outputs/results/foundation_05.json`
- `outputs/logs/foundation_05.json`
- `outputs/plots/foundation_05.png`
- `outputs/portfolio/05/evidence.json`

常见失败一：改善倍数小于 1。检查 `alpha`、初值和是否错误交换真实/测量数组。  
常见失败二：曲线非常平滑但明显落后。说明 RMSE 可能尚可，但相位滞后已影响控制，需要增大 `alpha` 或使用模型融合。

## 可视化证据

灰线是带噪测量，黑线是真实俯仰角，绿线是低通结果。你应同时观察两件事：绿线抖动明显减小；峰值和过零点相对黑线略有延迟。

日志给出噪声强度、采样周期和 `alpha`；测试量化 RMSE；图表揭示单一 RMSE 不容易表达的相位滞后。三种证据共同决定参数是否可用。

通过本关后，你获得“状态估计入门”里程碑：能把传感器噪声从主观的“有点抖”改写为分布、采样率、误差和延迟。

## 故障诊断挑战

比较两个极端参数：

```powershell
python -c "import sys,numpy as np; sys.path.insert(0,'src'); from upkie_mujoco_course.foundations.math_tools import *; t=np.arange(0,4,.01); clean=.1*np.sin(2*np.pi*.7*t); noisy=clean+.08*seeded_normal_trace(0,t.size); print('alpha=1 RMSE',rmse(low_pass_filter(noisy,alpha=1)[20:],clean[20:])); print('alpha=.02 RMSE',rmse(low_pass_filter(noisy,alpha=.02)[20:],clean[20:]))"
```

不要只选择 RMSE 更低的一项。打开曲线或计算峰值时间差，判断低 `alpha` 是否因滞后损害了控制需求。

## 三档任务

- **基础任务**：用自己的话解释 `alpha=0.2` 中 20% 和 80% 分别来自哪里。
- **岗位挑战**：测试 `alpha=0.05,0.1,0.2,0.5,1.0`，用同一 seed 画 RMSE 与滞后的权衡曲线。
- **开放探索**：加入固定偏置 `0.03 rad`，证明低通滤波无法消除偏置，并提出校准或状态扩维方案。

## 复盘与面试

1. 零均值噪声为什么仍会让瞬时控制力矩抖动？

<!-- upkie-qa:05-q1 -->
「零均值」只是统计平均意义上的性质：大量样本平均后趋近 0，但每一个瞬时样本都不是 0。控制器是逐拍工作的：每个控制周期它拿到的是「真值 + 当拍噪声」，乘以增益后直接变成力矩指令，例如 $u = K_p \cdot (\theta + n_k)$ 里的 $K_p n_k$ 项每拍都在随噪声跳动。微分项更糟：对带噪信号差分会把高频噪声放大。后果是执行器频繁正反切换、发热、磨损，这就是为什么需要滤波——即使噪声长期平均为 0。
<!-- /upkie-qa -->

2. 标准差和方差的单位分别是什么？

<!-- upkie-qa:05-q2 -->
标准差的单位与原始量相同，方差的单位是原始量单位的平方。例如俯仰角噪声用弧度衡量时，标准差单位是 rad，方差单位是 rad²。因为方差是「偏差平方的平均」，平方操作把单位也平方了；标准差是方差开根号，单位才回到原量纲。实用含义：要把噪声幅度与信号幅度直接比较时必须用标准差（同量纲可比），而 Kalman Filter 等算法内部用方差/协方差矩阵做代数运算。混淆两者会导致噪声大小被高估或低估几个量级。
<!-- /upkie-qa -->

3. `alpha` 变小对噪声和滞后分别有什么影响？

<!-- upkie-qa:05-q3 -->
在 $y_k = \alpha x_k + (1-\alpha) y_{k-1}$ 中，$\alpha$ 是「相信新测量的程度」：

- $\alpha$ 变小 → 降噪更强：新测量权重低，输出主要由历史平滑值决定，随机抖动被大幅抹平。
- $\alpha$ 变小 → 滞后更大：真实信号变化时，滤波器需要更多拍才能「追上」，相当于截止频率降低、相位滞后增大。

对平衡控制这很致命：俯仰角反馈滞后相当于控制器在用「过去的姿态」做决策，滞后过大会直接失稳。所以 $\alpha$ 是降噪与实时性之间的权衡，不存在「越小越好」。
<!-- /upkie-qa -->

4. 固定 seed 的单次 RMSE 为什么不能代表总体性能？

<!-- upkie-qa:05-q4 -->
因为单次 RMSE 只是噪声分布的一次抽样：换一个 seed，噪声序列不同，RMSE 就会变化。固定 seed 保证的是可复现性（方便调试和对比），不是代表性——你可能恰好抽到一个对某方法特别有利或不利的噪声序列。要评估总体性能，应该用多个不同 seed 重复实验，报告均值和标准差（或置信区间）；比较两种滤波参数时也应在同一组 seed 上成对比较，才能区分真实差异和抽样运气。
<!-- /upkie-qa -->

5. 为什么滤波器必须在 episode 重置时重置内部状态？

<!-- upkie-qa:05-q5 -->
一阶低通滤波器的输出依赖内部状态 $y_{k-1}$（历史的指数加权平均）。episode 重置后机器人回到初始姿态，但如果不清空 $y_{k-1}$，滤波器会把上一回合末尾的状态（比如倒地前的大俯仰角）当作历史继续平滑，开局输出一段与真实状态无关的错误估计，控制器据此做出错误动作，甚至直接开局失败。在强化学习里这还会污染训练数据：不同 episode 之间通过滤波器状态「串台」，破坏了环境重置的独立性假设。所以任何带内部状态的模块（滤波器、积分器、观测器）都必须在 reset 时一并重置。
<!-- /upkie-qa -->

## 下一关

下一关 `06` 正式进入 MuJoCo。你将把本阶段学到的数组形状、时间步、坐标、线性化边界和噪声意识用于自由基座机器人的状态更新。
