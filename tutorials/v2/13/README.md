# 13 PID 控制与抗饱和

> 建设状态：可执行  
> 阶段：经典控制  
> 作品集目录：`outputs/portfolio/13`

## 岗位任务

你接手一个带积分项的速度控制器。仿真里目标突然增大，轮端力矩已经到达上限，但积分器仍在累积误差；目标回到零后，机器人还继续向前冲。你的任务是复现这个现象、实现抗积分饱和，并用同一对象、同一采样周期和同一限幅量化恢复改善。

这不是“把曲线调得更好看”。执行器饱和是物理边界，控制器必须知道自己的命令何时已经无法继续增大。

## 学习目标

- 理解 P、I、D 分别根据现在、过去和变化趋势做什么；
- 从连续公式写出采样周期为 `0.01 s` 的离散积分与微分；
- 区分输出限幅和抗积分饱和，两者缺一不可；
- 解释为什么解除饱和后允许积分器重新工作；
- 生成响应、积分状态、日志和自动测试四类证据。

## 前置关卡

先完成 `12` 的 PD 平衡实验。你至少需要知道误差定义为“目标减当前”，轮端力矩限制为 `±1 N*m`。若还不能解释 `Kd` 为什么像阻尼，请先回到 12 章。

## 先观察现象

运行：

```powershell
python scripts/run_classical_control_lab.py --chapter 13
```

图中前 2 秒目标为 2，但一阶对象在 `|u|<=1` 时不可能达到 2。无保护积分器仍把误差加入内部状态，解除目标后还会维持错误方向的饱和输出；抗饱和版本则立即进入恢复。

真实结果中，解除饱和瞬间：

protected_integral_at_release: 0.0
naive_integral_at_release: 2.3389064674617983
recovery_iae_improvement_ratio: 12.635333503310314

先观察橙色曲线为什么“明知目标回零仍不回头”，再读下面的公式。

## 直觉与概念

<!-- upkie-animation:13-intuition -->

P 像看当前离目标多远；I 像把过去每一刻的欠账累加；D 像观察误差正在变好还是变坏。积分能消除长期小偏差，但如果执行器已经顶到上限，继续记账只会制造一笔无法兑现的“控制债务”。这就是积分饱和 windup。

限幅只保护执行器：`clip` 后的动作不会超过上限。抗饱和保护的是控制器内部状态：当误差正在把已经饱和的输出推得更远时，暂停积分。

## 控制数据流

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 474" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="215" y="12" width="72" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="251.0" y="34" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">目标 r</text>
<rect x="215" y="56" width="72" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="251.0" y="78" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">测量 y</text>
<rect x="197" y="100" width="107" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.4" y="122" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">误差 e=r-y</text>
<rect x="221" y="144" width="59" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.7" y="166" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">Kp e</text>
<rect x="188" y="188" width="126" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.8" y="210" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">Ki sum(e dt)</text>
<rect x="180" y="232" width="141" height="50" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.6" y="251" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="250.6" dy="0">Kd</tspan>
<tspan x="250.6" dy="22">(e-e_prev)/dt</tspan>
</text>
<rect x="190" y="292" width="122" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.9" y="314" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">未限幅 u_raw</text>
<rect x="198" y="336" width="106" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.8" y="358" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">clip 到 ±1</text>
<rect x="195" y="380" width="112" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.8" y="402" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">对象/执行器</text>
<rect x="191" y="424" width="118" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="250.0" y="446" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">冻结本次积分</text>
<line x1="230" y1="29" x2="230" y2="100" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="270" y1="73" x2="270" y2="100" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="250" y1="117" x2="250" y2="144" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="210" y1="117" x2="210" y2="188" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="290" y1="117" x2="290" y2="232" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="190,161 190,298 220,298 220,292" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="210,205 210,292 220,292" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="290,257 290,298 230,298 230,292" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="250" y1="309" x2="250" y2="336" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="250" y1="353" x2="250" y2="380" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="250" y1="353" x2="220" y2="424" stroke="#d36b27" stroke-width="1.5" stroke-dasharray="5,3.5" marker-end="url(#ad)"/>
<text x="170" y="348" text-anchor="middle" fill="#d36b27" font-size="13" font-family="inherit">已饱和且误差继续推向饱和</text>
<line x1="210" y1="441" x2="200" y2="205" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="150,397 150,73 260,73" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

安全边界在 `clip`，状态边界在条件积分；二者承担不同职责。

## 教科书级展开

<!-- upkie-animation:13-parameter -->

### 1. 符号、单位和符号约定

e(t) = r(t) - y(t)
u(t) = Kp e(t) + Ki integral(e(t) dt) + Kd de(t)/dt

- `r`、`y`：目标和测量，本实验为无量纲一阶状态；真实速度环可用 m/s；
- `e`：误差，与被控量单位相同；
- `u`：控制输入，本实验限制为 `±1`；接到 Upkie 轮端时单位为 N*m；
- `Kp`：输出单位/误差单位；
- `Ki`：输出单位/(误差单位·s)；
- `Kd`：输出单位·s/误差单位；
- `dt=0.01 s`：采样周期。

本章采用 `e=目标-当前`。如果代码使用相反定义，三个增益的符号也必须一致改变。

### 2. 从连续到离散

第 `k` 个采样点的积分近似为矩形面积累加：

$$
I_{\text{candidate}}[k] = I[k-1] + e[k] dt
$$

误差导数用相邻样本差分：

D[k] = (e[k] - e[k-1]) / dt

未限幅输出：

$$
u_{\text{raw}}[k] = Kp e[k] + Ki I_{\text{candidate}}[k] + Kd D[k]
u[k] = clip(u_{\text{raw}}[k], -u_{\text{max}}, u_{\text{max}})
$$

条件积分判断：如果 `u_raw` 已超限，且 `e * u_raw > 0`，说明本次误差会把输出推向更深饱和，于是拒绝 `I_candidate`；否则接受它。解除饱和或误差反向时，积分器重新工作。

### 3. 手算第一个采样点

实验使用 `Kp=2, Ki=3, Kd=0.05, e=2, dt=0.01 s`，首个样本没有历史误差，令微分项为 0：

$$
I_{\text{candidate}} = 0 + 2 \cdot 0.01 = 0.02
u_{\text{raw}} = 2 \cdot 2 + 3 \cdot 0.02 = 4.06
u = clip(4.06, -1, 1) = 1
$$

由于已经正向饱和且 `e*u_raw>0`，保护版本拒绝这次积分，积分状态仍为 0。无保护版本接受 0.02，并在后续样本继续累积。

### 4. 为什么“全程积分峰值为零”不是正确要求

真实结果中保护版本全程积分峰值为 `0.0635666`，不是 0。原因是解除饱和后，积分器需要正常工作来消除剩余偏差。正确检查点是饱和阶段结束瞬间的积分，而不是禁止积分器终身变化。

### 5. 假设、适用范围与失效条件

本实验假设采样周期固定、测量无大噪声、输出饱和对称。实际机器人中，微分会放大噪声，通常要对测量或 D 项滤波；执行器上下限可能不对称；存在静摩擦时，简单冻结积分可能留下稳态误差。更复杂系统可使用反算 anti-windup，但仍要说明反算增益。

## 代码映射

核心逻辑不到 20 行：

```python
candidate_integral = self.integral + error * dt
raw = (
    self.kp * error
    + self.ki * candidate_integral
    + self.kd * derivative
)
output = np.clip(raw, -self.limit, self.limit)
saturated = not np.isclose(output, raw)
pushes_further = saturated and error * raw > 0.0
if not self.anti_windup or not pushes_further:
    self.integral = candidate_integral
```

输入是误差和采样周期，输出是受限动作；内部状态是积分和上一时刻误差。`dt<=0` 会抛出异常，防止无意义的微分与积分。

## 动手检查点

```powershell
python scripts/run_classical_control_lab.py --chapter 13
python scripts/course_checkpoint.py --chapter 13
```

专属实验的其余真实指标：

protected_integral_peak: 0.06356663698825847
naive_integral_peak: 2.3389064674617983
protected_output_peak: 1.0

## 可视化证据

<!-- upkie-animation:13-evidence -->

- 图表：`outputs/plots/classical_13.png`；
- 日志：`outputs/logs/classical_13.json`；
- 结果：`outputs/results/classical_13.json`；
- 作品集：`outputs/portfolio/13/evidence.json`；
- 自动验收：`outputs/results/checkpoint_13.json`。

视觉用于比较恢复过程，日志保存配置和指标，pytest 验证恒定饱和误差下保护积分不增长。

## 故障诊断挑战

<!-- upkie-animation:13-comparison -->

把 `anti_windup=False`，不要改其他参数。按以下顺序定位：先看动作是否已经到 `+1`，再看积分状态是否仍上升，最后看目标回零后动作何时改变符号。若只看最终状态接近零，会漏掉恢复过程中的危险冲量。

常见失败二是 `dt` 单位写成毫秒数 10 而不是秒 0.01，积分每步放大 1000 倍。第一处证据是积分曲线斜率，而不是对象位置。

## 三档任务

- 基础任务：复算第一个采样点，运行两条命令并解释六个指标。
- 岗位挑战：加入标准差 0.02 的测量噪声，比较误差微分与测量微分，报告动作抖动。
- 开放探索：实现反算抗饱和，固定同一对象和限幅，与条件积分比较恢复 IAE 和稳态误差。

## 专业里程碑

你现在能区分“输出安全”和“控制器状态健康”，并能用解除饱和后的积分绝对误差证明改进。作品集应保留两条响应曲线、积分状态曲线和一次错误 `dt` 的诊断记录。

## 复盘与面试

1. 为什么只有 `clip` 仍会产生 windup？
2. 条件积分在什么情况下允许积分器反向消除积累？
3. D 项为什么容易放大编码器噪声？
4. 为什么本章检查 release 时刻，而不要求积分峰值始终为零？
5. 如果轮端正负力矩上限不同，抗饱和逻辑怎样修改？

## 下一关

14 章不再只把对象当成一阶方块，而是从质量、重力、质心高度和轮端力矩写出轮式倒立摆动力学，解释控制增益为什么必须服从物理尺度。
