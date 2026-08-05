# 04 微积分、微分方程与线性化

> 建设状态：可执行  
> 阶段：数学与工具  
> 作品集目录：`outputs/portfolio/04`

## 岗位任务

你要向控制团队解释：为什么倒立摆在小角度时可以用线性模型设计 LQR，而机器人已经倾斜 60 度时，继续相信同一近似会产生明显错误。

本关交付非线性摆与线性化模型的误差曲线、中心差分校验、二次型矩阵梯度和有效范围说明。岗位标准不是会写导数符号，而是能把近似的假设与失效条件写进设计评审，并能检查优化器使用的梯度。

## 学习目标

- **理解**：用“变化率”和“状态更新”解释导数与微分方程。
- **推导**：从 Taylor 展开得到中心差分和 `sin(theta)≈theta`，从逐项求导得到二次型梯度。
- **实现**：量化线性化误差，并用数值差分审计矩阵求导结果。

## 前置关卡

完成 `03`，理解状态向量和坐标系。只需要高中函数、斜率和三角函数；Taylor 展开会从直觉开始逐项解释。

## 先观察现象

比较两个数：

- `$theta` — 0.1 rad 时：sin(theta) ≈ 0.09983
- `$theta` — 1.0 rad 时：sin(theta) ≈ 0.84147

在 0.1 rad 附近，`sin(theta)` 与 `theta` 很接近；在 1 rad 附近，相差约 16%。线性化不是把非线性“消灭”，而是在选定工作点附近用更简单模型近似。

## 直觉与概念

<!-- upkie-animation:04-core -->

### 导数：此刻变化得有多快

位置曲线的斜率是速度，角度曲线的斜率是角速度。导数不是新的物理量魔法，而是“极短时间内的变化量除以时间”。

### 微分方程：状态怎样产生下一刻

普通方程求未知数，微分方程描述“当前状态和输入怎样决定变化率”。机器人动力学可抽象为：

$$
x_{\text{dot}} = f(x, u)
$$

`x` 是状态，`u` 是控制输入，`f` 是动力学规律。仿真器用有限时间步反复积分这个变化率。

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -65 860 155" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="24" width="140" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="90.0" y="46" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">当前状态 x_k</text>
<rect x="182" y="24" width="140" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="252.0" y="46" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">动力学 f(x,u)</text>
<rect x="344" y="24" width="152" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="419.9" y="46" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">状态变化率 x_dot</text>
<rect x="518" y="24" width="140" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="587.8" y="46" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">数值积分 dt</text>
<rect x="680" y="24" width="140" height="50" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="749.8" y="43" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="749.8" dy="0">下一状态</tspan>
<tspan x="749.8" dy="22">x_(k+1)</tspan>
</text>
<rect x="202" y="-34" width="130" height="32" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="267.0" y="-13" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">控制输入 u_k</text>
<line x1="267" y1="-2" x2="252" y2="24" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="160" y1="41" x2="182" y2="41" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="322" y1="41" x2="344" y2="41" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="496" y1="41" x2="518" y2="41" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="658" y1="41" x2="680" y2="41" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="750,74 750,100 90,100 90,58" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

## 教科书级展开

### 1. 中心差分的推导

在 `x` 附近，光滑函数可写成：

$$
f(x+h) = f(x) + h f'(x) + h^\frac{2}{2} f''(x) + h^\frac{3}{6} f'''(x) + \dots
f(x-h) = f(x) - h f'(x) + h^\frac{2}{2} f''(x) - h^\frac{3}{6} f'''(x) + \dots
$$

第一式减第二式，偶次项抵消：

$$
f(x+h) - f(x-h) = 2h f'(x) + h^\frac{3}{3} f'''(x) + \dots
$$

两边除以 `2h`：

$$
f'(x) \approx  [f(x+h)-f(x-h)]/(2h)
$$

被忽略的首项与 `h^2` 成正比，因此中心差分是二阶精度。这里“二阶”描述误差随步长缩小的速度，不是说只求二阶导数。

本关用 `f(x)=sin(x)`、`x=0.4 rad`、`h=1e-5 rad`，解析导数为 `cos(0.4)`。真实误差：

1.4298007222635079e-11

过小的 `h` 会让两次接近的浮点数相减，舍入误差开始主导，所以步长不是越小越好。

### 2. 单摆非线性模型

长度为 `l` 的理想单摆满足：

$$
theta_{\text{ddot}} = -(\frac{g}{l}) \sin(\theta)
$$

| 符号 | 含义 | SI 单位 |
|---|---|---|
| `theta` | 摆角，相对向下平衡点 | rad |
| `theta_ddot` | 角加速度 | rad/s^2 |
| `g` | 重力加速度，本关取 9.81 | m/s^2 |
| `l` | 摆长，本关取 1.0 | m |

`g/l` 的单位是 `1/s^2`；弧度在 SI 中视为无量纲，因此结果是 `rad/s^2`。

### 3. 在平衡点附近线性化

围绕 `theta_0=0` 展开 `sin(theta)`：

$$
\sin(\theta) = \sin(0) + \cos(0)(\theta-0) - \sin(0)/2 (\theta-0)^2 + \dots
           = \theta - \theta^\frac{3}{6} + \dots
$$

保留一阶项：

$$
\sin(\theta) \approx  \theta
theta_{\text{ddot}} \approx  -(\frac{g}{l}) \theta
$$

被忽略的主要项是 `theta^3/6`。角度翻倍时，这部分误差约放大 8 倍，这解释了线性模型为什么快速离开有效区。

更一般地，对 `x_dot=f(x,u)` 在平衡点 `(x_0,u_0)` 附近令：

delta_x = x - x_0
delta_u = u - u_0

一阶 Taylor 展开：

$$
delta_{x,\text{dot}} \approx  A delta_{x} + B delta_{u}
A = partial f / partial x evaluated at (x_{0},u_{0})
B = partial f / partial u evaluated at (x_{0},u_{0})
$$

这正是后续状态空间与 LQR 的入口。平衡点写错，`delta_x` 就不是小量，线性控制器的前提从第一步已经失效。

### 4. 数值有效范围

本关比较 `-(g/l)sin(theta)` 与 `-(g/l)theta`：

|theta| <= 10 deg 时最大误差 = 0.008600189943797076 rad/s^2
- `$theta` — 60 deg 时误差       = 1.7772987661132813 rad/s^2

验收阈值不是宇宙通用标准，只针对本实验 `g=9.81 m/s^2`、`l=1 m` 和指定角度范围。控制系统允许多大模型误差，还取决于闭环带宽、输入限幅和安全余量。

### 5. 代码映射

```python
def pendulum_acceleration(theta, gravity=9.81, length=1.0):
    return -(gravity / length) * np.sin(theta)

def linearized_pendulum_acceleration(theta, gravity=9.81, length=1.0):
    return -(gravity / length) * np.asarray(theta)
```

两种模型保持相同输入、输出和单位，才能公平比较。

### 6. 矩阵求导：一次处理多个状态方向

#### 第一层：直觉

一元函数的导数告诉你“往右走一点，函数升还是降”。状态向量有多个分量时，梯度把每个方向的斜率排成一个向量；沿梯度方向走，函数上升最快，沿负梯度方向走，函数下降最快。

#### 第二层：符号拆解

$$
J(x) = 0.5 x^T A x
gradient J = 0.5 (A + A^T) x
$$

| 符号 | 含义 | 本关形状 |
|---|---|---|
| `x` | 归一化状态偏差 `[x1,x2]^T` | 2x1 |
| `A` | 二次代价权重矩阵 | 2x2 |
| `J` | 标量代价 | 1 |
| `gradient J` | 对每个状态分量的偏导 | 2x1 |

#### 第三层：物理意义与单位

在控制中，`x` 可以包含角度、角速度和位置，`J` 衡量偏离目标的代价。若状态带不同 SI 单位，`A_ij` 必须抵消 `x_i x_j` 的单位，或者先把状态归一化。本关使用无量纲教学状态，避免把单位尺度误当成控制偏好。

#### 第四层：为什么需要

梯度下降、系统辨识、轨迹优化和神经网络训练都要回答“改哪个变量能最快降低误差”。解析梯度快，但容易写错转置或系数；中心差分慢，却适合用小规模算例做独立审计。

#### 第五层：逐项推导，不写“由此可得”

先把二次型展开成求和：

J = 0.5 sum_i sum_j x_i A_ij x_j

对第 `k` 个分量求偏导。`x_k` 可能出现在左边的 `x_i`，也可能出现在右边的 `x_j`：

$$
partial J / partial x_{k}
= 0.5 sum_{j} A_{kj} x_{j} + 0.5 sum_{i} x_{i} A_{ik}
= 0.5 [A x]_k + 0.5 [A^T x]_k
= 0.5 [(A+A^T)x]_k
$$

把所有 `k` 排回向量：

$$
gradient J = 0.5 (A+A^T)x
$$

当 `A=A^T` 时才可简化为 `gradient J=A x`。非对称矩阵直接写 `A x` 会漏掉另一半贡献。

#### 第六层：可手算的数值例子

$$
A = [[4, 1],      [1, 3]]
x = [0.4, -0.2]^T
$$

因为 `A` 对称：

$$
gradient J = A x
           = [4 \cdot 0.4 + 1 \cdot (-0.2), 1 \cdot 0.4 + 3 \cdot (-0.2)]^T
           = [1.4, -0.2]^T
$$

以 `h=1e-6` 逐维中心差分，实际得到：

analytic = [1.4000000000000001, -0.20000000000000007]
numeric  = [1.3999999999569912, -0.20000000000575113]
max error = 4.3008929751e-11

#### 第七层：代码映射

`quadratic_gradient()` 实现通用的 `0.5*(A+A.T)@x`；`finite_difference_gradient()` 每次只扰动一个分量，形成独立数值基线。第 04 关日志的 `matrix_derivative` 节保存 `A`、`x`、两种梯度和差分步长，结果文件要求最大误差不超过 `1e-8`。

#### 适用范围与失效条件

- `A` 与 `x` 维度必须一致，输入必须有限；
- 差分步长必须为正，过大会产生截断误差，过小会放大舍入误差；
- 梯度检查只在选定点成立，不能证明所有输入都正确；
- 有不可导的绝对值、接触切换或裁剪时，左右导数可能不同，中心差分不再代表唯一导数。

### 假设与失效条件

- 理想刚性单摆，无摩擦、无执行器和接触；
- 在 `theta=0` 附近线性化，不适用于绕圈或大角度跌倒；
- `g`、`l` 为常数；
- 本关用向下平衡点教学数学，Upkie 平衡控制会围绕自身审计得到的平衡角定义误差；
- 接触切换、饱和和摩擦属于分段或强非线性现象，不能只靠一阶 Taylor 模型覆盖。

## 动手检查点

```powershell
python scripts/run_foundation_lab.py --chapter 04 --seed 0
python scripts/course_checkpoint.py --chapter 04
```

应生成 `foundation_04.json` 结果、日志、双面板图和 `outputs/portfolio/04/evidence.json`。验收要求小角度误差不超过 `0.01 rad/s^2`，60 度误差大于 `0.5 rad/s^2`，矩阵梯度误差不超过 `1e-8`。

常见失败一：大角度误差也很小。检查是否错误地让“非线性模型”也返回了 `theta`。  
常见失败二：小角度误差超限。检查输入是否为弧度，或平衡点是否改动。
常见失败三：解析梯度恰好差一倍。检查目标函数前面的 `0.5` 是否与求导公式一致。

## 可视化证据

左图绿色阴影表示 `±10 deg` 小角度区，右图并列显示解析梯度和中心差分梯度。三重证据为：

- **视觉**：`outputs/plots/foundation_04.png` 同时显示模型有效区和两组梯度柱；
- **日志**：`outputs/logs/foundation_04.json` 的 `matrix_derivative` 保存矩阵、点、步长和完整数值；
- **自动测试**：`python -m pytest tests/test_foundations.py -q` 检查标量差分、矩阵梯度和证据契约。

通过本关后，你已经能在设计评审中把“线性模型有效”改写为可检验的陈述：“围绕哪个点、在多大范围、误差多少、何时切换安全策略”。

## 故障诊断挑战

假装机器人已经倾斜 60 度，却仍用线性模型预测角加速度：

```powershell
python -c "import sys,numpy as np; sys.path.insert(0,'src'); from upkie_mujoco_course.foundations.math_tools import *; a=np.deg2rad(60); print('非线性=',pendulum_acceleration(a)); print('线性=',linearized_pendulum_acceleration(a)); print('误差=',abs(pendulum_acceleration(a)-linearized_pendulum_acceleration(a)))"
```

诊断报告必须写明：错误不是数值积分造成的，而是在积分前，动力学近似已经偏离 `1.7773 rad/s^2`。

## 三档任务

- **基础任务**：用 `theta^3/6` 估算 10 度处 `sin(theta)≈theta` 的误差数量级。
- **岗位挑战**：手算二次型梯度，再故意去掉目标函数的 `0.5`，用数值差分定位倍数错误。
- **开放探索**：选择非对称 `A`，验证为什么梯度是 `0.5(A+A^T)x` 而不是 `Ax`。

## 复盘与面试

1. 中心差分为什么比前向差分精度高一阶？

<!-- upkie-qa:04-q1 -->
用泰勒展开看最清楚。前向差分 $\frac{f(x+h)-f(x)}{h}$ 展开后余项首项是 $\frac{h}{2}f''(x)$，误差是 $O(h)$。中心差分 $\frac{f(x+h)-f(x-h)}{2h}$ 中，$f(x+h)$ 和 $f(x-h)$ 展开式相减时，偶数阶项（含 $f''$ 的 $h^2$ 项）符号相反正好抵消，剩下的首个误差项是 $\frac{h^2}{6}f'''(x)$，所以误差是 $O(h^2)$，比前向差分高一阶。直观理解：中心差分对称地取两侧信息，把向一侧倾斜的系统性偏差抵消了。
<!-- /upkie-qa -->

2. 线性化必须声明哪一个平衡点？

<!-- upkie-qa:04-q2 -->
必须声明在哪个工作点 $(x^*, u^*)$ 处展开，因为线性化得到的 $A = \partial f/\partial x$、$B = \partial f/\partial u$ 是在该点求的雅可比，换一个点矩阵就不同。对倒立摆，直立点 $\theta=0$（不稳定平衡）和下垂点 $\theta=\pi$（稳定平衡）线性化后的 $A$ 矩阵符号相反，基于错误平衡点设计的 LQR 增益控制另一个平衡点时会把系统推向发散。所以任何线性控制器的有效性声明都必须附带「在哪个平衡点附近」这个前提。
<!-- /upkie-qa -->

3. `sin(theta)≈theta` 为什么要求弧度？

<!-- upkie-qa:04-q3 -->
因为这个近似来自泰勒展开 $\sin\theta = \theta - \theta^3/6 + \cdots$，而泰勒展开成立的前提是 $\theta$ 用弧度——只有弧度制下 $\sin$ 的导数才是 $\cos$，导数在 0 处才等于 1，斜率才能直接用 $\theta$ 本身近似。若用角度制，$\sin(30°) = 0.5$ 而 $\theta = 30$，两者差 60 倍，近似彻底失效。弧度是「弧长除以半径」的无量纲自然单位，数学公式默认都建立在它之上；工程代码里所有角度变量都应统一用弧度存储，只在显示时转成度。
<!-- /upkie-qa -->

4. 测试为什么同时要求小角度误差小、大角度误差大？

<!-- upkie-qa:04-q4 -->
这是在验证「近似的边界」而不只是「近似的正确性」。只测小角度误差小，无法区分「正确实现了小角度近似」和「把 $\sin$ 写成了恒等于 $\theta$ 的 bug」——后者在小角度测试里也能满分通过。加上「大角度（如 1 rad）处误差必须明显变大」的断言，才能确认被测代码确实是一个有适用范围的近似，而不是一个碰巧在小区间正确的错误实现。这种「反面断言」是验证近似类代码的通用技巧。
<!-- /upkie-qa -->

5. 控制器进入饱和后，线性闭环分析还缺少哪项事实？

<!-- upkie-qa:04-q5 -->
缺少的事实是：饱和后实际输出被限幅在 $u_{max}$，控制器不再是线性环节 $u = -Kx$，整个闭环变成了非线性系统。基于线性模型算出的稳定性、收敛速度、稳定域结论在饱和区间内不再成立：一个线性分析稳定的系统，在大偏差 + 饱和下可能根本拉不回来（可恢复域缩小）。所以工程上要额外回答：执行器限幅多大、典型扰动下需要多大控制量、饱和会不会长时间持续（伴随积分项时还会引发 windup）。
<!-- /upkie-qa -->

6. 二次型矩阵非对称时，为什么只有对称部分影响标量代价？

<!-- upkie-qa:04-q6 -->
任意方阵都可分解为对称部分加反对称部分：$A = \frac{A+A^T}{2} + \frac{A-A^T}{2}$。对反对称部分 $S$（满足 $S^T=-S$），标量 $x^T S x$ 转置后等于自身又等于自身的相反数，所以恒为 0。因此 $x^T A x = x^T \frac{A+A^T}{2} x$，只有对称部分对代价有贡献。这也解释了为什么二次型的梯度是 $\nabla(x^TAx) = (A+A^T)x$ 而不是想当然的 $2Ax$；两者只在 $A$ 对称时才相等。
<!-- /upkie-qa -->

7. 数值梯度通过是否足以证明整个优化程序正确？边界是什么？

<!-- upkie-qa:04-q7 -->
不足以。数值梯度检查只验证了一件事：解析梯度的实现与目标函数的实现在抽查点上相互一致。它的边界：(a) 如果目标函数本身就写错了（例如丢了 0.5 倍或用错模型），梯度和函数会「一致地错」，检查照样通过；(b) 只覆盖抽查的有限点，不保证全定义域；(c) 不验证优化器逻辑（步长、收敛判据、约束处理）。所以完整的验证还需要：用有解析解的小问题做端到端测试、检查代价单调下降、核对最优解的物理合理性。
<!-- /upkie-qa -->

## 下一关

下一关 `05` 在模型之外加入测量噪声。你会看到滤波能降低随机误差，但会引入滞后，这为互补滤波、Kalman Filter 和状态估计建立直觉。
