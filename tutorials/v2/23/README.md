# 23 二次规划与约束

> 建设状态：可执行  
> 阶段：状态估计与优化  
> 作品集目录：`outputs/portfolio/23`

## 岗位任务

控制器想让左右轮都输出 `1 N*m`，但每轮上限只有 `0.6 N*m`，且总热/电流预算要求两轮之和不超过 `0.9 N*m`。你的任务是把“尽量接近目标”与“绝不越过约束”写成凸二次规划，区分无约束最优解和真正可执行的解。

## 学习目标

- 理解二次目标、边界和线性不等式的作用；
- 手算无约束最优解，再判断它为何不可执行；
- 运行 QP 并量化最大约束违例；
- 认识可行性、凸性和数值公差；
- 将轮端 N*m 语义与 11 章模型契约连起来。

## 前置关卡

完成 18 章动作接口和 22 章模型验证。QP 不是替代控制器，而是在给定代价和安全约束后选择一个可行动作。

## 先观察现象

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 23
```

真实结果：

solver_success: 1.0
maximum_constraint_violation: 2.1094237467877974e-15
unconstrained_constraint_violation: 1.1
constrained_objective: -1.3950000000000022
solution_sum: 0.9000000000000021

`2.1e-15` 是浮点数舍入量级，可视为数值可行；`1.1` 则表示无约束解明显超过总预算。

## 直觉与概念

<!-- upkie-animation:23-intuition -->

二次目标像一张碗形地形，最低点是最想要的动作；约束像围栏。无约束最低点若在围栏外，真正答案必须落在边界上。QP 的价值不是“让控制更聪明”，而是把安全边界从事后 clip 提升为求解问题的一部分。

## 约束分配图

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 580 350" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="40" y="8" width="170" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.0" y="30" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">期望轮端动作</text>
<rect x="40" y="58" width="160" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="120.0" y="80" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">每轮 ±0.6 N·m</text>
<rect x="40" y="106" width="160" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="120.0" y="128" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">两轮和 ≤ 0.9 N·m</text>
<rect x="270" y="8" width="210" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="375.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="375.0" dy="0">二次目标</tspan>
<tspan x="375.0" dy="22">接近目标 + 平滑代价</tspan>
</text>
<rect x="40" y="158" width="160" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="120.0" y="180" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">线性约束</text>
<rect x="255" y="158" width="130" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="320.0" y="180" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">凸 QP 求解</text>
<rect x="240" y="210" width="190" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="335.0" y="230" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="335.0" dy="0">可行动作</tspan>
<tspan x="335.0" dy="22">u_left, u_right</tspan>
</text>
<rect x="240" y="278" width="200" height="48" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="340.0" y="307" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">残差、可行性、代价日志</text>
<polyline points="125,42 125,64 375,64 375,8" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="120" y1="92" x2="120" y2="158" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="120" y1="140" x2="120" y2="158" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="375" y1="60" x2="375" y2="158" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="120" y1="192" x2="320" y2="158" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="320" y1="192" x2="320" y2="210" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="320" y1="262" x2="320" y2="278" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

## 教科书级展开

<!-- upkie-animation:23-parameter -->

### 标准形式

$$
minimize  0.5 u^T H u + f^T u
subject to A u \le  b
           lower \le  u \le  upper
$$

- `u=[u_left,u_right]^T`，单位 N*m；
- H：对称半正定 Hessian，决定碗形曲率；
- f：线性偏好项；
- A、b：耦合约束；
- lower/upper：逐轮物理限幅。

本实验：

$$
H = \diag(2,2), f=[-2,-2]^T
lower=[-0.6,-0.6], upper=[0.6,0.6]
A=[1,1], b=[0.9]
$$

### 无约束解

对目标求导：

$$
H u + f = 0
u_{\text{free}} = -H^-1 f = [1,1]^T
$$

它既超过单轮 0.6，又满足和为 2，超过 0.9 的量为 `2-0.9=1.1`。因此它不是候选执行动作。

### 受约束解的直觉

目标对两个轮子完全对称，约束也对称，最优可行解在 `u_left=u_right` 和 `u_left+u_right=0.9` 的交点：

$$
u*=[0.45,0.45]^T N \cdot m
$$

它低于单轮 0.6，恰好用满总预算。若左右轮期望不同或加了偏航约束，解不再对称，必须依赖求解器。

### 可行性、凸性与数值公差

H 半正定且约束是线性的，问题为凸 QP；若可行集非空，局部最优就是全局最优。求解器用 SLSQP 处理本教学规模问题，输出 success、message、objective 和最大违例。工程中应根据实时性和稀疏结构选择专用 QP 求解器，并为不可行问题定义安全回退。

### 适用范围与失效条件

约束本身必须可信。若 11 章的轮端语义不是 N*m、温度预算未建模、接触已丢失或约束彼此矛盾，QP 的数学可行解也可能物理不安全。不能用很小的数值违例掩盖 0.01 N*m 级安全余量；阈值必须结合执行器和浮点误差设计。

## KKT 与对偶：为什么求解成功还不够

### 第一层：直觉

最优点像碗面与围栏的接触点。目标梯度想继续下坡，活跃约束的法向力把它推回，两者恰好平衡。KKT 条件把“平衡、没有越界、约束推力方向正确、没接触的围栏不施力”写成可计算残差。

### 第二层：符号

把单轮上下界也并入 `G u<=h`，乘子记为 `lambda>=0`：

$$
L(u,\lambda)=0.5 \cdot u^T H u+f^T u+\lambda^T(G u-h)
$$

`u` 的单位为 N*m，目标已归一化。`lambda` 表示约束上界放宽一个单位时最优代价的变化率。

### 第三层：物理意义

本题只有总预算 `u_left+u_right<=0.9` 活跃，单轮 `0.6` 上界未接触。因此总预算乘子应为正，单轮上下界乘子应为 0。正乘子说明增加总电流预算能继续降低跟踪代价。

### 第四层：设计动机

`success=True` 只表示求解器满足自己的停止规则，不能证明返回值是最优可行解。工程验收必须独立重算 KKT 和 primal-dual gap，防止容差过松、梯度写错或约束漏传。

### 第五层：五项条件

$$
stationarity:      H u+f+G^T \lambda=0
primal feasible:   G u-h\le 0
dual feasible:     \lambda\ge 0
complementarity:   lambda_{i}*(G_{i} u-h_{i})=0
duality gap:       primal objective-dual objective=0
$$

对凸 QP 且满足约束资格条件时，这些条件既是必要条件，也是全局最优的充分条件。

### 第六层：本题手算

`u*=[0.45,0.45]`，总预算活跃。stationarity 的每一维为：

$$
2 \cdot 0.45-2+\lambda=0
\lambda=1.1
$$

primal objective 为 `-1.395`，对偶函数在 `lambda=1.1` 时也为 `-1.395`，所以对偶间隙为 0；所有不活跃边界乘子为 0，互补残差也为 0。

### 第七层：代码与边界

`compute_kkt_diagnostics` 将耦合约束和逐元素边界统一后，对活跃约束求非负乘子，并重新计算五类残差。若 Hessian 只有半正定且存在零空间，还要检查对偶线性项是否位于 Hessian 的值域；若问题非凸，KKT 成立也不保证全局最优。

## 代码映射

```python
result = minimize(
    objective, initial, jac=gradient, method="SLSQP",
    bounds=list(zip(lower, upper, strict=True)),
    constraints={"type": "ineq", "fun": lambda u: b - A @ u},
)
violation = np.concatenate([A @ u - b, lower-u, u-upper])
maximum_violation = max(0.0, np.max(violation))
```

输入包含 H、f、A、b 和边界；输出包含解、代价、success 和最大违例。H 非对称或非半正定会被拒绝，防止把非凸问题悄悄交给凸 QP 教程。

## 动手检查点

```powershell
python scripts/run_estimation_optimization_lab.py --chapter 23
python scripts/course_checkpoint.py --chapter 23
```

## 可视化证据

<!-- upkie-animation:23-evidence -->

- `outputs/plots/estimation_23.png`：目标等高线、可行域、无约束解和 QP 解；
- `outputs/logs/estimation_23.json`：解和求解器消息；
- `outputs/results/estimation_23.json`：约束残差；
- `outputs/portfolio/23/evidence.json`：作品集；
- `outputs/results/checkpoint_23.json`：自动测试。

其中 `estimation_23.json` 必须同时包含 stationarity、primal feasibility、dual feasibility、complementarity 和 duality gap 五项硬检查；缺少任一项都不能以 `solver_success` 代替。

对应的真实 result 字段名为：

kkt_stationarity_residual
kkt_primal_feasibility_residual
kkt_dual_feasibility_residual
kkt_complementarity_residual
duality_gap

## 故障诊断挑战

<!-- upkie-animation:23-comparison -->

把 `b` 改成 `-1.5`，同时保持下界 `-0.6`，问题不可行。不要把求解失败捕获后返回零动作并称为“QP 正常”；应先报告不可行约束、进入安全停机或放松策略。

再把 H 改成有负特征值的矩阵，验证输入检查为何拒绝它：非凸目标可能有多个局部最优，不再符合本章保证。

## 三档任务

- 基础任务：手算 `[0.45,0.45]`，运行两个检查点。
- 岗位挑战：加入偏航差动力矩目标，比较总预算如何分配给平衡和转向。
- 开放探索：加入动作变化率约束，比较硬 clip 和 QP 的轨迹连续性。

## 专业里程碑

你能把“不能超过”从散落的 if 语句提升为可审计约束，并用残差证据证明解可行。作品集应保留可行域图、无约束违例和一次不可行问题复盘。

## 复盘与面试

1. 为什么无约束最优解不是可执行动作？

<!-- upkie-qa:23-q1 -->
因为无约束最优解只回答了“代价函数最希望输出什么”，完全没有回答“物理世界允许输出什么”。无约束最优解的计算只用到 H 和 f（令梯度为零，解 `Hu = -f`），而轮端执行器的真实能力写在另外两处：逐轮物理限幅 lower/upper（对应 11 章模型契约中轮端力矩 `[-1,1] N*m` 的范围）和耦合约束 `Au <= b`（如两轮力矩之和受限，对应总电流或总功率预算）。只要无约束解落在可行域外，它就只是一个数学上的“愿望”：把它直接发给执行器，要么被驱动器静默截断（行为变成了你没分析过的另一个控制律），要么违反热与电流预算埋下硬件风险。本章的教学实验里，无约束解的作用恰恰是反面基准：先手算它，量化它违反了哪些约束、违反多少，再看 QP 在可行域内找到的最优解 `[0.45,0.45]` 与它差多远。两者的差距就是“约束的价格”，这个价格应该被显式计算和审计，而不是被事后 clip 悄悄吞掉。这也是本章标题“把‘不能超过’从 if 语句提升为可审计约束”的含义。
<!-- /upkie-qa -->

2. H 半正定为什么重要？

<!-- upkie-qa:23-q2 -->
H 半正定是整套“可信保证”的地基。几何上，H 半正定意味着二次目标是一只开口向上的碗（或至少没有向下弯的方向）；配合线性约束，整个问题是凸 QP。凸性带来三个工程上至关重要的性质：第一，只要可行集非空，局部最优就是全局最优——求解器报告 success 时你拿到的确实是最好的可行动作，不存在“换个初值能找到更好解”的阴影；第二，求解行为可预测，不依赖初始点选择，这对每个控制周期都要重新求解的实时控制（如 24 章 MPC 每拍解一次 QP）是前提条件；第三，KKT 条件从必要条件升级为充分条件，本章的 `compute_kkt_diagnostics` 残差检查才能作为“解确实最优”的完整证据。反过来，若 H 有负特征值，目标曲面存在马鞍或向下方向，可能有多个局部最优，SLSQP 这类局部求解器会收敛到哪个取决于初值，KKT 满足也不再保证全局最优。所以本章代码在入口处直接拒绝非对称或非半正定的 H（“防止把非凸问题悄悄交给凸 QP 教程”）：与其让错误假设混进结果，不如在输入检查就失败。另外注意半正定（而非正定）时还有零空间：最优解可能不唯一，还需检查对偶线性项是否位于 H 的值域，本章第七层对此有专门讨论。
<!-- /upkie-qa -->

3. `2e-15` 违例为何不等于真实越界？

<!-- upkie-qa:23-q3 -->
因为 `2e-15` 量级的违例来自浮点运算的舍入误差，而不是求解器真的把动作放到了可行域外。双精度浮点数的机器精度约为 `2.2e-16`，任何经过几次矩阵乘加的约束残差计算，结果都不可能精确为零，几个 ulp 的残差是浮点代数的必然产物。把它当作“越界”会导致两种错误反应：要么误报失败、把好解当坏解丢弃；要么诱使人把判定阈值调成 0，结果任何数值方法都无法通过。正确做法是设一个与问题尺度匹配的数值公差（如 1e-9 或 1e-6，相对于约束量级），小于公差计为数值零。但本章同时强调反向纪律：不能用“很小的数值违例”这个概念去掩盖 `0.01 N*m` 量级的真实安全余量侵蚀——公差的上限必须结合执行器分辨率、传感器精度和安全设计余量来定，而不是哪个数值方便就用哪个。判断标准可以这样表述：违例量级接近机器精度乘以问题条件数→数值噪声；违例量级接近物理安全余量→真越界，必须当作故障处理。这与 20 章 Joseph 形式的讨论同源：浮点误差无法消除，只能被理解、量化和管理。
<!-- /upkie-qa -->

4. QP 不可行时安全控制应做什么？

<!-- upkie-qa:23-q4 -->
第一条红线是本章反复强调的：绝不能把求解失败捕获后静默返回零动作并称“QP 正常”——零动作对倒立摆系统不是中性选择（无控制意味着倒下），而隐藏失败会让后续所有证据链失真。正确的处理分三步。第一步，显式报告：记录求解器的 success/message、哪组约束彼此矛盾（如本章动手实验：`b=-1.5` 要求两轮力矩和不超过 -1.5，与下界 -0.6 相乘后最多只能到 -1.2，可行集为空），让故障可诊断。第二步，按预先设计的降级策略行动，而不是临时发挥：可选方案包括①进入安全停机序列（降低重心、限制速度、受控停止）；②按事先定义的优先级松弛软约束（把舒适性约束加松弛变量进目标，安全硬约束永不松弛）；③回退到上一拍的可行解或预存的安全动作。哪些约束可松、松弛代价多大，必须在设计阶段写进代码审计过，不能由运行时随机决定。第三步，事后复盘：不可行通常意味着上游出了问题——参考轨迹超出能力、约束参数配置错误、或状态估计异常，本章专业里程碑要求作品集保留“一次不可行问题复盘”正是这个目的。MPC（24 章）中适用同样的铁律：不可行处理策略是控制器设计的一部分，不是异常处理的边角料。
<!-- /upkie-qa -->

5. 约束与后处理 clip 的工程差别是什么？

<!-- upkie-qa:23-q5 -->
两者都能保证“输出不超限”，但优化质量和可审计性完全不同。第一，最优性：把约束写进 QP，求解器在可行域内寻找代价最小的点，碰到边界时会沿边界滑到最优角落（本章的 `[0.45,0.45]` 就是这样得到的）；而先无约束求解再 clip，是把域外的点沿坐标轴方向硬拉回盒子边界，clip 后的点一般不是可行域内的最优点，代价可能明显更高。第二，耦合约束的正确性：逐元素 clip 只能处理盒约束，对 `Au <= b` 这样的耦合约束（两轮力矩之和受限）无能为力：逐轮都在限幅内但之和越界的动作，clip 会原样放过；而 QP 把它与盒约束统一处理。第三，可预测性与可证明性：clip 是发生在优化器视野之外的非线性环节，优化器以为输出的是 A，系统实际执行的是 clip(A)，两者的偏差没有任何理论刻画；而 QP 解附带 KKT 残差和乘子，可以事后审计“哪条约束活跃、它把代价抬高了多少”。第四，失败模式：约束矛盾时 QP 显式报告不可行，触发安全处理；clip 永远“成功”，把矛盾静默吞掉。当然 clip 并非无用：18 章的动作接口仍保留限幅作为最后一道防线（defense in depth），但它的定位是兼管异常的安全网，而不是日常承担约束职责的主力：如果日志显示最后一道 clip 经常被触发，说明上游约束建模漏了东西。
<!-- /upkie-qa -->

## 下一关

24 章将把预测模型、二次代价和输入约束沿未来时域展开成 MPC，并用滚动优化产生当前第一步动作。
