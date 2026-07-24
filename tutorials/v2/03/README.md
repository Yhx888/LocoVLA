# 03 向量、矩阵与坐标变换

> 建设状态：可执行  
> 阶段：数学与工具  
> 作品集目录：`outputs/portfolio/03`

## 岗位任务

机载相机报告“目标在机器人前方 0.3 m、左侧 0.1 m”，而导航模块需要世界坐标。若把这三个数字直接当成世界坐标，机器人转身后仍会朝旧方向行驶。

本关要完成一次可逆的机身系到世界系变换，并用 SVD 检查观测矩阵是否丢失方向、用特征值分解识别对称矩阵的主方向。岗位目标不是背公式，而是能回答“这个向量在哪个坐标系里”和“这个矩阵在哪个方向最敏感”。

## 学习目标

- **理解**：区分点、向量、坐标系、旋转和平移。
- **推导**：从二维旋转推导逆变换，从 `A^T A` 推导 SVD 与特征值的关系。
- **实现**：验证坐标往返、SVD 重构和对称矩阵特征对重构误差。

## 前置关卡

完成 `02`，能够固定参数、seed 和结果身份。需要的数学只有勾股定理、正弦余弦和矩阵乘法。

## 先观察现象

假设机器人位于世界坐标 `(1.0, -0.4)`，机头相对世界 x 轴逆时针旋转 30 度。机身前方 `(0.3, 0.0)` 的点显然不应简单变成 `(1.3, -0.4)`，因为“前方”已经转向。

先画一个直角坐标系，估计这个点的世界坐标应该向 x、y 哪个方向变化。若计算结果与草图方向相反，优先检查坐标系和旋转方向，而不是调控制增益。

## 直觉与概念

<!-- upkie-animation:03-core -->

### 坐标不是物体本身

同一张桌子，从门口描述可能是“前方 2 m”，从窗边描述可能是“右侧 1 m”。物体没有移动，改变的是观察基准。

- **点**：表示位置，平移坐标系后数值会改变；
- **向量**：表示方向或差值，只旋转时改变方向，平移不会改变；
- **旋转矩阵 `R`**：描述一个坐标系的轴在另一个坐标系中怎样朝向；
- **平移向量 `t`**：描述两个坐标系原点相差多远。

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 813.8000000000001 90" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="16" width="145" height="54" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="92.7" y="37" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="92.7" dy="0">机身系点 p_body</tspan>
<tspan x="92.7" dy="22">单位 m</tspan>
</text>
<line x1="165" y1="43" x2="185" y2="43" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="185" y="16" width="168" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="269.3" y="38" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">旋转 R_world_body</text>
<line x1="353" y1="33" x2="373" y2="33" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="373" y="16" width="94" height="54" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="420.2" y="37" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="420.2" dy="0">世界方向</tspan>
<tspan x="420.2" dy="22">R p_body</tspan>
</text>
<line x1="467" y1="43" x2="487" y2="43" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="487" y="16" width="132" height="54" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="553.5" y="37" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="553.5" dy="0">加世界平移</tspan>
<tspan x="553.5" dy="22">t_world_body</tspan>
</text>
<line x1="620" y1="43" x2="640" y2="43" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="640" y="16" width="154" height="54" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="716.7" y="37" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="716.7" dy="0">世界系点 p_world</tspan>
<tspan x="716.7" dy="22">单位 m</tspan>
</text>
</svg></div>

## 教科书级展开

### 1. 二维旋转从哪里来

机身 x 轴相对世界 x 轴逆时针旋转角 `psi`。单位 x 轴在世界系中的坐标是：

$$
e_{x,\text{body},in,\text{world}} = [\cos \psi, \sin \psi]^T
$$

机身 y 轴与它垂直，因此是：

$$
e_{y,\text{body},in,\text{world}} = [-\sin \psi, \cos \psi]^T
$$

把两根轴作为矩阵的两列：

$$
R_{\text{world},\text{body}} = [[\cos \psi, -\sin \psi],                 [\sin \psi,  \cos \psi]]
$$

矩阵乘以机身坐标 `[x_b, y_b]^T`，本质上是在做线性组合：沿机身 x 轴走 `x_b`，再沿机身 y 轴走 `y_b`。

### 2. 三维偏航旋转

本关只绕竖直 z 轴旋转，z 坐标不变：

$$
R_{\text{world},\text{body}} =
[[\cos \psi, -\sin \psi, 0],  [\sin \psi,  \cos \psi, 0],  [0,        0,       1]]
$$

| 符号 | 含义 | 单位/形状 |
|---|---|---|
| `psi` | 偏航角，逆时针为正 | rad |
| `R_world_body` | 机身系向世界系旋转 | 3x3，无量纲 |
| `p_body` | 点在机身系中的坐标 | m，3 维 |
| `t_world_body` | 机身原点在世界系中的位置 | m，3 维 |
| `p_world` | 同一点在世界系中的坐标 | m，3 维 |

完整点变换：

p_world = R_world_body p_body + t_world_body

注意顺序：先旋转局部位移，再加世界平移。把平移放进旋转会改变物理含义。

### 3. 逆变换为什么使用转置

旋转矩阵的列是互相垂直的单位向量，因此：

$$
R^T R = I
R^-1 = R^T
$$

从正变换出发：

$$
p_{\text{world}} = R p_{\text{body}} + t
p_{\text{world}} - t = R p_{\text{body}}
R^T (p_{\text{world}} - t) = R^T R p_{\text{body}} = p_{\text{body}}
$$

所以逆变换是：

$$
p_{\text{body}} = R_{\text{world},\text{body}}^T (p_{\text{world}} - t_{\text{world},\text{body}})
$$

### 4. 数值算例

使用：

$$
\psi = 30 deg = \pi/6 rad
t = [1.0, -0.4, 0.2] m
p_{\text{body}} = [0.3, 0.1, -0.2] m
\cos \psi \approx  0.8660254, \sin \psi = 0.5
$$

世界坐标前两维：

$$
x_{w} = 0.8660 \cdot 0.3 - 0.5 \cdot 0.1 + 1.0 \approx  1.2098 m
y_{w} = 0.5 \cdot 0.3 + 0.8660 \cdot 0.1 - 0.4 \approx  -0.1634 m
z_{w} = -0.2 + 0.2 = 0.0 m
$$

实际日志保存了完整精度。逆变换往返误差为：

1.1857187100668868e-16 m

这接近双精度浮点舍入误差，不代表物理传感器能达到该精度；本实验验证的是代数实现。

### 5. 合法旋转矩阵的检查

合法三维旋转矩阵满足：

$$
R^T R = I
\det(R) = +1
$$

`det(R)=-1` 往往表示镜像反射，不是刚体旋转。本关实际得到：

rotation_determinant_error = 0.0
orthogonality_error = 1.051762515866283e-17

### 6. SVD：找出矩阵最强和最弱的方向

#### 第一层：直觉

把一块软橡皮先沿某些方向拉伸，再旋转到新方向。SVD 说的是：任何矩形线性映射都可以拆成“旋转或换基底 -> 沿互相垂直的方向缩放 -> 再旋转”。缩放量越小，该方向的信息越容易被测量噪声淹没。

#### 第二层：符号拆解

$$
A = U \Sigma V^T
$$

| 符号 | 含义 | 本关形状 |
|---|---|---|
| `A` | 归一化后的观测矩阵 | 3x2 |
| `V` | 输入空间的正交方向，列向量为 `v_i` | 2x2 |
| `Sigma` | 奇异值 `sigma_i` 构成的对角矩阵 | 2x2 |
| `U` | 输出空间的正交方向，列向量为 `u_i` | 3x2 |
| `V^T` | `V` 的转置 | 2x2 |

#### 第三层：物理意义与单位

若 `y=A x`，`x` 是状态变化，`y` 是传感器变化，`sigma_i` 表示沿 `v_i` 改变状态时，观测沿 `u_i` 被放大多少。本例先把各通道归一化，因此矩阵和奇异值无量纲。真实工程中若角度、速度、米混在一起而不做尺度归一化，最大奇异值可能只是在反映单位选择。

#### 第四层：为什么需要

- `sigma_min` 接近 0：至少一个状态方向几乎观测不到；
- 条件数 `kappa=sigma_max/sigma_min` 很大：反演会放大噪声；
- 保留较大的奇异值：可以构造低秩近似或压缩特征。

#### 第五层：从特征值到 SVD，不跳步

先看对称半正定矩阵 `A^T A`：

$$
A^T A v_{i} = lambda_{i} v_{i}
sigma_{i} = \sqrt(lambda_{i})
u_{i} = A v_{i} / sigma_{i}        (sigma_{i} > 0)
$$

把第三式两边乘 `sigma_i`：

A v_i = sigma_i u_i

把所有 `v_i` 排成 `V`，所有 `u_i` 排成 `U`，所有 `sigma_i` 放进 `Sigma`，同时处理全部方向：

A V = U Sigma
- `$A` — U Sigma V^T             因为 V V^T = I

#### 第六层：可手算复核的数值例子

本关矩阵为：

$$
A = [[1.0, 0.2],      [0.1, 0.9],      [0.5, 0.4]]
$$

实际日志给出：

$$
sigma_{1} = 1.2808952316
sigma_{2} = 0.7932889799
\kappa   = 1.6146640935
\lVert U \Sigma V^T - A\lVert _F = 2.6766507791e-16
$$

两个奇异值都远离 0，条件数也不大，因此这个教学观测矩阵没有明显丢失某个输入方向。

#### 第七层：Upkie 代码映射

`singular_value_decomposition()` 使用经济型分解，返回形状固定为 `U:(3,2)`、`s:(2,)`、`Vt:(2,2)`。第 03 关日志的 `svd` 节保存原矩阵、三个分解结果，结果文件用重构误差和条件数做自动检查。

### 7. 特征值分解：找出不改变方向的模式

#### 第一层：直觉

普通向量经过矩阵后方向和长度都会改变。特征向量是少数“方向不变”的向量，矩阵只把它拉长、压短或反向；特征值就是缩放倍数。

#### 第二层：符号拆解

K v_i = lambda_i v_i
- `$K` — V Lambda V^T            K 为实对称矩阵

`K` 是 2x2 对称刚度示例，`v_i` 是无量纲方向，`lambda_i` 是沿该方向的等效缩放。若 `K` 表示真实刚度，特征值会继承刚度单位；本关只使用无量纲教学矩阵。

#### 第三层：物理意义

在机器人中，对称质量矩阵、刚度矩阵和协方差矩阵经常出现。它们的特征向量可表示振动主模态或不确定性椭圆主轴；特征值表示对应模态强度。

#### 第四层：为什么需要

SVD 适合任意矩形矩阵；`eigh` 针对实对称方阵，利用对称性得到实特征值和正交特征向量。不要因为两者都返回“方向和数值”就混用接口。

#### 第五层：2x2 特征值不跳步推导

本关取：

$$
K = [[4, 1],      [1, 2]]
$$

非零特征向量要求 `(K-lambda I)v=0` 有非零解，因此行列式必须为 0：

$$
\det(K-\lambda I) = (4-\lambda)(2-\lambda)-1
                 = \lambda^2 - 6 \lambda + 7
                 = 0
\lambda = (6 +- \sqrt(36-28))/2
       = 3 +- \sqrt(2)
$$

#### 第六层：数值算例

$$
lambda_{1} = 1.5857864376
lambda_{2} = 4.4142135624
\lVert V \Lambda V^T-K\lVert _F = 4.7102773761e-16
\lVert K V-V \Lambda\lVert _F   = 2.2204460493e-16
$$

#### 第七层：代码映射与边界

`symmetric_eigendecomposition()` 明确拒绝非方阵和非对称矩阵，再调用 `np.linalg.eigh`。特征向量的整体正负号可以变化，`v` 与 `-v` 表示同一条轴，因此测试验证 `K V=V Lambda` 和重构，不硬编码向量符号。

### 假设与失效条件

- 使用右手坐标系，偏航逆时针为正；
- 角度输入必须是弧度；
- 本关只处理偏航，不代表完整 roll-pitch-yaw 组合；
- 旋转矩阵必须正交，不能混入缩放或剪切；
- 点与平移单位都为米；
- 欧拉角接近奇异姿态时应改用四元数或旋转矩阵直接传播。

## 动手检查点

```powershell
python scripts/run_foundation_lab.py --chapter 03 --seed 0
python scripts/course_checkpoint.py --chapter 03
```

验收阈值：坐标往返、旋转、SVD 重构、特征重构和特征对残差均不超过 `1e-12`，SVD 条件数不超过 `10`。

应生成：

- `outputs/results/foundation_03.json`
- `outputs/logs/foundation_03.json`
- `outputs/plots/foundation_03.png`
- `outputs/portfolio/03/evidence.json`

常见失败一：结果方向相反。检查是否误用 `R.T`，以及角度正方向。  
常见失败二：`旋转矩阵必须正交`。检查矩阵中是否混入缩放，或把角度直接填进矩阵。
常见失败三：SVD 能重构但条件数突然很大。检查列是否接近线性相关，以及是否忘记统一量纲。

## 可视化证据

图左侧的箭头展示坐标变换，右侧柱状图并列显示奇异值和特征值。三重证据为：

- **视觉**：`outputs/plots/foundation_03.png` 中方向正确，四根数值柱均可见；
- **日志**：`outputs/logs/foundation_03.json` 保存 `svd`、`eigendecomposition` 和完整矩阵；
- **自动测试**：`python -m pytest tests/test_foundations.py -q` 验证重构、正交和特征对关系。

通过本关后，你可以在作品集中展示一项岗位高频能力：明确坐标系、单位、变换方向，并用逆变换自动审计实现。

## 故障诊断挑战

运行下面的对比：

```powershell
python -c "import sys,numpy as np; sys.path.insert(0,'src'); from upkie_mujoco_course.foundations.math_tools import *; R=rotation_matrix_yaw(np.deg2rad(30)); p=np.array([.3,.1,-.2]); t=np.array([1.,-.4,.2]); print('正确=',transform_point(p,R,t)); print('误用转置=',R.T@p+t)"
```

记录两组坐标，并在图上判断哪一组符合“机身逆时针旋转 30 度”。诊断结论必须指出错误发生在变换方向，而不是归因于浮点误差。

## 三档任务

- **基础任务**：手算本章数值例子的 x、y 坐标，与日志对齐到小数点后 3 位。
- **岗位挑战**：把观测矩阵第二列改得接近第一列，比较最小奇异值和条件数怎样变化。
- **开放探索**：用齐次变换矩阵验证坐标逆变换，再比较一般方阵特征分解与对称 `eigh` 的边界。

## 复盘与面试

1. `R_world_body` 的两段下标分别表示什么？
2. 为什么点需要加平移，而速度向量通常不加？
3. 为什么逆旋转可以使用转置？前提是什么？
4. `det(R)=-1` 为什么值得警惕？
5. 角度单位错用“度”时，哪项检查可能仍通过，哪项现象会先异常？
6. 最小奇异值接近 0 为什么意味着某个方向难以观测？
7. 为什么特征向量不能用逐元素数值固定其正负号？

## 下一关

下一关 `04` 把坐标和状态随时间的变化写成微分方程，并解释为什么 LQR 等线性控制器只能在明确的平衡点附近使用。
