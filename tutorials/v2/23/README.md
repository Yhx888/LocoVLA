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
2. H 半正定为什么重要？
3. `2e-15` 违例为何不等于真实越界？
4. QP 不可行时安全控制应做什么？
5. 约束与后处理 clip 的工程差别是什么？

## 下一关

24 章将把预测模型、二次代价和输入约束沿未来时域展开成 MPC，并用滚动优化产生当前第一步动作。
