# 16 状态空间与可控性

> 建设状态：可执行  
> 阶段：经典控制  
> 作品集目录：`outputs/portfolio/16`

## 岗位任务

你已经有一个四状态线性模型，下一步准备设计 LQR。但“矩阵能相乘”不代表输入真的能控制所有状态。你的任务是建立明确的状态顺序和单位，计算可控矩阵与可观矩阵，并故意切断轮端力矩到俯仰加速度的耦合，证明错误模型会把可控秩从 4 降到 2。

## 学习目标

- 把多个一阶微分方程写成 `x_dot=A x+B u`；
- 解释 A、B、C、D 的尺寸、职责和单位；
- 逐步构造 `[B, AB, A²B, A³B]`；
- 用秩判断局部线性系统是否可控/可观；
- 说明奇异值受状态单位和缩放影响，不能跨缩放直接比较。

## 前置关卡

需要 14 章的线性化动力学和 15 章的极点概念。矩阵乘法规则在 03-04 章已铺垫。

## 先观察现象

```powershell
python scripts/run_classical_control_lab.py --chapter 16
```

正常输入映射的四个可控奇异值都非零；故意删除 B 矩阵中的俯仰耦合后，后两个奇异值落到数值零附近。真实结果：

controllability_rank: 4.0
faulty_input_controllability_rank: 2.0

即使 A 矩阵仍包含不稳定俯仰动力学，错误 B 让轮端动作无法改变那两个状态方向。

## 直觉与概念

<!-- upkie-animation:16-intuition -->

状态空间像一本动态账本：A 说明系统自己怎样从当前状态走到下一刻，B 说明输入从哪些入口改变状态，C 说明传感器读出哪些组合，D 说明输入是否直接出现在输出。

可控性问：“有限时间内，输入能不能把状态推到任意局部方向？”可观性问：“从一段输出历史，能不能反推出全部内部状态？”它们不是控制器好坏分数，而是设计前的结构门槛。

## 数据流与尺寸

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 340" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="36" y="10" width="170" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="121.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="121.0" dy="0">u: 1×1</tspan>
<tspan x="121.0" dy="22">轮端等效力矩 N·m</tspan>
</text>
<rect x="460" y="10" width="210" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="565.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="565.0" dy="0">x: 4×1</tspan>
<tspan x="565.0" dy="22">x, xdot, theta, thetadot</tspan>
</text>
<rect x="36" y="80" width="150" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="111.0" y="98" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="111.0" dy="0">B: 4×1</tspan>
<tspan x="111.0" dy="22">输入映射</tspan>
</text>
<rect x="460" y="80" width="170" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="545.0" y="98" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="545.0" dy="0">A: 4×4</tspan>
<tspan x="545.0" dy="22">自由动力学</tspan>
</text>
<rect x="185" y="148" width="130" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.0" y="169" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">xdot: 4×1</text>
<rect x="36" y="218" width="150" height="44" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="111.0" y="234" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="111.0" dy="0">D: 2×1</tspan>
<tspan x="111.0" dy="22">本章为 0</tspan>
</text>
<rect x="460" y="218" width="170" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="545.0" y="236" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="545.0" dy="0">C: 2×4</tspan>
<tspan x="545.0" dy="22">测量 x 与 theta</tspan>
</text>
<rect x="200" y="282" width="100" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.0" y="303" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">y: 2×1</text>
<line x1="565" y1="58" x2="565" y2="80" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="121" y1="58" x2="121" y2="80" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="565,128 565,164 250,164" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="121,128 121,164 250,164" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="565" y1="196" x2="565" y2="218" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="121" y1="196" x2="121" y2="218" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="565,266 565,298 250,298" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="121,262 121,298 250,298" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

## 教科书级展开

<!-- upkie-animation:16-parameter -->

### 1. 状态和单位

$$
x = [position, velocity, pitch_{\text{error}}, pitch_{\text{rate}}]^T
$$

- position：m；
- velocity：m/s；
- pitch_error：rad；
- pitch_rate：rad/s；
- input `u`：本简化模型的作用力（N），作用于基座（等价于地面对轮的水平反作用力）。注意：与 Ch14 的轮端力矩 `tau`（N·m）通过 `F = tau/r`（r 为轮半径）关联，二者单位与作用点不同，不可直接混用。

由于状态混合不同单位，A、B 各元素也有不同单位。矩阵形状正确不代表量纲正确。

### 2. 四个标量方程

采用 `m=10 kg, l=0.5 m, g=9.81 m/s²`：

$$
position_{\text{dot}} = velocity
velocity_{\text{dot}} = (\frac{1}{m}) u
pitch_{\text{error},\text{dot}} = pitch_{\text{rate}}
pitch_{\text{rate},\text{dot}} = (\frac{g}{l}) pitch_{\text{error}} - (1/(m l)) u
$$

整理为：

x_dot = A x + B u

$$
A = [[0, 1,   0, 0],      [0, 0,   0, 0],      [0, 0,   0, 1],      [0, 0, \frac{g}{l}, 0]]
$$
$$
B = [[0],      [\frac{1}{m}],      [0],      [-1/(m l)]]
$$

数值上 `1/m=0.1`，`g/l=19.62`，`-1/(ml)=-0.2`。

### 3. 为什么只看 B 不够

B 的第一和第三行是 0，意味着输入不能在同一瞬间直接跳变位置和角度。但输入先改变速度，速度经过 A 的动态传播后再改变位置；因此还要看 `AB, A²B, A³B`。

四状态单输入系统的可控矩阵：

$$
Co = [B, AB, A^2 B, A^3 B]
$$

如果四列能张成四维空间，即 `rank(Co)=4`，则局部线性模型可控。

### 4. 故障模型为什么降秩

把 B 最后一行 `-1/(ml)` 错写为 0，相当于声明轮端输入不会影响俯仰角加速度。此时输入只能控制位置/速度两个方向，俯仰/俯仰角速度由自身不稳定动力学演化，所以秩降为 2。

这类错误常来自执行器符号、关节映射或建模时漏掉耦合项。LQR 求解器可能仍返回矩阵或直接失败，但根因在模型结构，不在 Q/R 调参。

### 5. 可观矩阵

假设测量位置和俯仰角：

$$
C = [[1,0,0,0],      [0,0,1,0]]
$$

可观矩阵：

$$
Ob = [C; CA; CA^2; CA^3]
$$

位置随时间的变化暴露速度，角度随时间的变化暴露角速度，因此本模型 `rank(Ob)=4`。

### 6. 奇异值告诉我们什么

秩是“有没有这个方向”，奇异值还显示不同方向的数值强弱。实验最小可控奇异值：

minimum_controllability_singular_value: 0.09987027976806588

但这个值依赖状态单位：把 m 改成 mm 会改变矩阵缩放和奇异值，即使物理系统没变。因此跨项目比较前要先做一致的状态归一化。

### 7. 假设与失效条件

可控/可观结论针对当前平衡点的连续线性模型。动作饱和后，“数学上可达”不代表给定时间内物理上能到达；传感器噪声会让理论可观方向很难估计；接触切换会改变 A、B。工程验收还必须结合条件数、限幅和闭环仿真。

## 代码映射

```python
def controllability_matrix(A, B):
    blocks = [B]
    for power in range(1, A.shape[0]):
        blocks.append(np.linalg.matrix_power(A, power) @ B)
    return np.concatenate(blocks, axis=1)

Co = controllability_matrix(A, B)
rank = np.linalg.matrix_rank(Co)
singular_values = np.linalg.svd(Co, compute_uv=False)
```

输入是数值矩阵，输出是可控矩阵、秩和奇异值。必须先检查 A/B 形状和状态顺序；换顺序时 A、B、C 和控制器 K 都要同步置换。

## 动手检查点

```powershell
python scripts/run_classical_control_lab.py --chapter 16
python scripts/course_checkpoint.py --chapter 16
```

真实输出：

controllability_rank: 4.0
observability_rank: 4.0
minimum_controllability_singular_value: 0.09987027976806588
faulty_input_controllability_rank: 2.0

## 可视化证据

<!-- upkie-animation:16-evidence -->

- `outputs/plots/classical_16.png`：正常/故障可控矩阵奇异值；
- `outputs/logs/classical_16.json`：状态顺序和 A/B 数值；
- `outputs/results/classical_16.json`：秩门槛；
- `outputs/portfolio/16/evidence.json`：作品集；
- `outputs/results/checkpoint_16.json`：自动测试。

## 故障诊断挑战

<!-- upkie-animation:16-comparison -->

把 `B[3,0]` 置零，先不要运行 LQR。检查可控秩是否从 4 变 2，再追查“为什么输入不再影响 pitch_rate”。这比盲目增大 Q 的俯仰权重更快。

第二个故障是把状态顺序从 `[x,xdot,pitch,pitch_rate]` 改成 `[pitch,pitch_rate,x,xdot]`，但不置换 K。矩阵仍能相乘，语义却完全错误；第一证据是状态字段与增益列的契约不一致。

## 三档任务

- 基础任务：手写 A/B/C 的形状与单位，运行实验并解释秩。
- 岗位挑战：只测量 pitch，计算可观秩并说明缺失哪个状态方向。
- 开放探索：给状态做尺度归一化，比较归一化前后的奇异值和条件数。

## 专业里程碑

你现在能在设计反馈器之前审计模型结构，并能识别“算法调不动”其实是输入映射缺失。作品集应包含 A/B/C 契约表、奇异值图和一次状态顺序错配复盘。

## 复盘与面试

1. B 第一行是 0，为什么位置仍然可控？

<!-- upkie-qa:16-q1 -->
B 第一行为 0 只说明输入不能瞬时改变位置（力矩直接改变的是加速度层），但可控性看的不是单步直接作用，而是影响能否通过动力学链条传递：力矩→速度变化→位置变化，对应可控性矩阵里的 `A*B`、`A^2*B` 等高阶项。只要 `[B, AB, A^2B, A^3B]` 满秩（本章秩为 4），输入就能经由若干步间接驱动所有状态。日常直觉也如此：骑车时手不能直接平移身体，但通过把手→转向→轨迹仍能控制位置。
<!-- /upkie-qa -->

2. 可控秩为 4 是否保证有限力矩下任意快到达？

<!-- upkie-qa:16-q2 -->
不保证。可控性是结构性结论：存在某个（可能很大的）输入序列能在有限时间内把状态从任意初值驱动到任意目标，它对"要多大输入"没有任何承诺。要求到达时间越短，需要的力矩越大（大致按时间的幂次增长）；而 Upkie 轮端力矩被 `ctrlrange` 限在 `±1 N*m`，饱和之后再"可控"也只能按物理允许的速度收敛，甚至存在根本救不回来的初始偏差。所以可控秩 4 只是"能不能"的入场券，"多快、多大代价"要由 17 章的 LQR 代价权衡和饱和分析回答。
<!-- /upkie-qa -->

3. 为什么只测位置也可能观察到速度？

<!-- upkie-qa:16-q3 -->
因为速度会通过动力学在位置序列里留下痕迹：相邻两拍的位置差就携带速度信息。形式化地看，可观测性矩阵 `[C; CA; CA^2; ...]` 中 `C` 只取位置行，但 `CA` 行里会出现速度项（位置的导数就是速度），只要这些行合起来满秩，速度就能从位置时间序列中重建——这正是状态观测器（如卡尔曼滤波）的理论基础。但工程上要注意：差分重建速度会放大量化噪声（同 13 章 D 项问题），可观测不等于估计得准，噪声大时仍需要滤波器融合多传感器。
<!-- /upkie-qa -->

4. 状态单位改变为什么会影响奇异值？

<!-- upkie-qa:16-q4 -->
奇异值是对矩阵数值大小敏感的量，而状态单位选择直接改变矩阵元素的数值：把位置从米换成毫米，相当于对状态做对角缩放变换 `x' = T*x`，可控性矩阵变成 `T*[B, AB, ...]`，秩不变但奇异值被重新分布——某些方向被人为放大或压缩几个数量级。因此用"最小奇异值多小"衡量可控强弱时，必须先把状态归一化到可比较的物理尺度（如除以各自的典型幅值），否则结论反映的是单位制而不是物理。秩判据本身对单位不敏感，但数值秩的阈值判断也会受病态缩放干扰。
<!-- /upkie-qa -->

5. 接触切换时为什么要重新审查 A/B？

<!-- upkie-qa:16-q5 -->
因为 A/B 是在"轮子接地且纯滚动"这个约束条件下推导的，接触状态一变，动力学结构本身就变了，不是参数微调而是换了一套方程：离地时轮端力矩失去对俯仰和位置的作用通路（B 中对应项归零，系统可能直接失去可控性）；打滑时纯滚动约束失效，轮角与位移解耦，等效 B 缩小且方向改变。在错误的 A/B 上做可控性分析或 LQR 设计，结论对真实系统无效。工程做法是按接触模式分段建模（混合系统），并用接触监控信号触发模型和控制器切换。
<!-- /upkie-qa -->

## 下一关

17 章会在这套四状态模型上定义状态代价 Q 和动作代价 R，求解 LQR 增益；可控性是 Riccati 设计能够成立的结构前提。
