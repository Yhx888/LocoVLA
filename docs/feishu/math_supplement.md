# 数学知识详解（零基础版）

> 📗 **难度**：★★☆☆☆（基础）— 高中数学水平即可阅读
> **用途**：本教材的数学参考资料。遇到教程中跳过的推导步骤，可以来这里查。
> **链接到**：所有教程章节的公式推导都会链接本文档对应节。

---

## 一、线性代数基础

### 1.1 什么是矩阵？

#### 💡 直觉理解

矩阵就是一个**数字表格**。就像 Excel 表格有行有列，矩阵也有行（row）和列（column）。

在机器人学中，矩阵用来表示：
- 坐标变换（旋转、平移）
- 数据的批量处理
- 多变量系统的描述

#### 符号拆解

一个 $m \times n$ 矩阵有 $m$ 行 $n$ 列：

$$A = \begin{bmatrix} a_{11} & a_{12} & a_{13} \\ a_{21} & a_{22} & a_{23} \end{bmatrix}$$

| 符号 | 含义 | 类比 |
|------|------|------|
| $m$ | 行数 | Excel 中的行数 |
| $n$ | 列数 | Excel 中的列数 |
| $a_{ij}$ | 第 $i$ 行第 $j$ 列的元素 | 表格中的某个格子 |
| $m \times n$ | 矩阵的形状 | 说"这是一个 2×3 的矩阵" |

#### 特殊矩阵

| 类型 | 定义 | 2×2 示例 |
|------|------|----------|
| **方阵**（square matrix） | 行数 = 列数 | $\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix}$ |
| **单位矩阵**（identity matrix）$I$ | 对角线为 1，其余为 0 | $\begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$ |
| **对角矩阵**（diagonal matrix） | 只有对角线非零 | $\begin{bmatrix} a & 0 \\ 0 & b \end{bmatrix}$ |
| **对称矩阵**（symmetric matrix） | $A = A^T$ | $\begin{bmatrix} 1 & 2 \\ 2 & 3 \end{bmatrix}$ |
| **转置矩阵**（transpose）$A^T$ | 行列互换 | $\begin{bmatrix} 1 & 3 \\ 2 & 4 \end{bmatrix}^T = \begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix}$ |

#### 为什么需要矩阵？—— 课程关联

在 **Lesson 04（LQR 控制）** 中，系统状态 $\mathbf{x}$ 是一个 6×1 向量（列矩阵），系统矩阵 $A$ 是一个 6×6 方阵。LQR 的核心计算就是矩阵乘法 $K = R^{-1}B^T P$。

---

### 1.2 矩阵的基本运算

#### 矩阵加法

两个**形状相同**的矩阵对应元素相加：

$$\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} + \begin{bmatrix} 5 & 6 \\ 7 & 8 \end{bmatrix} = \begin{bmatrix} 6 & 8 \\ 10 & 12 \end{bmatrix}$$

#### 矩阵乘法

> ⚠️ **矩阵乘法不满足交换律**！$A \times B \neq B \times A$（绝大多数情况）

**规则**：$A$ 的第 $i$ 行与 $B$ 的第 $j$ 列对应元素相乘后求和：

$$C_{ij} = \sum_{k=1}^{n} A_{ik} \cdot B_{kj}$$

**数值算例**：

$$\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} \times \begin{bmatrix} 5 & 6 \\ 7 & 8 \end{bmatrix} = \begin{bmatrix} 1\times5+2\times7 & 1\times6+2\times8 \\ 3\times5+4\times7 & 3\times6+4\times8 \end{bmatrix} = \begin{bmatrix} 19 & 22 \\ 43 & 50 \end{bmatrix}$$

**物理意义**：矩阵乘法表示**变换的组合**。如果 $A$ 表示旋转，$B$ 表示平移，那么 $A \times B$ 表示先平移再旋转。

#### 矩阵的逆

矩阵 $A$ 的逆 $A^{-1}$ 满足：$A \times A^{-1} = A^{-1} \times A = I$

只有方阵才可能有逆矩阵，且行列式不为 0。

**2×2 矩阵的逆公式**：

对于 $A = \begin{bmatrix} a & b \\ c & d \end{bmatrix}$：

$$A^{-1} = \frac{1}{ad-bc} \begin{bmatrix} d & -b \\ -c & a \end{bmatrix}$$

其中 $ad-bc$ 是**行列式**（determinant），必须不为 0。

**数值算例**：

$$A = \begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix}, \quad \det(A) = 1\times4 - 2\times3 = -2$$

$$A^{-1} = \frac{1}{-2} \begin{bmatrix} 4 & -2 \\ -3 & 1 \end{bmatrix} = \begin{bmatrix} -2 & 1 \\ 1.5 & -0.5 \end{bmatrix}$$

验证：$A \times A^{-1} = \begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} \begin{bmatrix} -2 & 1 \\ 1.5 & -0.5 \end{bmatrix} = \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix} = I \quad$ ✅

> **课程关联**：LQR 的增益计算 $K = R^{-1}B^T P$ 中涉及矩阵求逆 $R^{-1}$。

---

### 1.3 二次型

#### 💡 直觉理解

**二次型**（quadratic form）是"一个向量经过一个矩阵变换后，再与自身做点积"。它的结果是一个**标量**（单个数字）。

**公式**：

$$Q(\mathbf{x}) = \mathbf{x}^T A \mathbf{x}$$

其中 $\mathbf{x}$ 是 $n$ 维向量，$A$ 是 $n \times n$ 矩阵。

**数值算例**：

$$\mathbf{x} = \begin{bmatrix} x_1 \\ x_2 \end{bmatrix}, \quad A = \begin{bmatrix} a & b \\ c & d \end{bmatrix}$$

$$\mathbf{x}^T A \mathbf{x} = [x_1 \; x_2] \begin{bmatrix} a & b \\ c & d \end{bmatrix} \begin{bmatrix} x_1 \\ x_2 \end{bmatrix} = a x_1^2 + (b+c)x_1x_2 + d x_2^2$$

**数值代入**：$\mathbf{x} = \begin{bmatrix} 2 \\ 1 \end{bmatrix}, \; A = \begin{bmatrix} 1 & 2 \\ 2 & 4 \end{bmatrix}$

$$\mathbf{x}^T A \mathbf{x} = 1\times2^2 + (2+2)\times2\times1 + 4\times1^2 = 4 + 8 + 4 = 16$$

#### 为什么需要二次型？

**半正定矩阵**（positive semidefinite matrix）：对所有 $\mathbf{x} \neq 0$，满足 $\mathbf{x}^T A \mathbf{x} \geq 0$。

> **课程关联**：在 **Lesson 04（LQR）** 中，代价函数 $J = \int (\mathbf{x}^T Q \mathbf{x} + \mathbf{u}^T R \mathbf{u}) dt$ 就是两个二次型的积分。$Q$ 必须是半正定矩阵，$R$ 必须是正定矩阵，这样才能保证代价函数有最小值。

---

### 1.4 特征值与特征向量

#### 💡 直觉理解

**特征向量**（eigenvector）是一个向量，它经过矩阵变换后**方向不变**（只缩放）。**特征值**（eigenvalue）就是这个缩放倍数。

$$A \mathbf{v} = \lambda \mathbf{v}$$

其中 $\mathbf{v}$ 是特征向量，$\lambda$ 是特征值。

#### 数值算例

$$A = \begin{bmatrix} 4 & 1 \\ 2 & 3 \end{bmatrix}$$

**求解特征值**：解 $\det(A - \lambda I) = 0$

$$\det\begin{bmatrix} 4-\lambda & 1 \\ 2 & 3-\lambda \end{bmatrix} = (4-\lambda)(3-\lambda) - 2 = \lambda^2 - 7\lambda + 10 = 0$$

解得 $\lambda_1 = 5, \lambda_2 = 2$

**验证**：$\lambda_1 = 5$ 代入 $A\mathbf{v} = 5\mathbf{v}$，求得 $\mathbf{v}_1 = \begin{bmatrix} 1 \\ 1 \end{bmatrix}$

$$A\mathbf{v}_1 = \begin{bmatrix} 4 & 1 \\ 2 & 3 \end{bmatrix} \begin{bmatrix} 1 \\ 1 \end{bmatrix} = \begin{bmatrix} 5 \\ 5 \end{bmatrix} = 5\begin{bmatrix} 1 \\ 1 \end{bmatrix}$$

> **课程关联**：在 **Lesson 04（LQR）** 中，求解 Riccati 方程得到的 $P$ 矩阵必须是**正定**的（所有特征值 > 0）。在 **Lesson 03（PD 控制）** 中，特征方程的根决定了系统稳定性（所有根的实部 < 0 则稳定）。

---

## 二、微积分基础

### 2.1 导数

#### 💡 直觉理解

**导数**（derivative）描述一个量随另一个量变化的**快慢**。位置的变化率是速度，速度的变化率是加速度。

#### 基本导数公式

| 函数 $f(x)$ | 导数 $f'(x)$ | 说明 |
|------------|-------------|------|
| $c$（常数） | $0$ | 常数不变 |
| $x^n$ | $n x^{n-1}$ | 幂函数 |
| $e^x$ | $e^x$ | 指数函数自身 |
| $\sin x$ | $\cos x$ | 正弦变余弦 |
| $\cos x$ | $-\sin x$ | 余弦变负正弦 |
| $\ln x$ | $1/x$ | 自然对数 |

#### 求导法则

**链式法则**（chain rule）：$f(g(x))$ 的导数为 $f'(g(x)) \cdot g'(x)$

**数值算例**：$f(x) = \sin(x^2)$，求 $f'(x)$

设 $g(x) = x^2$，则 $f(g) = \sin(g)$：
$$f'(x) = \cos(g(x)) \cdot g'(x) = \cos(x^2) \cdot 2x$$

#### 偏导数

当一个函数有多个变量时，对其中一个求导就是偏导数。

$$f(x, y) = x^2 + 3xy + y^2$$
$$\frac{\partial f}{\partial x} = 2x + 3y, \quad \frac{\partial f}{\partial y} = 3x + 2y$$

> **课程关联**：在 **Lesson 04（LQR）** 的 Riccati 推导中，对 $\mathbf{u}$ 求偏导 $\frac{\partial}{\partial \mathbf{u}}(\mathbf{u}^T R \mathbf{u})$ 得到 $2R\mathbf{u}$。在 **Lesson 06（PPO）** 的策略梯度中，对 $\theta$ 求导 $\nabla_\theta \log \pi_\theta(a|s)$。

---

### 2.2 向量与矩阵的导数

#### 💡 直觉理解

函数输入是向量、输出是标量时，导数是一个向量（梯度）。

**常见形式**：

$$\frac{\partial}{\partial \mathbf{x}}(\mathbf{x}^T A \mathbf{x}) = (A + A^T) \mathbf{x}$$

如果 $A$ 是对称矩阵（$A = A^T$），则：

$$\frac{\partial}{\partial \mathbf{x}}(\mathbf{x}^T A \mathbf{x}) = 2A\mathbf{x}$$

$$\frac{\partial}{\partial \mathbf{x}}(\mathbf{b}^T \mathbf{x}) = \mathbf{b}$$

$$\frac{\partial}{\partial \mathbf{x}}(\mathbf{x}^T \mathbf{b}) = \mathbf{b}$$

#### 为什么需要这个？—— 课程关联

在 **Lesson 04（LQR）** 中，最优控制的求解需要解：

$$\frac{\partial}{\partial \mathbf{u}}(\mathbf{u}^T R \mathbf{u} + 2\mathbf{x}^T P B \mathbf{u}) = 0$$

用上述公式：$\frac{\partial}{\partial \mathbf{u}}(\mathbf{u}^T R \mathbf{u}) = 2R\mathbf{u}$（因为 $R$ 对称），$\frac{\partial}{\partial \mathbf{u}}(2\mathbf{x}^T P B \mathbf{u}) = 2B^T P \mathbf{x}$。

---

### 2.3 数值积分

#### 💡 直觉理解

**数值积分**用离散的求和来近似连续的积分。在计算机中，我们无法做连续的积分，只能用离散的时间步长来累加。

**常用方法**：

**欧拉法**（Euler method）：

$$\int_0^T f(t) dt \approx \sum_{k=0}^{N-1} f(t_k) \cdot \Delta t$$

其中 $\Delta t = T/N$ 是步长，$t_k = k \cdot \Delta t$。

**数值算例**：用欧拉法近似 $f(t) = t^2$ 在 $[0, 1]$ 上的积分（$\Delta t = 0.25$）

| $k$ | $t_k$ | $f(t_k)$ | 矩形面积 |
|-----|-------|----------|---------|
| 0 | 0.00 | 0.00 | 0.00 |
| 1 | 0.25 | 0.0625 | 0.0156 |
| 2 | 0.50 | 0.25 | 0.0625 |
| 3 | 0.75 | 0.5625 | 0.1406 |

**近似值**：$0 + 0.0156 + 0.0625 + 0.1406 = 0.2188$

**精确值**：$\int_0^1 t^2 dt = \frac{1}{3} \approx 0.3333$

**误差**：34%（步长越小，误差越小）

> **课程关联**：在 **Lesson 02（MuJoCo 基础）** 中，MuJoCo 的仿真步进就是数值积分——在每个时间步 $\Delta t$ 内计算动力学方程，更新状态。

---

## 三、线性系统

### 3.1 状态空间表示

#### 💡 直觉理解

**状态空间表示**（state-space representation）用一组一阶微分方程来描述系统。想象你在驾驶一辆车——车的**状态**是位置和速度，**控制**是油门和刹车，这就是一个最简单的状态空间系统。

**标准形式**：

$$\dot{\mathbf{x}} = A\mathbf{x} + B\mathbf{u}$$

| 符号 | 含义 | 维度 | 类比 |
|------|------|------|------|
| $\mathbf{x}$ | 状态向量 | $n \times 1$ | 汽车的位置+速度 |
| $\dot{\mathbf{x}}$ | 状态变化率 | $n \times 1$ | 速度+加速度 |
| $\mathbf{u}$ | 控制输入 | $m \times 1$ | 油门大小 |
| $A$ | 系统矩阵 | $n \times n$ | 车的物理特性 |
| $B$ | 输入矩阵 | $n \times m$ | 油门如何影响状态 |

**数值算例：简谐振动**

$$\ddot{x} = -\omega^2 x$$

设状态 $\mathbf{x} = \begin{bmatrix} x \\ \dot{x} \end{bmatrix}$，则：

$$\dot{\mathbf{x}} = \begin{bmatrix} \dot{x} \\ -\omega^2 x \end{bmatrix} = \begin{bmatrix} 0 & 1 \\ -\omega^2 & 0 \end{bmatrix} \begin{bmatrix} x \\ \dot{x} \end{bmatrix}$$

所以 $A = \begin{bmatrix} 0 & 1 \\ -\omega^2 & 0 \end{bmatrix}$，$B = 0$（无外力）。

#### 观测方程

实际中我们不一定能直接看到所有状态，通过**观测方程**（measurement equation）来获取可测量的输出：

$$\mathbf{y} = C\mathbf{x} + D\mathbf{u}$$

> **课程关联**：**Lesson 03（PD 控制）** 的轮式倒立摆和 **Lesson 04（LQR 控制）** 都基于状态空间模型。Upkie 的状态是 6 维向量（关节位置+速度），控制是 6 维向量（执行器指令）。

---

### 3.2 线性化

#### 💡 直觉理解

**线性化**（linearization）用线性函数来近似一个非线性函数。就像在曲线上某一点画切线——在切点附近，切线和曲线几乎重合。

**泰勒展开**（Taylor expansion）：

$$f(x) \approx f(x_0) + f'(x_0)(x - x_0)$$

#### sinθ 的线性化

在机器人学中最常见的线性化：当 $\theta \approx 0$ 时，$\sin\theta \approx \theta$

**误差表**：

| $\theta$（度） | $\theta$（弧度） | $\sin\theta$ | 近似 $\theta$ | 误差 |
|:-:|:-:|:-:|:-:|:-:|
| 2.86° | 0.05 | 0.04998 | 0.05 | **0.04%** |
| 5.73° | 0.10 | 0.09983 | 0.10 | **0.17%** |
| 11.5° | 0.20 | 0.19867 | 0.20 | **0.67%** |
| 28.6° | 0.50 | 0.47943 | 0.50 | **4.1%** |
| 57.3° | 1.00 | 0.84147 | 1.00 | **15.9%** |

> **结论**：$\theta < 0.2 \;\text{rad}$（约 11.5°）时误差小于 1%，工程上可安全使用。

**为什么 $\cos\theta \approx 1$？**

当 $\theta$ 很小时，$\cos\theta \approx 1$。在 $\theta = 0.1$ rad 时，$\cos(0.1) = 0.995$，误差仅 0.5%。

> **课程关联**：**Lesson 03（PD 控制）** 中轮式倒立摆的动力学方程就是通过这个近似线性化的。**Lesson 04（LQR）** 中 LQR 要求系统是线性的，所以必须在平衡点附近做线性化。

---

### 3.3 二阶系统

#### 💡 直觉理解

**二阶系统**（second-order system）用二阶微分方程描述的系统，物理上对应"质量-弹簧-阻尼器"系统。

**标准形式**：

$$\ddot{x} + 2\zeta\omega_n \dot{x} + \omega_n^2 x = 0$$

| 符号 | 含义 | 范围 | 物理类比 |
|------|------|------|----------|
| $\omega_n$ | 自然频率（natural frequency） | > 0 | 弹簧的硬度 |
| $\zeta$ | 阻尼比（damping ratio） | ≥ 0 | 阻尼器的强度 |
| $\ddot{x}$ | 加速度 | — | 质量 |

#### 阻尼比的影响

| $\zeta$ 范围 | 类型 | 行为 |
|:-----------:|:----:|:----:|
| $\zeta = 0$ | 无阻尼 | 等幅振荡，永不停止 |
| $0 < \zeta < 1$ | 欠阻尼 | 逐渐衰减的振荡 |
| $\zeta = 1$ | 临界阻尼 | 最快回到平衡，不振荡 |
| $\zeta > 1$ | 过阻尼 | 缓慢回到平衡，不振荡 |

#### 特征方程

将 $x(t) = e^{st}$ 代入标准形式，得到特征方程：

$$s^2 + 2\zeta\omega_n s + \omega_n^2 = 0$$

**求解**：

$$s = -\zeta\omega_n \pm \omega_n\sqrt{\zeta^2 - 1}$$

**稳定性条件**：所有根的**实部为负**（$-\zeta\omega_n < 0$），即 $\zeta > 0$。

> **课程关联**：**Lesson 03（PD 控制）** 中，PD 控制器的闭环系统就是二阶系统——$K_p$ 控制 $\omega_n$，$K_d$ 控制 $\zeta$。调节 PD 参数本质上就是在调这个二阶系统的阻尼和刚度。

---

## 四、概率论与信息论

### 4.1 概率基础

#### 条件概率

**条件概率**（conditional probability）：$P(A|B)$ 表示事件 B 发生的情况下事件 A 发生的概率。

$$P(A|B) = \frac{P(A \cap B)}{P(B)}$$

#### 期望值

**期望**（expectation）：随机变量的加权平均。

$$E[X] = \sum_i x_i P(x_i) \quad \text{或} \quad E[X] = \int x p(x) dx$$

#### 方差

**方差**（variance）：衡量随机变量偏离其期望的程度。

$$\text{Var}(X) = E[(X - E[X])^2] = E[X^2] - (E[X])^2$$

> **课程关联**：**Lesson 06（PPO）** 的策略梯度定理中，$\mathbb{E}_{\pi_\theta}$ 表示在策略 $\pi_\theta$ 下的期望。优势函数 $A_t = Q - V$ 中，$Q$ 是动作价值的期望。

---

### 4.2 重要性采样

#### 💡 直觉理解

**重要性采样**（importance sampling）是用一个分布采样的数据来估计另一个分布的期望。就像你想知道"四川人爱吃火锅的程度"，但你只随机采访了100个湖南人——没关系，你给每个湖南人的回答乘以一个"跨省调整因子"就行了。

#### 数学表达

想从分布 $p(x)$ 计算 $E_{p}[f(x)]$，但只有从 $q(x)$ 采样的数据：

$$E_{p}[f(x)] = \int f(x)p(x)dx = \int f(x)\frac{p(x)}{q(x)}q(x)dx = E_{q}\left[f(x)\frac{p(x)}{q(x)}\right]$$

其中 $\frac{p(x)}{q(x)}$ 就是**重要性权重**（importance weight）。

#### 数值算例

假设 $p(x)$ 是均匀分布 $[0, 10]$，$q(x)$ 是均匀分布 $[0, 5]$，想计算 $E_p[x]$：

- 从 $q$ 采样 5 个点：$[1, 2, 3, 4, 5]$
- 重要性权重：$\frac{p(x)}{q(x)} = \frac{1/10}{1/5} = 0.5$
- 加权平均：$0.5 \times (1+2+3+4+5) / 5 = 0.5 \times 15/5 = 1.5$
- 精确值：$E_p[x] = 5$

> **课程关联**：**Lesson 06（PPO）** 使用重要性采样来重用旧策略采集的数据。$r_t(\theta) = \frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{old}}(a_t|s_t)}$ 就是重要性权重。

---

## 五、最优控制基础

### 5.1 最优化问题

#### 💡 直觉理解

**最优化**（optimization）就是在所有可能的选项中，找到"最好"的那个。就像在淘宝上买手机——在价格、性能、续航之间做权衡，找到最适合你的那一款。

#### 无约束优化

$$\min_x f(x)$$

**必要条件**：$f'(x) = 0$（导数为 0 的点是极值点）

#### 数值算例

$$\min_x f(x) = x^2 - 4x + 5$$

**求解**：$f'(x) = 2x - 4 = 0 \Rightarrow x = 2$

验证：$f''(x) = 2 > 0$，所以 $x=2$ 是最小值点，$f(2) = 4 - 8 + 5 = 1$。

#### 多变量优化

$$\min_{\mathbf{x}} f(\mathbf{x})$$

**必要条件**：$\nabla f(\mathbf{x}) = 0$（梯度为零向量）

> **课程关联**：**Lesson 04（LQR）** 的核心就是对控制量 $\mathbf{u}$ 求偏导并令其为零：$\frac{\partial}{\partial \mathbf{u}}(\cdots) = 0$，找到使代价函数最小的控制律。

---

### 5.2 HJB 方程

#### 💡 直觉理解

**HJB 方程**（Hamilton-Jacobi-Bellman equation）是**最优性原理**的数学表达。最优性原理说："如果一个策略全局最优，那么从任何中间状态出发，剩下的策略也一定最优。"

这就像下棋——如果某一步棋是全局最优的一步，那么从这一步之后的所有走法，也一定是"从这一步开始"的最优走法。

#### 数学形式

$$0 = \min_{\mathbf{u}} \{ \text{瞬时代价} + \text{未来代价的变化率} \}$$

$$0 = \min_{\mathbf{u}} \{ \mathbf{x}^T Q \mathbf{x} + \mathbf{u}^T R \mathbf{u} + \frac{\partial V}{\partial \mathbf{x}}(A\mathbf{x} + B\mathbf{u}) \}$$

其中 $V(\mathbf{x})$ 是**值函数**（value function），表示从状态 $\mathbf{x}$ 出发的最优累计代价。

#### 为什么猜 $V(\mathbf{x}) = \mathbf{x}^T P \mathbf{x}$？

因为代价函数是二次型 $\mathbf{x}^T Q \mathbf{x}$，值函数取同样形式不仅自然，而且能保证导数是线性形式（$\frac{\partial V}{\partial \mathbf{x}} = 2\mathbf{x}^T P$），和控制律 $\mathbf{u} = -K\mathbf{x}$ 自洽。

> **课程关联**：**Lesson 04（LQR）** 的 Riccati 方程推导完全基于 HJB 方程。核心推导就是：定义 $V$ → 写出 HJB → 对 $\mathbf{u}$ 求导 → 代回得 Riccati 方程。

---

## 六、强化学习基础

### 6.1 策略梯度

#### 对数导数技巧

$$\nabla_\theta \log \pi_\theta(a|s) = \frac{\nabla_\theta \pi_\theta(a|s)}{\pi_\theta(a|s)}$$

这个技巧把"对概率求导"转化成"对对数概率求导"，优点是数值稳定（避免概率接近 0 时的数值问题），而且有利于后面的推导。

#### 为什么对数导数出现在策略梯度中？

策略梯度定理：

$$\nabla_\theta J(\theta) = \mathbb{E}[\nabla_\theta \log \pi_\theta(a|s) \cdot Q(s,a)]$$

\log 出现的原因是：对 $\pi_\theta$ 求导时，$\frac{d}{d\theta}\log\pi_\theta = \frac{1}{\pi_\theta}\frac{d\pi_\theta}{d\theta}$，而 $\mathbb{E}[X] = \sum \pi X$ 中的 $\pi$ 恰好与 $1/\pi$ 抵消。

> **课程关联**：**Lesson 06（PPO）** 的策略梯度定理和 PPO-Clip 目标函数都基于这个技巧。

---

## 附录：各章所需数学知识速查

| 课程章节 | 需要的数学知识 | 参考本文档节 |
|----------|---------------|-------------|
| Lesson 02: MuJoCo 基础 | 数值积分、线性代数 | 2.3, 1.1 |
| Lesson 03: PD 控制 | 二阶系统、线性化、微分方程 | 3.3, 3.2, 2.1 |
| Lesson 04: LQR 控制 | 状态空间、二次型、矩阵求逆、HJB 方程 | 3.1, 1.3, 1.2, 5.2 |
| Lesson 05: Gymnasium 环境 | 期望值、概率 | 4.1 |
| Lesson 06: 强化学习 PPO | 策略梯度、重要性采样、对数导数 | 6.1, 4.2, 6.1 |
| Lesson 07: 鲁棒性 | 随机变量、方差 | 4.1 |
