# 32 具身任务与分层架构

> 建设状态：可执行
> 阶段：应用型 VLA
> 作品集目录：`outputs/portfolio/32`

## 岗位任务

你的交付物是一份"分层控制系统架构设计文档"：设计一个三层架构（任务层→规划层→控制层），让 Upkie 在保持平衡的同时执行高层任务（如"移动到红色目标"）。面试官会问："你的系统怎么保证高层决策不会破坏低层平衡？如果感知模块给出错误目标，安全层怎么拦截？"

具体交付：

1. 一张完整的系统架构图（SVG 或 Mermaid），标注每个模块的职责、数据流和频率。
2. 一段代码，实现任务调度器：每 0.01 s 更新一次动作与安全控制；MuJoCo 在两次动作更新之间完成 5 个 0.002 s 物理子步。
3. 一段安全层代码：拦截任何会导致俯仰角超过 15 度的高层指令。

## 学习目标

- **能理解**：解释分层架构的三个核心原则——频率分离、接口隔离和安全优先，以及为什么不能让高层直接控制底层执行器。
- **能推导**：从各层的延迟和频率出发，计算端到端延迟（从感知到执行），并证明安全层的响应时间必须在控制层的容许范围内。
- **能实现**：用 Python 实现一个简单的三层控制器框架，并在 Upkie 仿真中运行。

## 前置关卡

完成 `31`（Sim2Real 评估协议）的证据验收。你需要理解：

- 低层控制器（LQR/MPC/残差 RL）的接口和频率
- 执行器的力矩限制和安全约束
- 域随机化下的鲁棒性要求

## 先观察现象

**错误基线实验**：不加分层，让高层任务直接修改底层控制器的参考值。

```python
# 高层任务：每 100 步改变目标位置
for i in range(5000):
    if i % 100 == 0:
        target_x = np.random.uniform(-2, 2)  # 随机目标

    # 直接传给 LQR
    x_ref = np.array([target_x, 0, 0.3, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    u = -K @ (x - x_ref)
    data.ctrl[:] = np.clip(u, -1, 1)
    mujoco.mj_step(model, data)
```

**记录观察**：目标突然跳变 → LQR 输出很大力矩 → 机器人剧烈晃动甚至倒下。

## 直觉与概念

<!-- upkie-animation:32-intuition -->

### 分层架构：公司的组织结构

把控制系统想象成一家公司：

- **CEO（任务层）**：决定"做什么"（去红色目标那里），不关心"怎么做"
- **经理（规划层）**：把 CEO 的目标分解成可执行的计划（"先向左移动 0.5 m"）
- **员工（控制层）**：执行具体动作（"左轮力矩 0.3 N*m"），并确保不违反安全规定

**核心原则**：CEO 不能直接指挥员工——如果 CEO 突然说"所有人都跳楼"，经理应该拦截这个不合理的指令。

### 三层架构定义

任务层 (10 Hz):
输入: 语言指令, 图像
输出: 高层目标 (target_position, target_color, stop_condition)
职责: 理解任务语义, 分解子目标
规划层 (30 Hz):
输入: 高层目标, 当前状态
输出: 速度指令 (v_ref, yaw_rate_ref, height_ref)
职责: 轨迹规划, 避障, 速度限制
动作/安全控制层 (100 Hz):
输入: 速度指令, 当前状态
输出: 执行器指令 (ctrl[0:6])
职责: 平衡控制, 力矩分配, 安全限幅

当前权威配置是 `physics timestep = 0.002 s（500 Hz）`、`frame_skip = 5`，因此 `action/control update = 0.01 s（100 Hz）`。500 Hz 只负责 MuJoCo 物理积分；经过 5 个物理子步后，100 Hz 才更新一次动作和安全控制输出。二者不是两个互相矛盾的“低层控制频率”，而是积分内环与动作更新外环。

### 频率分离的原因

| 层级 | 频率 | 原因 |
|---|---|---|
| MuJoCo 物理积分 | 500 Hz | `timestep=0.002 s`，连续推进接触与刚体动力学 |
| 动作/安全控制 | 100 Hz | `frame_skip=5`，每 5 个物理子步更新一次 6 维动作 |
| 规划层 | 30 Hz | 轨迹规划需要求解优化，计算耗时约 10-30 ms |
| 任务层 | 10 Hz | 图像处理和语言理解耗时 50-100 ms |

**关键约束**：高层不能以低层的频率运行（计算太慢），低层不能以高层的频率更新参考（参考变化太快导致不稳定）。

## 教科书级展开

<!-- upkie-animation:32-parameter -->

### 架构五要素

**1. 模块**

TaskPlanner → TrajectoryGenerator → VLASafetyController → LowLevelController → MuJoCo

**2. 职责**

| 模块 | 职责 | 输入 | 输出 |
|---|---|---|---|
| TaskPlanner | 解析语言/视觉任务 | instruction, image | target_pos, target_color |
| TrajectoryGenerator | 生成平滑轨迹 | target_pos, current_state | v_ref, yaw_ref |
| VLASafetyController | 拦截不安全指令 + 平衡控制 | ExpertCommand, runner 状态 | ctrl (6 维，已限幅) |

**3. 数据流**

instruction ──→ TaskPlanner ──→ target_pos ──→ TrajectoryGenerator
image ────────→                                               │
ExpertCommand (forward_velocity, yaw_rate, stop)
│
current_state ←── MuJoCo ←── ctrl ←── VLASafetyController ←──┘
│
安全限幅 + 平衡控制

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 430" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="20" y="8" width="210" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="125.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="125.0" dy="0">RGB-D 图像</tspan>
<tspan x="125.0" dy="22">160×120×4，10 Hz</tspan>
</text>
<rect x="290" y="8" width="180" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="380.0" y="28" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="380.0" dy="0">自然语言指令</tspan>
<tspan x="380.0" dy="22">UTF-8 文本</tspan>
</text>
<rect x="155" y="74" width="210" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="260.0" y="94" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="260.0" dy="0">任务层</tspan>
<tspan x="260.0" dy="22">语言与目标检测，10 Hz</tspan>
</text>
<rect x="155" y="140" width="210" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="260.0" y="160" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="260.0" dy="0">规划层</tspan>
<tspan x="260.0" dy="22">速度与偏航参考，30 Hz</tspan>
</text>
<rect x="155" y="206" width="210" height="44" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="260.0" y="222" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="260.0" dy="0">本体状态</tspan>
<tspan x="260.0" dy="22">15 维，100 Hz</tspan>
</text>
<rect x="155" y="264" width="210" height="54" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="260.0" y="285" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="260.0" dy="0">确定性安全层</tspan>
<tspan x="260.0" dy="22">限速、俯仰门槛、紧急停止</tspan>
</text>
<rect x="155" y="334" width="210" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="260.0" y="354" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="260.0" dy="0">MuJoCo 与低层执行器</tspan>
<tspan x="260.0" dy="22">100 Hz</tspan>
</text>
<polyline points="125,60 125,100 220,100" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="380,60 380,100 300,100" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="260" y1="126" x2="260" y2="140" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="260" y1="192" x2="260" y2="206" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="220,228 220,250 365,250 365,291" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="260" y1="250" x2="260" y2="264" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="260" y1="318" x2="260" y2="334" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="365,360 365,386 220,386 220,366" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="365" y1="291" x2="385" y2="291" stroke="#d36b27" stroke-width="1.5" stroke-dasharray="5,3.5" marker-end="url(#ad)"/>
<text x="425" y="286" text-anchor="middle" fill="#d36b27" font-size="13" font-family="inherit">安全干预计数与停止锁存</text>
</svg></div>

图中的频率不是装饰：任务层来不及按 100 Hz 处理 RGB-D，低层控制也不能等待 10 Hz 的语言推理。安全层因此处在高层命令与 6 维执行器动作之间，即使任务层输出异常，俯仰门槛和紧急停止仍能在 100 Hz 控制步内生效。

**4. 接口边界**

- TaskPlanner → TrajectoryGenerator：只传递目标位置和颜色，不传递原始图像
- TrajectoryGenerator → VLASafetyController：只传递 `ExpertCommand`（forward_velocity, yaw_rate, stop），不传递完整轨迹
- VLASafetyController → MuJoCo：输出经过安全限幅的 6 维 ctrl 向量

**5. 划分原因**

每个模块独立可测试——你可以单独测试 VLASafetyController 是否拦截了危险指令，不需要运行完整的感知-规划-控制链路。

### 安全层设计

```python
import numpy as np
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.vla.expert import ExpertCommand


class VLASafetyController:
    """安全控制器：拦截可能导致翻倒的高层指令，同时输出平衡控制。"""

    def __init__(
        self,
        yaw_torque_gain: float = 0.025,
        acceleration_limit: float = 0.1,
        soft_pitch_limit: float = 0.18,
    ):
        self.balance = WheelBalancerController()
        self.yaw_torque_gain = float(yaw_torque_gain)
        self.acceleration_limit = float(acceleration_limit)
        self.soft_pitch_limit = float(soft_pitch_limit)
        self.command_velocity = 0.0
        self.safety_interventions = 0

    def reset(self) -> None:
        self.balance.reset()
        self.command_velocity = 0.0
        self.safety_interventions = 0

    def compute_action(self, runner, command: ExpertCommand) -> np.ndarray:
        """根据安全约束过滤高层命令，输出 6 维 ctrl。"""
        state = runner.posture_state()

        # 安全层核心：俯仰角过大时，强制停止移动
        safety_active = abs(float(state["pitch_error"])) > self.soft_pitch_limit
        requested_velocity = 0.0 if safety_active else float(command.forward_velocity)
        requested_yaw = 0.0 if safety_active else float(command.yaw_rate)
        if safety_active:
            self.safety_interventions += 1
            self.command_velocity = 0.0
            self.balance.target_position = float(state["x_position"])
            self.balance.last_time = runner.time

        # 加速度限幅：防止速度突变导致翻倒
        control_dt = runner.model.opt.timestep * runner.spec.frame_skip
        max_delta = self.acceleration_limit * control_dt
        velocity_error = requested_velocity - self.command_velocity
        self.command_velocity += float(np.clip(velocity_error, -max_delta, max_delta))
        self.balance.target_velocity = float(np.clip(self.command_velocity, -0.12, 0.12))

        # 底层平衡控制
        action = self.balance.compute_action(runner, runner.time)

        # 偏航力矩分配
        root_dof = int(runner.model.jnt_dofadr[runner.root_joint_id])
        measured_yaw_rate = float(runner.data.qvel[root_dof + 5])
        yaw_torque = 0.0
        if abs(requested_yaw) > 1e-6:
            if abs(requested_velocity) < 1e-6:
                opposing_motion = requested_yaw * measured_yaw_rate < 0.0
                gain = 0.05 if opposing_motion else self.yaw_torque_gain
                limit = 0.03 if opposing_motion else 0.015
                yaw_torque = float(np.clip(gain * (requested_yaw - measured_yaw_rate), -limit, limit))
            else:
                yaw_torque = 0.02 * requested_yaw
        for name in ("left_wheel_motor", "right_wheel_motor"):
            action[runner.actuator_ids[name]] -= yaw_torque

        return np.clip(action, runner.ctrl_low, runner.ctrl_high)
```

关键行设计原因：

- `abs(pitch_error) > soft_pitch_limit`：当俯仰角误差超过 0.18 rad（约 10 度），强制将速度命令和偏航命令置零。这是安全层的"预警"机制——在真正翻倒之前提前干预。
- 加速度限幅 `acceleration_limit * control_dt`：即使目标速度在允许范围内，如果变化太快也会产生过大的惯性力。通过限制每步的速度增量来防止速度突变。
- 速度硬限幅 `[-0.12, 0.12]`：确保速度指令永远在安全范围内，无论高层请求多大。
- 偏航力矩区分运动/静止状态：静止时偏航控制更精细（增益和限幅都更小），运动时直接用简单比例。

## 动手检查点

### 检查点 1：分层架构运行

```powershell
python scripts/run_vla_lab.py --chapter 32
```

预期：输出分层架构的延迟和命令拦截率指标，Upkie 保持平衡的同时执行高层任务，不突然倾倒。

### 检查点 2：安全层拦截

```powershell
python -c "
from upkie_mujoco_course.vla.control import VLASafetyController
from upkie_mujoco_course.vla.expert import ExpertCommand
controller = VLASafetyController(soft_pitch_limit=0.18)
print(f'安全俯仰角阈值: {controller.soft_pitch_limit} rad')
print(f'加速度限幅: {controller.acceleration_limit} m/s^2')
print(f'速度硬限幅: [-0.12, 0.12] m/s')
# 越权命令检查：即使传入超大速度，controller 也会在 compute_action 中截断
unsafe = ExpertCommand(forward_velocity=5.0, yaw_rate=10.0, stop=False)
print(f'越权命令: velocity={unsafe.forward_velocity}, yaw={unsafe.yaw_rate}')
print(f'controller 最大目标速度: 0.12 m/s（硬编码截断）')
"
```

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 32
```

## 可视化证据

<!-- upkie-animation:32-evidence -->

在 `outputs/plots/checkpoint_32.png` 中绘制：

1. **上图**：三层的执行频率时间线——控制层最密，任务层最疏。
2. **中图**：Upkie 在"移动到红色目标"任务下的位置轨迹。
3. **下图**：安全层的拦截事件标记——在哪些时刻安全层修改了高层指令。

## 故障诊断挑战

<!-- upkie-animation:32-comparison -->

**破坏**：去掉安全层——让规划层的速度指令直接传给控制层。

**第一处异常**：当目标距离较远时，规划层可能输出很大的速度指令，导致 LQR 为了跟踪速度而大幅倾斜躯干，俯仰角超过稳定范围，机器人倒下。

**根因假设**：没有安全层的速度限制和加速度限制，速度指令的突变产生过大的惯性力。

**最小修复**：恢复 VLASafetyController。

**验证**：Upkie 在所有目标距离下都能保持平衡。

## 三档任务

### 基础任务

- 实现三层架构框架，在仿真中运行"移动到固定目标"任务。
- 记录安全层的拦截次数和拦截时的俯仰角。

### 岗位挑战

- 设计三个不同难度的任务（近距离/中距离/远距离目标），比较成功率。
- 在规划层加入简单的避障逻辑：如果前方有障碍物，绕行。

### 开放探索

- 研究 ROS2 的行为树（Behavior Tree）框架，比较它与你实现的任务调度器的优缺点。
- 写一段 200 字分析：为什么具身系统必须分层？什么情况下可以不分层？

## 复盘与面试

1. 为什么不能让高层直接控制底层？

<!-- upkie-qa:32-q1 -->
三个不匹配。第一，频率不匹配：高层任务层运行在 10 Hz 量级（感知和规划本身就需要上百毫秒），而底层动作更新在 100 Hz；如果平衡控制等高层发号施令，机器人在两次高层决策之间的几十毫秒里就可能倒了——倒立摆的失稳时间常数远小于高层周期。注意一个容易混淆的数字：500 Hz 是 MuJoCo 物理积分频率，不是新的策略动作频率，同一动作会保持多个物理子步。第二，语义不匹配：高层的输出是“去那里”这类任务级描述，而执行器需要的是以 N*m 为单位的轮端力矩；中间必须有规划层把目标位置翻译成速度指令，再由控制层翻译成力矩，每一层只做自己量纲内的翻译。第三，安全不匹配：高层不知道力矩限幅、俯仰安全边界这些物理约束，让它直接出力矩等于把安全责任交给一个看不见物理状态的模块。分层的本质是把不同时间尺度、不同抽象层级的问题分配给各自胜任的模块，这也是 34 关安全命令和 36 关 BC 策略都只接管自己那一层的原因。
<!-- /upkie-qa -->

2. 安全层为什么必须在规划层和控制层之间？

<!-- upkie-qa:32-q2 -->
因为安全约束是物理的，不是语义的。判断一条指令安不安全，需要的信息是俯仰角离跌倒阈值还有多远、力矩是否接近限幅、速度是否超界——这些都是物理状态量，只有位于规划层下方、能看到实时状态的层级才掌握。把安全检查放在规划层之上（比如让任务层自己保证不发危险指令）不可靠：任务层只理解“去红色目标”这种语义，它无法预知这条指令在当前姿态下会不会导致跌倒。放在控制层之下也不够：控制层输出已经是最终力矩，此时只能做限幅这种末端裁剪，无法拒绝“方向性错误”的指令。夹在中间正好：安全层拿到规划层的速度指令，对照实时物理状态做审查——安全就放行，越界就拦截或降级（限速、停止），然后才交给控制层执行。这样安全保障不依赖上游任何模块的正确性：即使感知识错颜色、规划算错路径（见 q4），底线依然成立。
<!-- /upkie-qa -->

3. 端到端延迟是多少？

<!-- upkie-qa:32-q3 -->
按最坏情况估算约 140 ms：任务处理 100 ms + 规划 30 ms + 等待下一次动作更新最多 10 ms（动作更新周期 100 Hz，最坏要等一个整周期）。这个估算练习里有两个常见误区。其一，把物理积分频率当成响应频率：MuJoCo 每 2 ms 推进一个物理步，但同一个动作要保持 5 个物理子步才轮到下一次策略输出，所以新动作的最小响应周期是 10 ms 而不是 2 ms——把 2 ms 当成控制周期会把延迟低估五倍。其二，把各层延迟简单相加当成唯一答案：实际系统里各层异步运行，感知在处理新帧时控制层仍在用旧目标高频维持平衡，所以 140 ms 是“新信息传到动作”的延迟，而不是系统失控 140 ms。这也解释了分层的巧妙之处：对延迟最敏感的平衡任务由延迟最小的底层闭环负责，对延迟宽容的导航任务才由慢速高层负责；否则 140 ms 的反应时间对倒立摆早就致命了。工程上应把各段延迟写进监控日志，而不是只算一次纸面估计。
<!-- /upkie-qa -->

4. 如果感知出错（检测到错误的目标颜色），系统会怎样？

<!-- upkie-qa:32-q4 -->
规划层会忠实地向错误目标移动——它无从知道感知给的目标是错的，只能把收到的坐标当真。但安全层不依赖感知结果，它只看物理状态（俯仰、速度、力矩），所以平衡保障不受影响。最坏结果是：机器人稳稳地走到错误的地方——任务失败，但不会翻倒、不造成物理损坏。这个例子揭示了分层架构的一个深层设计原则：把“任务正确性”和“物理安全性”分离成两个独立的保证，分别由不同层级负责。任务正确性依赖感知、规划每一环都对，失效是预期内的事（感知本来就有误检率）；物理安全性则只依赖安全层和控制层这两个确定性模块，它们不用神经网络、不依赖外部输入语义，可靠性可以单独验证。评估这类系统时也应分开报告两类指标：任务成功率可以因感知退化而下降，但跌倒次数必须始终为零；37 关的失败分析框架正是沿着这条线把两类失效分开统计的。
<!-- /upkie-qa -->

## 下一关

关卡 `33`（RGB-D 相机与目标检测）会假设你已经有一个分层架构框架。本关产出的架构将成为下一关集成视觉感知的"骨架"——RGB-D 相机数据在任务层被处理，检测结果传递给规划层用于目标定位。
