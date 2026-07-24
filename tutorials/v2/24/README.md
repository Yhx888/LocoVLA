# 24 模型预测控制（MPC）

> 建设状态：可执行
> 阶段：状态估计与优化
> 作品集目录：`outputs/portfolio/24`

## 岗位任务

在轮足机器人平衡场景中，实现模型预测控制（MPC），并与 LQR 进行定量对比。交付物：
- `outputs/results/estimation_24.json`：包含线性对照与 MuJoCo 闭环指标的验收结果
- `outputs/plots/estimation_24.png`：LQR / MPC / 受限 MPC 三行对比图
- `outputs/logs/estimation_24.log`：QP 求解统计日志
- `outputs/portfolio/24/mpc_vs_lqr_report.md`：对照报告
- `outputs/results/trajectory_24.json`：直接配点与单次打靶的同题验收结果

风险：如果 MPC 在硬约束下找不到可行解，控制器必须抛出 `MPCSolveError` 并进入上层安全处理；本实现禁止静默丢弃状态约束后返回无约束解。

## 学习目标

- **能理解**：用自己的话说明 MPC 和 LQR 的核心区别——MPC 能显式处理约束，LQR 不能。
- **能推导**：从 QP（二次规划）的目标函数和约束出发，手算 2 步预测的最优控制。
- **能实现**：运行对比脚本，解释每条曲线的物理含义和指标差异。

## 前置关卡

完成 `23`（二次规划、KKT 与对偶）的证据验收，或通过先修诊断。LQR 状态反馈与 DARE 来自 `16-17`，本章在此基础上加入有限时域和硬约束。

## 先观察现象

在运行任何代码之前，先思考一个场景：

> Upkie 正在平衡，突然有人推了它一下。LQR 会算出一个很大的力矩试图恢复平衡，但电机有物理上限（比如 ±1 N*m）。如果 LQR 算出的力矩超出上限，实际控制量会被截断（clip），导致控制效果偏离最优。

**问题**：有没有一种控制器，在计算力矩的时候就知道电机有上限，从而提前规划好力矩分配，避免"算出来用不了"？

这就是 MPC 要解决的核心问题。

## 直觉与概念

<!-- upkie-animation:24-intuition -->

**MPC 就像下棋时往前多想几步。**

下象棋时，你不会只看当前局面就走棋。你会想："如果我走这步，对手可能走那步，然后我再走……"——你在脑中模拟未来几步的局势，选择让局势最好的当前走法。

MPC 做的完全一样：
1. **预测**：从当前状态出发，用动力学模型模拟未来 N 步（预测时域）
2. **优化**：在这 N 步中，找一组控制量使得"状态误差小 + 控制量省"的总代价最低
3. **执行**：只执行第一步的控制量（剩余丢弃，下一步重新算）
4. **滚动**：到了下一步，用新测量值重新开始——这就是"滚动时域"（receding horizon）

**LQR 的局限**：LQR 也有最优控制，但它假设控制量可以任意大。如果 LQR 算出力矩 5 N*m，但电机只能输出 1 N*m，实际效果就不最优了。MPC 把"电机只能输出 ±1 N*m"作为约束写进优化问题里，从根本上解决这个问题。

**映射到 Upkie**：Upkie 的轮端电机力矩范围是 ±1.0 N*m。当俯仰偏差较大时（如被推了一下），LQR 可能算出 ±3 N*m 的力矩。如果直接 clip 到 ±1 N*m，控制效果就不最优。MPC 在优化时就知道这个限制，提前规划好力矩序列。

## 教科书级展开

<!-- upkie-animation:24-parameter -->

### 第一层：核心公式

MPC 在每个控制周期求解的优化问题：

```
minimize    J = sum_{k=0}^{N-1} [ e_k^T Q e_k + u_k^T R u_k ] + e_N^T Q_f e_N
u_0,...,u_{N-1}

subject to  x_{k+1} = A x_k + B u_k,    k = 0, 1, ..., N-1
            x_0 = x_current
            u_min <= u_k <= u_max,        k = 0, 1, ..., N-1
```

假设与平衡点：线性化在直立平衡点（pitch=0, pitch_rate=0, x=0, x_dot=0）附近，离散时间步长 dt=0.02 s。

### 第二层：符号拆解

| 符号 | 含义 | SI 单位 | 本关取值 |
|------|------|---------|----------|
| N | 预测时域（向前看几步） | 无量纲（步数） | 20 |
| x_k | 第 k 步的状态向量 | 混合 | [pitch(rad), pitch_rate(rad/s), x(m), x_dot(m/s)] |
| u_k | 第 k 步的控制量 | N*m | wheel_torque, 范围 [-1.0, 1.0] |
| e_k | 状态误差 = x_k - x_ref | 同 x_k | x_ref = [0,0,0,0]（保持直立原地） |
| A | 状态转移矩阵（离散） | 无量纲 | 4x4，由连续模型欧拉离散化得到 |
| B | 输入矩阵（离散） | 混合 | 4x1 |
| Q | 状态代价权重矩阵 | 混合 | diag(200, 5, 5, 5)，俯仰误差权重最大 |
| R | 控制代价权重矩阵 | 混合 | [[10]]，适中惩罚 |
| Q_f | 终端代价矩阵 | 同 Q | 默认等于 Q |
| dt | 采样周期 | s | 0.02 |

> **注意**：本关状态顺序为 `[pitch, pitch_rate, x, x_dot]`，与 Ch16/Ch17 的 `[x, x_dot, pitch, pitch_dot]` 不同，对应不同的物理参数（m=5.4, L=0.28, r=0.06）和阻尼项。做跨章对比时需先做状态置换。

直觉解读各项：
- `e_k^T Q e_k`：状态误差的"罚款"。Q 的对角线元素越大，对应状态的误差越"贵"。Q[0,0]=200 说明俯仰误差的代价是位置误差的 40 倍——机器人优先保持直立。
- `u_k^T R u_k`：控制量的"电费"。R=10 惩罚大力矩，避免电机过载。
- `e_N^T Q_f e_N`：终端"罚款"。确保预测终点状态也不要偏离太远。

### 第三层：物理意义

以 Upkie 被推了一下（pitch = 0.05 rad）为例：

1. LQR 会立即算出 u = -K * [0.05, 0, 0, 0]^T。如果 K 很大（因为俯仰权重高），u 可能算出 -3 N*m，但电机只能给 -1 N*m。
2. MPC 会"想"：未来 20 步（0.4 秒），每步最多用 1 N*m。它发现第 1 步用满 -1 N*m 可以快速减小俯仰，但后续需要反向力矩来避免过冲。于是 MPC 规划出一个"先全力、后收力"的力矩序列。

关键物理洞察：MPC 的力矩曲线比 LQR 更"平滑"，因为它提前知道约束的存在，不会先算出超大力矩再截断。

### 第四层：设计动机——为什么把约束写进优化而不是事后截断

| 方面 | LQR + clip | MPC（带约束） |
|------|------------|---------------|
| 计算方式 | 先算无约束最优，再截断 | 把约束作为优化条件 |
| 最优性 | 截断后不最优 | 约束下最优 |
| 稳定性保证 | 截断可能破坏稳定性 | 有理论保证（需终端约束/代价） |
| 计算量 | 低（一次矩阵乘法） | 较高（每步求解 QP） |
| 适用场景 | 控制量不经常饱和 | 控制量频繁饱和 |

### 第五层：逐步推导

**5.1 离散动力学模型**

连续时间线性倒立摆模型（详见 `upkie_balance_ss_matrices`）：

```
theta_ddot = (g/L) * theta - tau / (m*L*r)
x_ddot = -g * theta + tau / (m*r)
```

其中 g=9.81 m/s^2, L=0.28 m, m=5.4 kg, r=0.06 m。

> **源码中的隐性阻尼项**：如果你打开 `mpc.py` 查看 `upkie_balance_ss_matrices` 函数，会发现连续矩阵 A_c 并不是纯粹的无阻尼倒立摆。具体来说，A_c 的 `[1,1]`（角速度行）和 `[3,3]`（线速度行）各有一个 `-0.05` 的对角项：
>
> ```
> A_c = [[0,     1,    0,  0   ],
>         [g/L, -0.05, 0,  0   ],
>         [0,     0,    0,  1   ],
>         [-g,    0,    0, -0.05]]
> ```
>
> 上面的简化公式省略了这两项。加上它们的原因是纯数学的：无阻尼时，离散化矩阵 A_d 的某些极点恰好落在单位圆上（模 = 1），导致 DARE（离散代数 Riccati 方程）求解时数值不稳定。物理上，-0.05 可以理解为等效粘性摩擦——它远小于 g/L ≈ 35，不影响倒立摆的失稳趋势，但足以让 `(A, B)` 对在数值计算中保持良好条件。

用一阶欧拉离散化（dt=0.02 s）：

```
A_d = I + dt * A_c
B_d = dt * B_c
```

**5.2 把 QP 写成标准形式**

将预测时域内的所有控制量拼成一个大向量：

```
U = [u_0, u_1, ..., u_{N-1}]^T    (N x 1 向量)
```

将动力学代入目标函数，J 可以写成关于 U 的二次函数：

```
J(U) = (1/2) U^T H U + f^T U + const
```

其中 H 是正定矩阵（由 A, B, Q, R 组合而成），f 是与初始状态相关的向量。约束变为 `u_min <= u_k <= u_max`。这就是标准的有界二次规划（Box-constrained QP）。

**5.3 求解方法——解析梯度（adjoint method）**

为了精确收敛，不用 scipy 默认的数值差分梯度，而是自己推导解析梯度：

1. **前向**：展开轨迹 x_0, x_1, ..., x_N
2. **后向**：从终端递推代价梯度
   - lambda_N = 2 Q_f e_N
   - lambda_k = 2 Q e_k + A^T lambda_{k+1}
3. **梯度**：dJ/du_j = 2 R u_j + B^T lambda_{j+1}

这比数值差分精度高约 8 个数量级，是 MPC 与 LQR 数值对齐的关键。

**5.4 MPC 退化到 LQR 的条件**

当满足以下三个条件时，MPC 的首步控制等于 LQR 控制：
1. **无约束**：控制限幅足够大，不构成有效约束
2. **长时域**：N 足够大（或 N -> 无穷）
3. **终端代价 = DARE 解**：Q_f = P，其中 P 满足离散代数 Riccati 方程

此时有限时域问题等价于无限时域问题，MPC 首步 = LQR 最优控制。

适用范围：本关的线性化模型仅在直立平衡点附近有效（pitch < 0.3 rad）。接触丢失、传感器过期或输入超出训练分布时，必须进入诊断/安全路径。

### 第六层：手算 2 步算例

为能手算，用一维标量系统：

```
a = 1.1,  b = 1.0,  q = 1.0,  r = 0.1
x_0 = 1.0,  x_ref = 0,  N = 2,  u_max = 0.5
```

目标：minimize J = q*x_0^2 + r*u_0^2 + q*x_1^2 + r*u_1^2 + q*x_2^2

步骤 1：写出预测状态
- x_1 = a*x_0 + b*u_0 = 1.1 + u_0
- x_2 = a*x_1 + b*u_1 = 1.21 + 1.1*u_0 + u_1

步骤 2：写出目标函数并展开
```
J = 1.0 + 0.1*u_0^2 + (1.21 + 2.2*u_0 + u_0^2) + 0.1*u_1^2 + (1.4641 + 2.662*u_0 + 2.42*u_1 + 1.21*u_0^2 + 2.2*u_0*u_1 + u_1^2)
  = 2.31*u_0^2 + 1.1*u_1^2 + 2.2*u_0*u_1 + 4.862*u_0 + 2.42*u_1 + 3.6741
```

步骤 3：无约束最优（对 u_0, u_1 求偏导 = 0）
```
dJ/du_0 = 4.62*u_0 + 2.2*u_1 + 4.862 = 0
dJ/du_1 = 2.2*u_1 + 2.2*u_0 + 2.42 = 0
```

从第二式：u_1 = -u_0 - 1.1。代入第一式：
```
4.62*u_0 + 2.2*(-u_0 - 1.1) + 4.862 = 0
2.42*u_0 + 2.442 = 0
u_0 = -1.009
```

但 u_max = 0.5，所以无约束最优被截断。

步骤 4：有约束最优。设 u_0 = -0.5（在下界），求 u_1 的最优：
```
2.2*u_1 + 2.2*(-0.5) + 2.42 = 0  →  u_1 = -0.6
```

u_1 = -0.6 < -0.5 也越界，设 u_1 = -0.5。

结果：MPC 输出 u_0 = -0.5（约束饱和）。这个简单例子中 LQR+clip 也得到 -0.5，但在多步、多状态的真实场景中，MPC 的"提前规划"优势就体现出来——它会为后续步骤保留力矩余量，而不是每一步都贪心用满。

### 第七层：代码映射

核心代码结构：

```
src/upkie_mujoco_course/controllers/mpc.py
+-- class LinearMPC
|   +-- __init__()                           # 存储 A, B, Q, R, Qf, horizon, limit
|   +-- _predict_states()                    # 前向展开轨迹
|   +-- _compute_objective_and_gradient()    # 目标函数 + 伴随法梯度
|   +-- compute()                            # 调用 scipy minimize 求解 QP
+-- upkie_balance_ss_matrices()              # 构造 4 状态离散 A, B
```

关键代码 1——前向预测（`_predict_states`）：

```python
for index, control in enumerate(controls):
    current = self.a @ current + self.b @ control  # x_{k+1} = A x_k + B u_k
    trajectory[index + 1] = current
```

关键代码 2——伴随法梯度（`_compute_objective_and_gradient`）：

```python
lam = 2.0 * self.qf @ terminal_error  # lambda_N = 2 Qf e_N
for j in range(self.horizon - 1, -1, -1):
    grad[j] = 2.0 * self.r @ controls[j] + self.b.T @ lam  # dJ/du_j
    lam = 2.0 * self.q @ error_j + self.a.T @ lam           # lambda_k 递推
```

关键代码 3——QP 求解（`compute`）：

```python
result = minimize(
    objective_and_gradient,  # 同时返回函数值和梯度
    initial, method="L-BFGS-B", jac=True, bounds=bounds,
)
control = result.x[:input_size]  # 只取第一步控制量（滚动时域）
```

`jac=True` 是关键：告诉 scipy 函数返回 `(f, grad)` 元组，避免数值差分近似梯度。

与 LQR 的接口对齐：MPC 和 LQR 共享 `compute(state, reference)` 接口，对比脚本可复用同一仿真循环。

## 轨迹优化：直接配点与单次打靶同题比较

### 第一层：直觉

直接配点像同时摆放整条路上的路标，再检查相邻路标是否符合动力学；单次打靶像只选择一串控制“发射角”，每次从起点完整前向积分，看终点是否命中。公平比较必须使用同一动力学、网格、边界和代价。

### 第二层：符号与单位

共享问题为双积分器：

$$
p_{\text{dot}}=v, v_{\text{dot}}=u
[p(0),v(0)]=[0 m,0 \frac{m}{s}]
[p(T),v(T)]=[1 m,0 \frac{m}{s}]
T=1 s, N=20, dt=0.05 s
|u_{k}|\le 10 \frac{m}{s}^2
J=dt*[0.5 \cdot u_{0}^2+sum_{k=1}^{N-1}u_{k}^2+0.5 \cdot u_{N}^2]
$$

`p` 是位置 m，`v` 是速度 m/s，`u` 是加速度 m/s^2。该平方代价用于同题比较，不直接解释为电能。

### 第三层：物理意义

轨迹必须先加速再减速，才能在 1 秒内前进 1 m 且末速度回到 0。控制平方代价避免不必要的尖峰；终端位置和速度是硬约束，不允许用较低代价换取漏靶。

### 第四层：为什么比较两种参数化

- 直接配点决策变量多，但能直接检查每一段动力学缺陷，适合长时域和路径约束；
- 单次打靶变量少，但每次迭代都要从头积分，系统不稳定或时域很长时对初值敏感。

这里不证明某方法永远更好，而是验证两种参数化在同一凸离散问题上得到相同代价。

### 第五层：不跳步离散与约束

在每个节点放置状态和控制，用梯形配点离散为：

$$
p_{k+1}-p_{k}=0.5 \cdot dt \cdot (v_{k}+v_{k+1})
v_{k+1}-v_{k}=0.5 \cdot dt \cdot (u_{k}+u_{k+1})
$$

直接配点优化：

$$
z=[p_{0},v_{0},\dots,p_{N},v_{N},u_{0},\dots,u_{N}]
$$

并把初值、每段梯形动力学缺陷和终值全部设为等式约束。单次打靶只优化 `U=[u_0,...,u_N]`，用同一梯形离散从初态前向展开，再约束最终 `[p_N,v_N]=[1,0]`。

### 第六层：数值复核

运行实验后从轨迹优化 result 读取本机本次指标：

```python
import json
from pathlib import Path

result = json.loads(Path("outputs/results/trajectory_24.json").read_text(encoding="utf-8"))
metrics = result["metrics"]
for name, value in metrics.items():
    print(f"{name}: {value:.6f}")

assert metrics["direct_collocation_terminal_error"] <= 1e-7
assert metrics["shooting_terminal_error"] <= 1e-7
assert metrics["direct_collocation_dynamic_defect"] <= 1e-8
assert metrics["shooting_dynamic_defect"] <= 1e-12
assert metrics["trajectory_cost_gap"] <= 1e-5
```

连续时间解析最小代价接近 12；离散结果略高来自有限网格。若只比较终端误差而不比较动力学缺陷，伪造的节点轨迹也可能“命中”终点。

### 第七层：代码映射、命令与边界

核心实现位于 `controllers/trajectory_optimization.py`：`solve_direct_collocation` 同时优化节点和控制，`solve_single_shooting` 只优化控制并调用同一个前向积分器。

```powershell
python scripts/run_trajectory_optimization_lab.py
```

该算例假设线性、光滑、固定时域且没有接触切换。对 Upkie 起立、跳跃或轮地接触切换问题，需要多阶段动力学、接触互补约束和稀疏 NLP 求解器，不能把本算例的收敛性直接外推。

## 动手检查点

```powershell
python scripts/run_mpc_balance_compare.py
python scripts/run_trajectory_optimization_lab.py
python scripts/course_checkpoint.py --chapter 24
```

预期结果：
- 终端打印 JSON 格式的指标（含 mpc_pitch_rmse、max_torque、settling_time、constraint_hit_rate、solve_time_ms）
- 生成 `outputs/plots/estimation_24.png`（三行子图）
- 生成 `outputs/results/estimation_24.json`（passed = true）
- 生成 `outputs/logs/estimation_24.log`
- 生成 `outputs/portfolio/24/mpc_vs_lqr_report.md`
- 生成 `outputs/results/trajectory_24.json`、`outputs/logs/trajectory_24.json` 和 `outputs/plots/trajectory_24.png`

关键指标解读：

| 指标 | 含义 | 期望值 |
|------|------|--------|
| mpc_over_lqr_rmse_ratio | MPC/LQR 俯仰 RMSE 比值 | <= 1.2 |
| constrained_mpc_torque_within_limit | 受限 MPC 力矩是否超限 | == 1.0 |
| constraint_hit_rate | 受限 MPC 触碰约束边界的比例 | >= 0.5% |
| solve_time_ms_mean | MPC 平均求解时间 | <= 200 ms |
| mujoco_solve_success_ratio | MuJoCo 闭环求解成功比例 | == 1.0 |
| mujoco_prediction_constraints_satisfied | 预测状态硬约束是否满足 | == 1.0 |
| mujoco_actual_constraints_satisfied | 实际闭环状态是否满足约束 | == 1.0 |
| mujoco_steps_executed | 真实 MuJoCo 闭环步数 | >= 100 |

失败诊断：
- 如果 `constraint_hit_rate` = 0：说明扰动太小或约束太松，约束没有真正起作用
- 如果 `mpc_over_lqr_rmse_ratio` > 1.2：说明 MPC 求解器没有收敛，检查 `solve_time_ms` 是否超时
- 如果预测约束不满足：不得退回无约束解，检查 `MPCSolveError` 和 `prediction_max_violation`
- 如果 `passed` = false：查看 `checks` 字段中哪一项为 false

显式不可行路径由下面的回归测试锁定：

```powershell
python -m pytest tests/test_mpc.py::test_mpc_rejects_infeasible_state_constraint_without_unconstrained_fallback -q
```

该测试要求硬约束不可行时抛出 `MPCSolveError`，禁止静默 fallback 到无状态约束解。

## 可视化证据

<!-- upkie-animation:24-evidence -->

运行后检查 `outputs/plots/estimation_24.png`：

- **第一行（俯仰角）**：三条曲线应从初始扰动收敛到零。LQR（蓝）和 MPC（绿）几乎重合；受限 MPC（橙）可能收敛稍慢，但俯仰不超出 ±0.20 rad 灰色虚线。
- **第二行（力矩）**：LQR 力矩可能超出 ±0.35 N*m 橙色虚线；受限 MPC 严格在虚线内。这就是约束的作用。
- **第三行（位置/速度）**：受限 MPC 的位置和速度轨迹，用于观察侧向漂移。

视觉只回答"发生了什么"，日志给出时间与数值，测试负责可重复判定；三者缺一不可。

再检查 `outputs/plots/trajectory_24.png`：位置、速度和控制曲线中，直接配点与单次打靶应基本重合；右下角的终端误差、动力学缺陷和代价差必须全部低于 result 中的硬阈值。

## 故障诊断挑战

<!-- upkie-animation:24-comparison -->

**挑战：关掉解析梯度**

在 `mpc.py` 的 `compute` 方法中，把 `jac=True` 改为 `jac=False`（或删掉），观察：
1. MPC 与 LQR 的 RMSE 比值会显著增大
2. 求解时间可能变长（scipy 需要更多迭代）
3. 某些极端状态下 MPC 可能求解失败

按"现象 -> 第一处异常证据 -> 根因假设 -> 最小验证 -> 修复后对比"记录，不允许通过放宽阈值隐藏失败。

**求解器消息处理**：不得用 `warnings.filterwarnings("ignore")` 掩盖求解异常。先检查 `last_solve_stats.success`、`message`、`prediction_max_violation` 和 result 中的 checks；求解失败或预测硬约束违反都应明确失败。

## 三档任务

- **基础任务**：运行 `run_mpc_balance_compare.py`，解释 `estimation_24.json` 中每个字段。说明为什么 `mpc_over_lqr_rmse_ratio` 接近 1 但不等于 1（因为有限时域与无限时域的差异）。
- **岗位挑战**：修改扰动参数（`disturbance[10, 0] = 0.15`，更大的俯仰扰动），报告 LQR 力矩饱和比例、MPC 约束命中率和 settling time 的变化。
- **开放探索**：尝试把预测时域从 20 改为 5 和 50，先写假设（时域越长越接近 LQR、求解时间线性增长），再用同一评估协议公平比较。

## 复盘与面试

1. **本关最关键的假设是什么？** 动力学模型准确。如果 A、B 矩阵与真实系统偏差大，MPC 的预测就不准，优化结果也不可靠。失效时第一个可观测信号：仿真中 MPC 表现好但实机上变差。
2. **为什么当前接口、单位和限幅这样设计？** `compute(state, reference)` 与 LQR 接口一致，方便对比脚本复用。control_limit 对应物理电机的力矩上限（Upkie 轮端 ±1.0 N*m）。替代方案：可以用 CVXPY 等凸优化库替代 scipy，获得更好的 QP 求解性能。
3. **你能用哪三份证据证明结果可复现？** (a) estimation_24.json 中的 seed=0；(b) estimation_24.log 中的求解统计；(c) test_mpc.py 中的自动化测试。
4. **如果指标退化 20%，你先查模型、数据、控制还是部署？** 先查模型（A, B 矩阵是否与仿真对齐），再查控制（约束设置是否与实际电机一致）。数据和部署在这一步不涉及。

## 下一关

下一关 `25` 将把当前控制与仿真接口封装成 Gymnasium 环境，明确 observation/action shape、seed、终止与截断语义，为强化学习训练建立可复现契约。
