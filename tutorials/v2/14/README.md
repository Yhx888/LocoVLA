# 14 轮式倒立摆动力学

> 建设状态：可执行  
> 阶段：经典控制  
> 作品集目录：`outputs/portfolio/14`

## 岗位任务

控制器在小角度附近工作正常，推倒到 60° 后却完全不符合线性预测。你需要建立一个可手算的轮式倒立摆俯仰模型，说明重力项、转动惯量和轮端力矩怎样共同决定角加速度，并量化小角度近似的有效范围。

本关不把简化模型冒充完整 Upkie 多刚体模型。它的价值是提供可解释局部模型，用于检查符号、单位、数量级和后续状态空间推导。

## 学习目标

- 从转动形式的牛顿第二定律写出非线性俯仰方程；
- 解释为什么直立倒立摆的重力项会放大偏角；
- 用 `sin(theta)≈theta` 推导线性化，并写明平衡点；
- 计算 `0.5 N*m` 对角加速度的作用增益；
- 从图表判断 10° 与 60° 时近似误差为何不同。

## 前置关卡

需要完成 04 章的线性化基础和 11 章的轮端力矩契约。你应当知道角度用 rad、力矩用 N*m，不能把角度数直接代入三角函数。

## 先观察现象

```powershell
python scripts/run_classical_control_lab.py --chapter 14
```

图中绿色阴影是 `|theta|<=10°`。非线性曲线和线性曲线在这里接近；到 60° 时，两者角加速度差达到：

large_angle_error_rad_s2: 3.5545975322265626

先比较曲线在哪个角度开始明显分开。这个分界不是“算法突然坏了”，而是被省略的高阶项逐渐变大。

## 直觉与概念

<!-- upkie-animation:14-intuition -->

把机器人上半身想成倒立扫把。扫把偏得越多，重力让它继续倒下的转动作用越明显；轮子施加反向力矩，试图把支撑点移到质心下方。质量更大或质心更高时，重力作用更强；转动惯量更大时，同样力矩产生的角加速度更小。

Upkie 是自由基座、多刚体、带接触的系统。本章只保留一个俯仰角和一个等效轮端力矩，目的是看清主导关系。

## 建模边界

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1270 100" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="14" width="150" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="95.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="95.0" dy="0">完整 Upkie</tspan>
<tspan x="95.0" dy="22">13 q, 12 v</tspan>
</text>
<line x1="170" y1="40" x2="190" y2="40" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="190" y="14" width="150" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="265.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="265.0" dy="0">锁定腿形</tspan>
<tspan x="265.0" dy="22">合并质量与质心</tspan>
</text>
<line x1="340" y1="40" x2="360" y2="40" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="360" y="14" width="150" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="435.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="435.0" dy="0">单俯仰自由度</tspan>
<tspan x="435.0" dy="22">theta</tspan>
</text>
<line x1="510" y1="40" x2="530" y2="40" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="530" y="14" width="150" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="605.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="605.0" dy="0">非线性模型</tspan>
<tspan x="605.0" dy="22">sin(theta)</tspan>
</text>
<line x1="680" y1="40" x2="700" y2="40" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="700" y="14" width="150" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="775.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="775.0" dy="0">在 theta=0</tspan>
<tspan x="775.0" dy="22">附近线性化</tspan>
</text>
<line x1="850" y1="40" x2="870" y2="40" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="870" y="14" width="150" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="945.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="945.0" dy="0">状态空间 A,B</tspan>
<tspan x="945.0" dy="22">供 16-17 章使用</tspan>
</text>
<rect x="1060" y="14" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="1145.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="1145.0" dy="0">接触丢失/大角度</tspan>
<tspan x="1145.0" dy="22">/腿形变化</tspan>
</text>
<line x1="1145" y1="14" x2="585" y2="164" stroke="#d36b27" stroke-width="1.5" stroke-dasharray="5,3.5" marker-end="url(#ad)"/>
<text x="1115" y="6" text-anchor="middle" fill="#d36b27" font-size="13" font-family="inherit">超出适用范围</text>
</svg></div>

## 教科书级展开

<!-- upkie-animation:14-parameter -->

### 1. 假设与平衡点

为了可手算，采用：

- 等效质量 `m=10 kg`；
- 质心到轮轴距离 `l=0.5 m`；
- 重力加速度 `g=9.81 m/s^2`；
- 转动惯量近似 `I=m l^2=2.5 kg*m^2`；
- 俯仰误差 `theta=0 rad` 对应当前站立平衡点，而不是世界坐标绝对零姿态；
- 两轮接地、腿形固定、忽略摩擦柔性和执行器延迟。

### 2. 力矩平衡

绕轮轴写转动方程：

$$
I theta_{\text{ddot}} = m g l \sin(\theta) - \tau
$$

- `theta`：相对平衡点俯仰误差，rad；
- `theta_ddot`：角加速度，rad/s²；
- `mgl sin(theta)`：重力力矩，N*m；
- `tau`：用于纠偏的等效轮端力矩，N*m；
- `I`：转动惯量，kg*m²。

正 `theta` 时重力项为正，意味着偏角会自行增大，这是倒立平衡点“不稳定”的物理来源。正 `tau` 在本模型中产生负角加速度；若你的关节轴定义相反，力矩符号也会相反。

两边除以 `I`：

$$
theta_{\text{ddot}} = (m g l \sin(\theta) - \tau) / I
$$

单位检查：`N*m/(kg*m²)=(kg*m²/s²)/(kg*m²)=1/s²`，弧度无量纲，所以写作 rad/s²。

### 3. 小角度线性化

在 `theta=0` 附近，正弦泰勒展开：

$$
\sin(\theta) = \theta - \theta^\frac{3}{6} + \dots
$$

忽略三次及更高项：

$$
theta_{\text{ddot}} \approx  (m g l \theta - \tau) / I
$$

这不是把 `sin` 永久替换为角度，而是声明只在局部使用一阶近似。

### 4. 5° 数值算例

`theta=5°=0.087266 rad, tau=0.2 N*m`：

I = 10*0.5^2 = 2.5 kg*m^2
重力力矩 = 10*9.81*0.5*sin(0.087266) ≈ 4.270 N*m
theta_ddot ≈ (4.270-0.2)/2.5 ≈ 1.628 rad/s^2

线性模型把 `sin(theta)` 换成 `theta`，结果非常接近。实验在整个 `±10°` 区间得到最大误差：

small_angle_max_error_rad_s2: 0.017200379887594153

### 5. 力矩作用增益

在角度不变时：

$$
partial(theta_{\text{ddot}})/partial(\tau) = -\frac{1}{I} = -0.4 (rad/s^2)/(N \cdot m)
$$

所以增加 `0.5 N*m` 会让角加速度减少 `0.2 rad/s²`。实验报告绝对增益 `0.4`，符号则由坐标约定说明。

### 6. 与完整机器人方程的关系

多刚体系统写作：

$$
M(q) q_{\text{ddot}} + C(q,q_{\text{dot}}) q_{\text{dot}} + g(q) = S^T \tau + J^T \lambda
$$

`M` 是质量矩阵，`C` 表示速度耦合，`g` 是重力，`lambda` 是接触力。本章标量模型相当于从其中抽取一个主导俯仰方向，并把复杂接触影响折入等效参数。它不能用于计算腿部关节力矩或接触冲击。

## 代码映射

```python
def inverted_pendulum_acceleration(theta, torque, m=10.0, l=0.5, g=9.81):
    inertia = m * l**2
    return (m * g * l * np.sin(theta) - torque) / inertia

def linearized_acceleration(theta, torque, m=10.0, l=0.5, g=9.81):
    inertia = m * l**2
    return (m * g * l * theta - torque) / inertia
```

输入角度必须是 rad，力矩必须是 N*m。函数无内部状态和文件副作用，适合单元测试；实验函数负责扫角度、画图和落盘。

## 动手检查点

```powershell
python scripts/run_classical_control_lab.py --chapter 14
python scripts/course_checkpoint.py --chapter 14
```

真实输出：

small_angle_max_error_rad_s2: 0.017200379887594153
large_angle_error_rad_s2: 3.5545975322265626
torque_acceleration_gain_rad_s2_per_nm: 0.4

## 可视化证据

<!-- upkie-animation:14-evidence -->

- `outputs/plots/classical_14.png`：非线性/线性角加速度和局部有效区；
- `outputs/logs/classical_14.json`：质量、质心长度、测试力矩和指标；
- `outputs/results/classical_14.json`：阈值与 checks；
- `outputs/portfolio/14/evidence.json`：作品集索引；
- `outputs/results/checkpoint_14.json`：自动测试证据。

## 故障诊断挑战

<!-- upkie-animation:14-comparison -->

故意把 60 当作 rad 代入 `sin`。第一处异常不是“机器人跌倒”，而是输入已经远超模型声明的 `±1.2 rad` 扫描范围。再把力矩单位误写成 N*mm：`0.2 N*m` 若错误当成 `0.2 N*mm`，实际相差 1000 倍。

另一个典型错误是把重力项写成负号，得到“直立状态自然稳定”。用 `tau=0, theta>0` 检查角加速度符号可以立刻发现。

## 三档任务

- 基础任务：手算 5° 算例，运行实验并解释三个指标。
- 岗位挑战：分别把 `m`、`l` 增加 20%，保持同一角度与力矩，解释角加速度变化。
- 开放探索：从 MuJoCo 小扰动数据辨识等效 `mgl/I` 与 `1/I`，比较解析参数和辨识参数。

## 专业里程碑

你已经能把控制对象从“一个会倒的动画”还原成带单位的动力学关系，并能明确模型何时失效。作品集应包含方程假设表、局部误差图和一次符号错误诊断。

## 复盘与面试

1. 为什么直立倒立摆的重力项会放大偏角？
2. `sin(theta)≈theta` 的平衡点和有效范围是什么？
3. 为什么增加质心高度会同时改变重力力矩和惯量？
4. 接触力 `J^T lambda` 为什么不能在轮子离地时忽略？
5. 如何用小扰动实验验证力矩符号？

## 下一关

15 章会把线性模型的动态行为压缩成极点：不用逐点看完所有曲线，也能从极点实部和阻尼判断扰动会衰减、振荡还是发散。
