# 15 稳定性、极点与频域直觉

> 建设状态：可执行  
> 阶段：经典控制  
> 作品集目录：`outputs/portfolio/15`

## 岗位任务

同事给你两组控制参数。一组响应会逐渐安静，另一组最初看似振荡相近，随后振幅越来越大。你需要在长时间仿真前先用极点判断稳定性，再用时域和频域曲线交叉验证，避免只凭“前两秒看起来没问题”做结论。

## 学习目标

- 从二阶特征多项式求极点并解释实部、虚部；
- 把自然频率、阻尼比映射到衰减速度和振荡频率；
- 用同一参数连接极点图、自由响应和频率增益；
- 区分局部线性稳定与全局机器人安全；
- 识别负阻尼和接近共振时的第一处数据证据。

## 前置关卡

需要理解 14 章的局部线性模型，并能解高中二次方程。复数只需理解为“实部决定包络，虚部决定振荡”。

## 先观察现象

```powershell
python scripts/run_classical_control_lab.py --chapter 15
```

绿色曲线使用 `zeta=0.7`，橙色曲线使用 `zeta=-0.1`。真实运行 4 秒后：

stable_final_abs_state: 6.052156540856485e-06
unstable_peak_abs_state: 4.845606967001785

两条曲线都可能穿过零点，单次过零不代表稳定。稳定要求状态包络随时间趋向零。

## 直觉与概念

<!-- upkie-animation:15-intuition -->

极点像系统自身偏好的运动方式。负实部意味着每转一圈振幅都缩小，正实部意味着每转一圈振幅都放大；虚部越大，来回摆动越快。阻尼不是“越大越高级”，而是在响应速度、超调和噪声敏感度之间权衡。

频域则换一个问法：如果持续用不同频率推机器人，它会把哪个频率放大最多？时域看一次扰动怎样消失，频域看持续扰动怎样通过系统。

## 三种证据的关系

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 260" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="200" y="10" width="140" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="270.0" y="32" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">特征多项式</text>
<rect x="40" y="62" width="160" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="120.0" y="84" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">极点 s1, s2</text>
<rect x="40" y="112" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.0" y="132" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="125.0" dy="0">自由响应</tspan>
<tspan x="125.0" dy="22">衰减/振荡/发散</tspan>
</text>
<rect x="340" y="62" width="160" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="420.0" y="82" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="420.0" dy="0">传递函数</tspan>
<tspan x="420.0" dy="22">H(j omega)</tspan>
</text>
<rect x="330" y="130" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="415.0" y="150" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="415.0" dy="0">频率增益</tspan>
<tspan x="415.0" dy="22">共振与带宽</tspan>
</text>
<line x1="270" y1="27" x2="120" y2="62" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="120" y1="96" x2="120" y2="112" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="270" y1="27" x2="420" y2="62" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="420" y1="114" x2="420" y2="130" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<rect x="200" y="198" width="140" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="270.0" y="220" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">时域实验</text>
<line x1="120" y1="164" x2="270" y2="198" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="420" y1="182" x2="270" y2="198" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="200" y1="182" x2="270" y2="198" stroke="#d36b27" stroke-width="1.5" stroke-dasharray="5,3.5" marker-end="url(#ad)"/>
<text x="230" y="215" text-anchor="middle" fill="#d36b27" font-size="13" font-family="inherit">饱和/接触/非线性 → 线性分析未覆盖</text>
</svg></div>

## 教科书级展开

<!-- upkie-animation:15-parameter -->

### 1. 标准二阶模型

$$
x_{\text{ddot}} + 2 \zeta omega_{n} x_{\text{dot}} + omega_{n}^2 x = 0
$$

- `x`：偏离平衡点的状态，本实验无量纲；
- `omega_n`：自然频率，rad/s；
- `zeta`：阻尼比，无量纲；
- 时间单位：s。

令试探解 `x(t)=exp(s t)`，则：

$$
x_{\text{dot}} = s \exp(s t)
x_{\text{ddot}} = s^2 \exp(s t)
$$

代回并除去非零的 `exp(s t)`：

$$
s^2 + 2 \zeta omega_{n} s + omega_{n}^2 = 0
$$

### 2. 不跳步求极点

由二次方程公式：

$$
s = [-2 \zeta omega_{n} \pm  \sqrt((2 \zeta omega_{n})^2 - 4 omega_{n}^2)] / 2
  = -\zeta omega_{n} \pm  omega_{n} \sqrt(\zeta^2 - 1)
$$

当 `0<zeta<1`：

$$
s = -\zeta omega_{n} \pm  j omega_{n} \sqrt(1-\zeta^2)
$$

实部 `-zeta omega_n` 决定指数包络，虚部决定振荡角频率。

### 3. 稳定参数手算

实验取 `omega_n=4 rad/s, zeta=0.7`：

实部 = -0.7*4 = -2.8 1/s
虚部 = 4*sqrt(1-0.7^2) ≈ 2.857 rad/s
s1,2 ≈ -2.8 ± j2.857

因此包络约按 `exp(-2.8t)` 衰减。实验报告：

stable_max_real_pole: -2.8

### 4. 负阻尼为什么发散

把 `zeta` 改为 `-0.1`：

实部 = -(-0.1)*4 = +0.4 1/s

正实部使包络按 `exp(0.4t)` 增长。真实结果：

unstable_max_real_pole: 0.40000000000000024

尾数来自浮点表示，不代表物理精度达到 16 位。

### 5. 频率响应

对单位静态增益的二阶低通：

$$
|H(j \omega)| = omega_{n}^2 /
\sqrt((omega_{n}^2-\omega^2)^2 + (2 \zeta omega_{n} \omega)^2)
$$

当输入频率接近自然频率时，两项竞争决定是否出现共振峰。`zeta=0.7` 接近 `1/sqrt(2)`，响应较平坦，本实验扫频得到峰值 `1.0002000600011722`，没有尖锐共振。这个略高于 1 的数值还受到频率网格离散影响。

### 6. 离散仿真假设

实验用半隐式 Euler，`dt=0.002 s`。采样频率远高于 `omega_n=4 rad/s` 对应的运动频率。若 `dt` 过大，数值积分本身可能让稳定连续系统看起来发散，所以必须同时报告连续极点和离散仿真步长。

### 7. 适用范围与失效条件

极点结论针对平衡点附近、参数固定、未饱和的线性模型。Upkie 轮子离地、腿形变化、动作限幅或姿态进入大角度后，系统矩阵已经改变。局部极点稳定不等于机器人永不跌倒；它只是必要证据之一。

## 代码映射

```python
def second_order_poles(omega_n, zeta):
    return np.roots([1.0, 2.0 * zeta * omega_n, omega_n**2])

for k in range(1, len(time)):
    acceleration = -2*zeta*omega_n*velocity - omega_n**2*position[k-1]
    velocity += dt * acceleration
    position[k] = position[k-1] + dt * velocity
```

`np.roots` 给解析模型的极点，循环给离散数值证据。两者结论不一致时，先检查步长、符号和状态更新顺序。

## 动手检查点

```powershell
python scripts/run_classical_control_lab.py --chapter 15
python scripts/course_checkpoint.py --chapter 15
```

完整真实指标：

stable_max_real_pole: -2.8
unstable_max_real_pole: 0.40000000000000024
stable_final_abs_state: 6.052156540856485e-06
unstable_peak_abs_state: 4.845606967001785
frequency_peak_gain: 1.0002000600011722

## 可视化证据

<!-- upkie-animation:15-evidence -->

- `outputs/plots/classical_15.png`：稳定/不稳定时域响应和稳定扫频；
- `outputs/logs/classical_15.json`：极点实虚部与参数；
- `outputs/results/classical_15.json`：量化门槛；
- `outputs/portfolio/15/evidence.json`：作品集索引；
- `outputs/results/checkpoint_15.json`：自动测试。

## 故障诊断挑战

<!-- upkie-animation:15-comparison -->

把阻尼项符号从负反馈写成正反馈，相当于 `zeta<0`。诊断顺序：先看极点实部，再看时域包络，最后看动作是否在尚未饱和前就注入能量。不要等机器人跌倒才定位。

再把 `dt` 改成 0.2 s。若离散曲线发散但连续极点仍在左半平面，第一嫌疑是数值积分，不应立刻重调控制增益。

## 三档任务

- 基础任务：手算两组极点，运行实验并核对实部。
- 岗位挑战：比较 `zeta=0.2,0.7,1.0,1.5` 的超调、调节时间和频率峰值。
- 开放探索：把连续极点映射到离散极点 `z=exp(s dt)`，研究采样周期变化。

## 专业里程碑

你现在能在运行长仿真前用极点筛掉明显不稳定设计，并能用时域/频域证据复核。作品集应包含一张双域图和一份“连续模型稳定但数值仿真失败”的诊断说明。

## 复盘与面试

1. 极点实部和虚部分别决定什么？
2. 为什么过零不能证明稳定？
3. `zeta=0.7` 为什么几乎没有共振峰？
4. 连续极点稳定但仿真发散时先查什么？
5. 局部稳定为什么不等于轮足机器人全局安全？

## 下一关

16 章将单个二阶变量扩展为 `[x, x_rate, pitch, pitch_rate]` 四状态系统，并检查轮端输入是否真的能影响所有不稳定状态。
