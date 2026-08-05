# 18 速度、偏航、高度与动作接口

> 建设状态：可执行  
> 阶段：经典控制  
> 作品集目录：`outputs/portfolio/18`

## 岗位任务

上层任务只想表达“向前 0.1 m/s、以 0.45 rad/s 转向、机身降低 0.02 m”，底层却需要六维执行器动作、左右轮方向、力矩限幅、腿部镜像关节和失稳保护。你的任务是建立一个统一 `MotionCommand` 接口，并在 MuJoCo 中依次验证速度、偏航和高度三种命令。

真正的工程难点不只是三条公式，而是通道耦合和生命周期：上一段速度任务留下的目标位置若不清除，会在下一段转向任务中继续产生平衡力矩。

## 学习目标

- 区分高层运动命令与低层执行器动作；
- 推导速度斜坡、偏航差动力矩和高度镜像腿目标；
- 正确处理模型左右轮方向系数 `[1,-1]`；
- 解释模式切换为什么要调用 `reset()`；
- 用真实闭环指标评价跟踪、稳定、接触与限幅。

## 前置关卡

需要完成 11 章模型契约、12 章 PD 平衡和 17 章 LQR 对比。你必须知道当前动作顺序由执行器映射决定，不能假设数组最后两项永远是同符号轮端力矩。

## 先观察现象

实验开发时，三段任务最初连续运行但不重置内部参考。偏航 6 秒只转了约 `0.265 rad`，俯仰峰值升到 `0.319 rad`。根因是速度任务留下的目标位置继续驱动平衡器，不是偏航增益太小。

加入任务边界复位后重新运行：

```powershell
python scripts/run_classical_control_lab.py --chapter 18
```

真实结果变为：

yaw_change_rad: 0.5301153714449112
max_pitch_error_rad: 0.11648018773140617
wheel_contact_ratio: 1.0

这是一类典型岗位故障：单个功能都能跑，组合流程却因隐藏状态互相污染。

## 直觉与概念

<!-- upkie-animation:18-intuition -->

高层命令像驾驶员说“多快、往哪转、站多高”；低层控制器像底盘，把意图翻译成每个电机和关节可执行的有限动作。接口必须把单位、范围、默认值、模式切换和安全降级写清楚。

本章的 `height=0` 表示标称站姿，不额外用高度误差修腿；非零高度才启动比例映射。这样速度阶段不会被高度通道无意干扰。

## 控制架构

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 550" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="180" y="8" width="240" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="300.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="300.0" dy="0">MotionCommand</tspan>
<tspan x="300.0" dy="22">v m/s, yaw_rate rad/s, height m</tspan>
</text>
<rect x="180" y="74" width="240" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="300.0" y="96" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">安全检查：俯仰误差 ≤ 0.18 rad</text>
<rect x="460" y="122" width="180" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="550.0" y="144" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">速度斜坡 0.2 m/s²</text>
<rect x="60" y="126" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="145.0" y="146" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="145.0" dy="0">偏航率 P 控制</tspan>
<tspan x="145.0" dy="22">差动力矩</tspan>
</text>
<rect x="60" y="196" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="145.0" y="216" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="145.0" dy="0">高度 P 映射</tspan>
<tspan x="145.0" dy="22">镜像腿目标</tspan>
</text>
<rect x="460" y="196" width="190" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="555.0" y="218" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">轮式平衡器：公共力矩</text>
<rect x="210" y="248" width="200" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="310.0" y="270" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">左右轮力矩混合</text>
<rect x="60" y="300" width="190" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="155.0" y="320" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="155.0" dy="0">乘 wheel_directions</tspan>
<tspan x="155.0" dy="22">映射模型 ctrl</tspan>
</text>
<rect x="470" y="300" width="160" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="550.0" y="322" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">4 个腿位置动作</text>
<rect x="210" y="366" width="170" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="295.0" y="388" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">6 维动作 + 限幅</text>
<rect x="230" y="414" width="150" height="34" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="305.0" y="436" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">MuJoCo / 实机</text>
<rect x="210" y="462" width="220" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="320.0" y="482" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="320.0" dy="0">姿态、速度、偏航率</tspan>
<tspan x="320.0" dy="22">高度、接触</tspan>
</text>
<line x1="300" y1="60" x2="300" y2="74" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="300" y1="108" x2="460" y2="138" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="260" y1="108" x2="145" y2="126" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="170" y1="108" x2="145" y2="196" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="460" y1="156" x2="460" y2="196" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="230,152 230,234 10,234 10,248" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="460,230 460,234 10,234 10,248" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="10,282 10,326 -50,326 -50,300" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="230,230 470,310 170,310" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="155,352 155,368 -5,368 -5,366" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="550,334 550,368 85,368 85,366" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="-5" y1="400" x2="230" y2="414" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="340,488 340,510 -10,510 -10,91 180,91" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
</svg></div>

低层安全边界始终在确定性控制器中，上层语言或视觉模块不能绕过力矩限幅和失稳降级。

## 教科书级展开

<!-- upkie-animation:18-parameter -->

### 1. 运动命令契约

command = {forward_velocity, yaw_rate, height, source}

- `forward_velocity`：前向速度目标，m/s；本控制器限制到 `±0.12 m/s`；
- `yaw_rate`：绕竖直轴角速度目标，rad/s；
- `height`：相对标称基座高度目标，m；0 表示标称站姿；
- `source`：命令来源，用于日志和故障追踪。

### 2. 速度斜坡

高层速度不能一步跳到目标。控制周期：

$$
dt = timestep \cdot frame_{\text{skip}} = 0.002 \cdot 5 = 0.01 s
$$

加速度限制 `a_max=0.2 m/s²`，每步最大变化：

$$
delta_{v,\text{max}} = a_{\text{max}} dt = 0.2 \cdot 0.01 = 0.002 \frac{m}{s}
v_{\text{cmd}}[k] = v_{\text{cmd}}[k-1] + clip(v_{\text{target}}-v_{\text{cmd}}[k-1], \pm 0.002)
$$

从 0 到 0.1 m/s 至少需要 50 步，即 0.5 s。这既限制机械冲击，也让平衡器有时间移动目标位置。

### 3. 公共平衡力矩与偏航差动力矩

在“物理前进方向”的统一语义下：

tau_left_physical  = tau_balance - tau_yaw
tau_right_physical = tau_balance + tau_yaw

偏航控制：

tau_yaw = clip(K_yaw*(yaw_rate_target-yaw_rate), ±tau_yaw_max)

常规参数 `K_yaw=0.025 N*m/(rad/s)`，常规限幅 `0.015 N*m`；检测到角速度与目标方向相反时临时使用更强纠偏，但仍不超过 `0.03 N*m`。

模型坐标的左右轮轴是镜像的，方向系数 `[d_left,d_right]=[1,-1]`。最终写入：

$$
ctrl_{\text{left}}  = d_{\text{left}}  * tau_{\text{left},\text{physical}}
ctrl_{\text{right}} = d_{\text{right}} * tau_{\text{right},\text{physical}}
$$

若忘记方向系数，同样的“前进”物理力矩可能在模型中变成相反动作。

### 4. 数值混合算例

设公共平衡力矩 `0.20 N*m`，偏航力矩 `0.01 N*m`：

$$
tau_{\text{left},\text{physical}}  = 0.20-0.01 = 0.19 N \cdot m
tau_{\text{right},\text{physical}} = 0.20+0.01 = 0.21 N \cdot m
ctrl_{\text{left}}  = +1 \cdot 0.19 = 0.19
ctrl_{\text{right}} = -1 \cdot 0.21 = -0.21
$$

动作数组里两个符号相反，但物理前进分量相同、偏航分量相反。不要只看 ctrl 数字符号判断转向。

### 5. 高度到镜像关节

标称站姿：

left_hip=-0.2, left_knee=0.6
right_hip=0.2, right_knee=-0.6 rad

高度误差 `e_h=h_target-h_current`，关节修正：

$$
\delta = clip(K_{h} e_{h}, -0.1, 0.1) rad
left_{\text{hip}}  = nominal_{\text{left},\text{hip}}  + \delta
left_{\text{knee}} = nominal_{\text{left},\text{knee}} - \delta
right_{\text{hip}} = nominal_{\text{right},\text{hip}} - \delta
right_{\text{knee}}= nominal_{\text{right},\text{knee}}+ \delta
$$

镜像符号保证左右腿几何动作一致。本实验选 `K_h=4 rad/m`。增益扫描表明 2 和 4 保持接触，6 已导致俯仰超过 `1.65 rad`、接触率降至约 0.287；因此 4 是当前模型的保守上界附近，不可继续盲增。

### 6. 模式切换与隐藏状态

`WheelBalancerController` 保存目标位置、上次时间和滤波力矩；速度斜坡也保存当前命令。任务从速度切到原地偏航时，应显式执行：

controller.reset()

下一次计算会把当前位置设为新的目标位置。若不重置，旧位置误差与偏航差动力矩同时竞争，导致动作饱和或姿态增大。

### 7. 安全降级

当 `|pitch_error|>0.18 rad`，控制器把速度、偏航和高度请求清零，重置目标位置，并累计 `safety_interventions`。最终动作仍经过模型 `ctrlrange`，轮端绝对值不超过 `1 N*m`。

### 8. 适用范围和限制

本章高度通道是局部比例关节映射，不是带运动学标定的精密高度伺服。目标 `-0.02 m` 的最终误差仍有 `0.01460 m`，只比零动作基线改善 1.37 倍。它适合教授接口、镜像和耦合，不应外推为复杂地形高度控制。

偏航模型也依赖双轮接地；单轮离地时差动力矩关系失效。实机还需要电机电流、轮胎侧滑和通信时延约束。

## 代码映射

```python
physical_torque = direction * action[actuator_id]
physical_torque += turn_sign * yaw_torque
action[actuator_id] = direction * physical_torque

leg_targets = (
    height.compute_targets(nominal_pose, target_height=target_height,
                           current_height=state["base_height"])
    if abs(target_height) > 1e-9
    else nominal_pose
)
return np.clip(action, runner.ctrl_low, runner.ctrl_high)
```

输入是 `MotionCommand` 和机器人状态，输出固定为 `(nu,)=(6,)`。副作用包括速度斜坡、目标位置、滤波力矩和安全计数；`reset()` 是公开生命周期契约的一部分。

## 动手检查点

```powershell
python scripts/run_classical_control_lab.py --chapter 18
python scripts/course_checkpoint.py --chapter 18
```

17 秒实验分为：0-8 秒速度、8-14 秒偏航、14-17 秒高度。任务边界调用 `reset()`。真实输出：

velocity_error_m_s: 0.04012579482076397
yaw_change_rad: 0.5301153714449112
height_error_m: 0.014596411153010167
height_improvement_ratio: 1.3701998244873685
max_pitch_error_rad: 0.11648018773140617
wheel_torque_peak_nm: 0.2896468368635672
wheel_contact_ratio: 1.0

## 可视化证据

<!-- upkie-animation:18-evidence -->

- `outputs/plots/classical_18.png`：速度目标/测量、偏航角、高度与俯仰；
- `outputs/logs/classical_18.json`：降采样原始轨迹和控制周期；
- `outputs/results/classical_18.json`：七项指标和门槛；
- `outputs/portfolio/18/evidence.json`：作品集；
- `outputs/results/checkpoint_18.json`：自动测试。

速度误差门槛 `<=0.15 m/s`，偏航变化 `>=0.5 rad`，高度误差 `<=0.018 m`，高度改善 `>=1.2`，俯仰 `<=0.3 rad`，力矩 `<=1 N*m`，接触率 `>=0.95`。

## 故障诊断挑战

<!-- upkie-animation:18-comparison -->

故障一：删除两个任务边界的 `controller.reset()`。按“偏航不足 -> 俯仰峰值增大 -> balance.target_position 仍属于速度阶段 -> 根因”为证据链，不要先调大偏航增益。

故障二：把 `wheel_directions` 改成 `[1,1]`。模型契约 11 应先拒绝；若绕过契约，前进和转向语义会混乱。这说明早期关卡是后续安全防线，不是一次性练习。

故障三：把高度增益改成 6。观察俯仰和接触先恶化，不能只看高度瞬时更接近目标。

## 三档任务

- 基础任务：手算轮端混合算例，运行两个检查点，解释七项指标。
- 岗位挑战：在不改门槛的前提下加入 `0.05 rad/s` 偏航率噪声，设计滤波并报告延迟。
- 开放探索：建立腿部运动学标定表或局部雅可比，使高度误差显著低于当前比例映射，并保留失稳边界扫描。

## 专业里程碑

你已经把单一平衡器扩展为具备命令契约、通道混合、状态复位和安全降级的运动接口。作品集应展示三阶段曲线、模式串扰故障和增益 2/4/6 的安全边界对比。

## 复盘与面试

1. 为什么 ctrl 中左右轮符号相反仍可能表示共同前进？

<!-- upkie-qa:18-q1 -->
因为模型里左右轮的方向系数是 `[1,-1]`：两个轮子安装方向镜像，同一个"物理前进力矩"映射到 ctrl 数组时符号相反。以正文算例为例：物理力矩 `tau_left=0.19, tau_right=0.21` 都是前进方向，但写入 ctrl 后变成 `+0.19` 和 `-0.21`。判断机器人在前进还是转向，必须先用方向系数换算回物理语义（`physical = direction * ctrl`），再看共同分量（前进）和差动分量（偏航）；直接拿 ctrl 数字符号下结论是 11 章模型契约强调过的典型陷阱。
<!-- /upkie-qa -->

2. 速度斜坡的 `0.002 m/s/step` 怎样算出？

<!-- upkie-qa:18-q2 -->
由控制周期和加速度上限两个物理量相乘得到。控制周期 `dt = timestep * frame_skip = 0.002 * 5 = 0.01 s`；加速度限制 `a_max = 0.2 m/s²`；每步最大速度变化 `delta_v_max = a_max * dt = 0.2 * 0.01 = 0.002 m/s`。每步命令按 `v_cmd[k] = v_cmd[k-1] + clip(v_target - v_cmd[k-1], ±0.002)` 更新，从 0 到 0.1 m/s 至少 50 步即 0.5 s。斜坡的意义有两层：限制机械冲击，也给平衡器留出时间逐步移动目标位置，避免目标突变引发姿态大扰动。
<!-- /upkie-qa -->

3. 模式切换为什么必须考虑控制器内部状态？

<!-- upkie-qa:18-q3 -->
因为 `WheelBalancerController` 不是无状态函数：它保存目标位置、上次时间和滤波力矩，速度斜坡也保存当前命令。本章的真实故障就是证据：三段任务连续运行不复位时，速度任务留下的目标位置继续驱动平衡器，与偏航差动力矩竞争，导致 6 秒只转了 0.265 rad、俯仰峰值升到 0.319 rad；加入任务边界 `controller.reset()` 后偏航提升到 0.530 rad。这是典型岗位故障模式：单个功能都能跑，组合流程却因隐藏状态互相污染。模式切换时必须显式定义哪些内部状态清零、哪些保留。
<!-- /upkie-qa -->

4. 高度增益 6 为什么不能因误差更小就采用？

<!-- upkie-qa:18-q4 -->
因为跟踪误差只是多目标中的一项，安全约束一票否决。增益扫描结果显示：`K_h=2` 和 `4` 都能保持轮子接触，而 `6` 已导致俯仰超过 1.65 rad、接触率降到约 0.287——机器人实际上已经失控离地，即使高度误差数字更好看也没有意义：高度通道的快速腿部动作会扰动质心和俯仰，增益越大扰动越猛，平衡器追不上。正确做法是在满足全部安全门槛（接触率、俯仰峰值）的候选中选跟踪最好的，所以取 4 作为保守上界附近的工作点，不可继续盲增。
<!-- /upkie-qa -->

5. 上层 VLA 为什么不能直接输出未限幅轮端力矩？

<!-- upkie-qa:18-q5 -->
因为 VLA 输出是学习得到的、没有物理保证的高层意图，而轮端力矩直接决定平衡生死：一帧错误的大力矩就可能让机身在几百毫秒内倒下，神经网络无法承诺每帧输出都在安全范围。正确分层是：VLA 输出有界的 `MotionCommand`（速度、偏航率、高度，各自有单位、范围和默认值），底层接口再依次施加速度斜坡、安全检查（`|pitch_error|>0.18 rad` 时清零降级）和模型 `ctrlrange` 限幅（轮端≤ `1 N*m`）。这样即使上层输出离谱命令，安全层也能兜底；把安全寄托在网络"大概率正确"上是工程不可接受的。
<!-- /upkie-qa -->

6. 当前高度控制还有哪些明确局限？

<!-- upkie-qa:18-q6 -->
至少三条：第一，它只是局部比例关节映射（`K_h=4 rad/m` 镜像修正髋/膝角），没有运动学标定，目标 `-0.02 m` 的最终误差仍有 0.0146 m，只比零动作基线改善 1.37 倍，不是精密高度伺服；第二，安全裕度窄，增益扫到 6 就失稳离地，无法支持大幅或快速高度变化；第三，它假设双轮接地、平坦地面和准静态过程，不能外推到复杂地形高度控制；实机还要叠加电机电流、轮胎侧滑和通信时延约束。开放探索给出的改进方向是建立腿部运动学标定表或局部雅可比。
<!-- /upkie-qa -->

## 下一关

19 章将处理传感器噪声：控制器不能直接信任每一帧姿态，需要用陀螺仪短期动态和加速度计长期参考构造互补滤波估计。
