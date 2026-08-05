# 07 URDF、MJCF 与模型审计

> 建设状态：可执行
> 阶段：机器人仿真
> 作品集目录：`outputs/portfolio/07`

## 岗位任务

你的交付物是一份"模型审计报告"：逐字段验证 Upkie 的 MJCF 文件，确认每个 body、joint、actuator 和 sensor 的定义与 `configs/robot/upkie.json` 一致。面试官会问："你怎样确保仿真模型和真实机器人的物理参数完全对齐？"

具体交付：

1. 一份审计报告（`outputs/model_audit/upkie_v2_audit.json`），包含每个关节的类型、位置范围、父 body 和子 body。
2. 一张标注了所有坐标系和关节的模型示意图。
3. 一段 Python 代码，自动验证 MJCF 中的关节名称、轴方向和执行器增益是否与配置文件一致。

## 学习目标

- **能理解**：区分 URDF 和 MJCF 的用途——URDF 描述机器人结构（用于 ROS），MJCF 描述仿真场景（用于 MuJoCo），两者字段不完全对应。
- **能推导**：给定 MJCF 文件，手动推算出 `nq` 和 `nv` 的值，并解释每个关节对维度的贡献。
- **能实现**：编写审计脚本，自动检查模型定义与配置文件的一致性。

## 前置关卡

完成 `06`（MuJoCo 状态与时间步进）的证据验收。你需要理解：

- `qpos`、`qvel`、`ctrl` 的维度和索引含义
- MuJoCo 模型加载的基本流程
- 什么是自由关节（free joint）和铰链关节（hinge joint）

## 先观察现象

**错误基线实验**：打开 Upkie 的 URDF 文件（`assets/upkie/upkie_description/urdf/upkie.urdf`），找到任意一个 `<joint>` 标签，把它的 `axis` 属性改错（比如把 `0 1 0` 改成 `1 0 0`），然后运行仿真。

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
from upkie_mujoco_course.sim.loader import build_mujoco_model

model = build_mujoco_model()
data = mujoco.MjData(model)

# 教学简化：这里直接用硬编码索引 ctrl[0]。
# 实际应使用 actuator_map：runner.actuator_map.ids["left_hip_servo"]
# 给 left_hip 一个正方向的控制输入
data.ctrl[0] = 0.5
for _ in range(500):
    mujoco.mj_step(model, data)
```

**记录三个观察**：

1. 机器人腿部运动方向是否符合预期？如果轴方向错了，腿会往反方向弯。
2. 机器人在施加控制后是否保持平衡？轴方向错误会导致控制器输出反向。
3. `qpos` 中对应关节的值是增大还是减小？与正确的轴方向对比。

## 直觉与概念

<!-- upkie-animation:07-core -->

### URDF vs MJCF：两种"机器人说明书"

把 URDF 和 MJCF 想象成同一个人的两种简历：

| 特性 | URDF | MJCF |
|---|---|---|
| 全称 | Unified Robot Description Format | MuJoCo Format |
| 用途 | ROS 生态（运动规划、可视化） | MuJoCo 仿真 |
| 关节类型 | revolute, prismatic, fixed, continuous | hinge, slide, ball, free |
| 接触模型 | 不包含 | 包含（geom + contact） |
| 执行器 | 不包含 | 包含（actuator） |
| 传感器 | 不包含 | 包含（sensor） |

URDF 只描述"机器人长什么样"，MJCF 还描述"机器人怎么被控制"和"机器人怎么感知"。

### MJCF 层级结构

MJCF 文件的核心是 `<worldbody>` 标签内的树形结构：

<worldbody>
<body name="root">          ← 根部 body（含自由关节）
<joint type="free"/>
<geom .../>               ← 碰撞和可视化几何
<body name="left_thigh">  ← 左大腿
<joint name="left_hip" type="hinge" axis="0 1 0"/>
<geom .../>
<body name="left_shin"> ← 左小腿
<joint name="left_knee" type="hinge" axis="0 1 0"/>
<body name="left_wheel"> ← 左轮
<joint name="left_wheel" type="hinge" axis="0 1 0"/>
</body>
</body>
</body>
<body name="right_thigh"> ← 右大腿（镜像）
...
</body>
</body>
</worldbody>

每个 `<body>` 是一个刚体，`<joint>` 定义它相对于父 body 的运动自由度。

### 审计的核心问题

审计不是"看看文件有没有语法错误"，而是回答：**这个模型描述的物理实体和我预期的完全一样吗？**

审计清单：

1. **关节数量与类型**：6 个铰链关节 + 1 个自由关节 = 7 个 joint 标签
2. **关节轴方向**：hip 和 knee 应该绕 Y 轴旋转（像膝关节前后摆动），wheel 也绕 Y 轴
3. **执行器映射**：前 4 个 actuator 对应 4 个腿部关节（位置控制），后 2 个对应 2 个轮子（力矩控制）
4. **质量分布**：总质量、每个 body 的质量、质心位置
5. **关节范围**：每个关节的角度限制（`range` 属性）是否合理

## 教科书级展开

### MJCF 关节到 qpos/qvel 的映射

**规则**：

| 关节类型 | qpos 贡献 | qvel 贡献 |
|---|---|---|
| free | 7（3 平移 + 4 四元数） | 6（3 平移速度 + 3 角速度） |
| hinge | 1（角度 rad） | 1（角速度 rad/s） |
| slide | 1（位移 m） | 1（速度 m/s） |
| ball | 4（四元数） | 3（角速度） |

**Upkie 推算**：

free joint:  qpos += 7, qvel += 6
left_hip:    qpos += 1, qvel += 1
left_knee:   qpos += 1, qvel += 1
left_wheel:  qpos += 1, qvel += 1
right_hip:   qpos += 1, qvel += 1
right_knee:  qpos += 1, qvel += 1
right_wheel: qpos += 1, qvel += 1
──────────────────────────────────
总计:        qpos = 13, qvel = 12

### 执行器定义解析

MJCF 中执行器的典型定义：

```xml
<actuator>
  <!-- 腿部位置控制：hip 用 kp=40，knee 用 kp=60（来自 configs/robot/upkie.json） -->
  <position name="left_hip_servo" joint="left_hip" kp="40" />
  <position name="left_knee_servo" joint="left_knee" kp="60" />
  <position name="right_hip_servo" joint="right_hip" kp="40" />
  <position name="right_knee_servo" joint="right_knee" kp="60" />

  <!-- 轮端力矩控制 -->
  <motor name="left_wheel_motor" joint="left_wheel" ctrlrange="-1 1" />
  <motor name="right_wheel_motor" joint="right_wheel" ctrlrange="-1 1" />
</actuator>
```

**关键区别**：

- `<position>` 执行器：`ctrl` 输入是目标角度（rad），MuJoCo 内部用 `tau = kp * (target - current) - kv * velocity` 计算力矩。
- `<motor>` 执行器：`ctrl` 输入直接就是力矩（N*m），`ctrlrange="-1 1"` 限制了最大力矩为 1 N*m。

**审计要点**：如果你把腿部执行器误定义为 `<motor>` 而不是 `<position>`，控制器输出的角度值会被当作力矩值，量级差几十倍（hip 的 kp=40），机器人会剧烈抖动。注意 hip 和 knee 的 kp 不同（40 vs 60），这是因为膝关节需要更大的力矩来支撑体重。

### 代码映射：审计脚本核心

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

import mujoco
import json

from upkie_mujoco_course.sim.loader import build_mujoco_model

def audit_model(config_path: str) -> dict:
    """审计 MuJoCo 模型与配置文件的一致性。"""
    model = build_mujoco_model()
    with open(config_path) as f:
        config = json.load(f)

    report = {"joints": [], "actuators": [], "errors": []}

    # 审计关节
    for i in range(model.njnt):
        jnt_type = int(model.jnt_type[i])
        jnt_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) or ""
        info = {
            "name": jnt_name,
            "type": {0: "free", 1: "ball", 2: "slide", 3: "hinge"}[jnt_type],
            "qpos_dim": {0: 7, 1: 4, 2: 1, 3: 1}[jnt_type],
            "qvel_dim": {0: 6, 1: 3, 2: 1, 3: 1}[jnt_type],
        }
        report["joints"].append(info)

    # 审计维度（upkie.json 中嵌套在 state_dimensions 下）
    dims = config.get("state_dimensions", {})
    if model.nq != dims.get("nq", -1):
        report["errors"].append(
            f"nq 不匹配: 模型={model.nq}, 配置={dims.get('nq')}")

    return report
```

关键行设计原因：

- `{0: "free", 1: "ball", 2: "slide", 3: "hinge"}[jnt_type]`：MuJoCo 内部用整数枚举关节类型（0=free, 1=ball, 2=slide, 3=hinge），这里映射为可读字符串。
- `{0: 7, 1: 4, 2: 1, 3: 1}[jnt_type]`：每种关节对 qpos 的贡献不同，这个映射表是手动推算 nq 的代码版本。
- `mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)`：MuJoCo 的 Python 绑定推荐使用此 API 按索引查名称，比 `model.joint(i).name` 更稳定。

## 动手检查点

### 检查点 1：模型审计脚本

```powershell
python scripts/01_check_model.py
```

预期输出：

模型审计通过
- `$nq` — 13 (匹配)
- `$nv` — 12 (匹配)
- `$nu` — 6 (匹配)
关节: left_hip, left_knee, left_wheel, right_hip, right_knee, right_wheel
执行器: 4 position (left_hip_servo kp=40, left_knee_servo kp=60, ...) + 2 motor

如果看到 `nq 不匹配`，检查 `configs/robot/upkie.json` 和 `assets/upkie/upkie_description/urdf/upkie.urdf` 是否同时更新。

### 检查点 2：关节轴方向验证

```powershell
python -c "
import sys; sys.path.insert(0, 'src')
import mujoco
from upkie_mujoco_course.sim.loader import build_mujoco_model
m = build_mujoco_model()
for i in range(m.njnt):
    jnt_type = int(m.jnt_type[i])
    if jnt_type == 3:  # hinge
        name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i)
        print(f'{name}: axis = {m.jnt_axis[i]}')
"
```

预期：所有铰链关节的轴应为 `[0, 1, 0]`（绕 Y 轴旋转，即矢状面内的前后摆动）。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 07
```

## 可视化证据

在 `outputs/plots/checkpoint_07.png` 中绘制模型结构图：

1. 用 MuJoCo 的 renderer 渲染一张 Upkie 的正面和侧面图。
2. 在图上标注每个 body 的名称和坐标系方向。
3. 用箭头标注每个铰链关节的旋转轴方向。

## 故障诊断挑战

**破坏**：在 Upkie 的 URDF 文件中（`assets/upkie/upkie_description/urdf/upkie.urdf`），把 `left_wheel` 关节的 `axis` 从 `0 1 0` 改成 `0 0 1`（绕 Z 轴而不是 Y 轴旋转）。

**第一处异常**：轮子不再像轮子一样前后滚动，而是像陀螺一样绕垂直轴旋转。在仿真中表现为：给轮端力矩后，机器人的偏航角（yaw）发生变化而不是前进。

**根因假设**：轴方向决定了力矩的施加方向。绕 Z 轴的力矩会让轮子水平旋转，这在物理上不对——真实的 Upkie 轮子是像自行车轮一样前后转的。

**最小修复**：恢复 `axis="0 1 0"`。

**验证**：重新运行仿真，给轮端力矩后机器人应沿 X 方向移动，偏航角不变。

## 三档任务

### 基础任务

- 运行审计脚本，保存审计报告到 `outputs/model_audit/`。
- 手动绘制 MJCF 的 body 树结构图（纸笔或 Mermaid），标注每个 joint 的类型和轴方向。

### 岗位挑战

- 写一个完整的审计脚本，检查以下 10 项并输出 PASS/FAIL：
  1. nq 匹配
  2. nv 匹配
  3. nu 匹配
  4. 所有 hinge joint 的轴方向正确
  5. position actuator 的 kp > 0
  6. motor actuator 的 ctrlrange 对称
  7. 总质量在合理范围（3-8 kg）
  8. 所有 body 的 name 不重复
  9. 所有 joint 的 name 不重复
  10. free joint 存在于根部 body

### 开放探索

- 在 MuJoCo 中加载一个其他机器人的 MJCF/URDF 模型（如 MuJoCo 自带的人体模型），用你的审计脚本分析它的关节结构。
- 比较该模型与 Upkie 的关节数量、自由度数量和执行器数量，写一段 200 字分析。

## 复盘与面试

1. URDF 和 MJCF 的核心区别是什么？

<!-- upkie-qa:07-q1 -->
URDF 只描述运动学结构（关节、连杆、坐标系），是 ROS 生态的通用交换格式；MJCF 在此之上还包含动力学（质量、惯量）、接触（碰撞几何、摩擦系数）和控制（执行器、传感器）的完整定义。换句话说：URDF 回答「机器人长什么样、怎么连接」，MJCF 还要回答「它有多重、怎么碰撞、怎么被驱动」。这也是为什么从 URDF 转 MJCF 后必须补充审计——转换工具无法凭空补全 URDF 里不存在的物理信息。
<!-- /upkie-qa -->

2. 为什么审计不能只检查语法？

<!-- upkie-qa:07-q2 -->
因为一个语法完全正确的 MJCF 可以携带物理上错误的参数——比如关节轴方向反了、某个连杆质量被设成 0、关节活动范围超出机械极限。XML 解析器和 MuJoCo 编译器只保证「文件能被加载」，不管「参数是否符合真实机器人」。审计要做的是语义层检查：把 nq/nv/nu、关节顺序、质量分布、执行器类型逐项与机器人规格对照，任何一项对不上都可能让后面所有关卡建立在错误模型上。
<!-- /upkie-qa -->

3. position actuator 和 motor actuator 的本质区别？

<!-- upkie-qa:07-q3 -->
position actuator 是闭环的：内部自带 PD 控制器，`ctrl` 输入是目标角度，MuJoCo 每步自动计算 `kp*(目标-当前) - kd*速度` 得到力矩；motor actuator 是开环的：`ctrl` 输入直接就是力矩值，没有任何反馈逻辑。如果你把 motor 当 position 用——往 ctrl 里塞目标角度——机器人会得到一个量级完全错误的恒定力矩。用 motor 做位置控制时必须自己在代码里写 PD 逻辑。
<!-- /upkie-qa -->

4. 如果 nq 和配置不一致，第一个可见症状是什么？

<!-- upkie-qa:07-q4 -->
最直接的症状是索引越界：代码按预期布局访问 `qpos[10]`，而实际 nq 更小，直接抛 IndexError。但更危险的是隐蔽情形：索引没越界，只是关节顺序变了，你以为读的是左髋角度，实际读到的是右膝——程序不报错，控制器却在用错误的物理量做决策，表现为机器人行为诡异但日志「一切正常」。这就是为什么本关要求先产出状态向量索引表，再用断言把布局钉死。
<!-- /upkie-qa -->

## 下一关

关卡 `08`（自由基座与空间姿态）会深入讲解 free joint 的四元数表示。本关审计确认了"自由关节贡献 7 维 qpos 和 6 维 qvel"这个事实，下一关将解释为什么四元数是必要的、万向节锁是什么、以及如何在代码中正确转换四元数和欧拉角。
