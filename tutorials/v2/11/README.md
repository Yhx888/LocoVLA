# 11 可替换机器人模型契约

> 建设状态：可执行  
> 阶段：机器人仿真  
> 作品集目录：`outputs/portfolio/11`  
> 本关产物：一份可复查的机器人模型契约审计报告

## 岗位任务：接收一台“能加载”的新机器人

你所在的运动控制团队准备把 Upkie 换成另一台双轮足机器人。供应方交来的 URDF 可以被 MuJoCo 打开，画面也没有明显异常，但这还远远不够。控制器需要确认：状态数组的长度和顺序是否一致、根节点是否真的能自由运动、轮端输入到底是速度还是力矩、左右轮正方向是否相反、传感器字段是否完整。

任何一项含糊，都可能造成一种很危险的假象：程序和测试能运行，机器人却在执行错误的物理命令。本关的岗位交付物不是“模型截图”，而是一个能自动拒绝语义错误模型的替换契约。

## 学习目标

完成本关后，你应当能够：

- 用自己的话解释“文件能加载”和“模型可替换”为什么不是同一件事；
- 从自由基座和六个受控关节推导 `nq=13, nv=12, nu=6`；
- 解释轮端 `torque / N*m / [-1, 1]` 三个字段各自约束什么；
- 运行正常审计和故障注入，根据第一项失败检查定位配置根因；
- 把审计结果、日志、图表和自动测试整理为作品集证据。

## 前置关卡

建议先完成 `06-10`。如果你已经熟悉 MuJoCo，可以先回答下面三个诊断问题：

1. 为什么自由基座的位置用 7 个数表示，而速度只用 6 个数？
2. `1 rad/s` 与 `1 N*m` 为什么不能送进同一个轮端接口？
3. 为什么左右轮在机械镜像安装时通常需要相反的方向系数？

三个问题都能解释清楚，并不代表可以跳过自动审计；它只允许你跳过部分概念阅读。

## 先观察现象

先不要修改任何文件，运行一个“轮端语义被写成速度”的故障：

```powershell
python scripts/11_model_contract_lab.py --inject-fault wheel_semantics
```

命令会以非零状态退出，这是预期现象。真实运行得到：

contract_check_ratio: 0.9166666666666666
failed_check_count: 1.0
模型契约审计未通过

此时模型的 `nq`、`nv`、`nu` 都没有变化，画面也仍然能渲染。唯一失败项是 `wheel_torque_semantics`。这说明模型替换最难发现的问题往往不是“文件损坏”，而是“同一个数字被双方理解成不同物理量”。

## 直觉与概念

<!-- upkie-animation:11-core -->

### 契约像插头标准，但还要规定电压

把机器人模型想成一台要接入控制系统的设备。关节名和数组长度类似插头形状；单位、方向和限幅类似电压与极性。插头能插进去，只能证明形状兼容，不能证明通电后安全。

在本课程里，`RobotSpec` 是解析后的接口说明，`MjModel` 是实际编译出的物理模型，`upkie.json` 是人和工具共同阅读的事实源。三者必须互相印证，而不是只信任其中一个。

## 契约数据流

<div style="margin:16px 0;font-size:15px;font-family:inherit">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1448 432" style="max-width:100%;height:auto;display:block">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#64748b"/>
</marker>
<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
  <path d="M0,1 L9,5 L0,9" fill="#d36b27"/>
</marker>
</defs>
<rect x="16" y="12" width="158" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="95.0" y="32" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="95.0" dy="0">upkie.json</tspan>
<tspan x="95.0" dy="22">字段、单位、限幅</tspan>
</text>
<rect x="216" y="12" width="116" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="274.5" y="32" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="274.5" dy="0">RobotSpec</tspan>
<tspan x="274.5" dy="22">类型化配置</tspan>
</text>
<rect x="417" y="172" width="170" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="501.8" y="192" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="501.8" dy="0">MjModel</tspan>
<tspan x="501.8" dy="22">nq=13 nv=12 nu=6</tspan>
</text>
<rect x="617" y="92" width="106" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="669.7" y="112" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="669.7" dy="0">契约审计</tspan>
<tspan x="669.7" dy="22">12 项检查</tspan>
</text>
<rect x="817" y="92" width="143" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="888.7" y="112" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="888.7" dy="0">result.json</tspan>
<tspan x="888.7" dy="22">指标与通过条件</tspan>
</text>
<rect x="817" y="172" width="143" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="888.7" y="192" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="888.7" dy="0">log.json</tspan>
<tspan x="888.7" dy="22">逐项检查与根因</tspan>
</text>
<rect x="817" y="252" width="137" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="885.6" y="272" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="885.6" dy="0">plot.png</tspan>
<tspan x="885.6" dy="22">通过/失败概览</tspan>
</text>
<rect x="1218" y="92" width="140" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="1288.0" y="112" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="1288.0" dy="0">作品集证据</tspan>
<tspan x="1288.0" dy="22">可追溯 commit</tspan>
</text>
<rect x="1018" y="332" width="162" height="52" rx="6" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>
<text x="1098.5" y="352" text-anchor="middle" fill="#1e293b" font-size="15" font-family="inherit">
<tspan x="1098.5" dy="0">控制循环</tspan>
<tspan x="1098.5" dy="22">100 Hz, 轮端 N·m</tspan>
</text>
<line x1="174" y1="38" x2="216" y2="38" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="174,38 395,38 395,118 617,118" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="333,38 475,38 475,118 617,118" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="587,198 602,198 602,118 617,118" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="723" y1="118" x2="817" y2="118" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="723,118 770,118 770,198 817,198" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="723,118 770,118 770,278 817,278" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<line x1="960" y1="118" x2="1218" y2="118" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="587,198 802,198 802,358 1018,358" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#a)"/>
<polyline points="1099,358 587,198" fill="none" stroke="#d36b27" stroke-width="1.5" stroke-dasharray="5,3.5" marker-end="url(#ad)"/>
<text x="1159" y="350" text-anchor="middle" fill="#d36b27" font-size="13" font-family="inherit">安全边界: ±1 N·m</text>
</svg></div>

模块职责不能混在一起：加载器负责构建模型，审计器负责判断契约，实验入口负责保存证据。这样一来，即使以后换成 MJCF，审计标准仍然不依赖命令行界面。

## 十二项契约逐项拆解

| 检查项 | 当前要求 | 它防止的错误 |
|---|---|---|
| `schema_version_v2` | `2.0` | 新旧字段被静默混用 |
| `state_dimensions` | `13 / 12 / 6` | 控制器切片错位 |
| `floating_base` | 必须为真 | 机器人被钉在空中 |
| `root_joint` | 唯一自由关节名为 `root` | 根状态读取错误 |
| `controlled_joint_mapping` | 六个关节全部存在 | 命令发给不存在的关节 |
| `actuator_count` | 四个位置、两个力矩 | 执行器数量或类型不一致 |
| `wheel_torque_semantics` | `torque`, `N*m` | 把速度当力矩 |
| `wheel_torque_limit` | `[-1, 1] N*m` | 配置限幅与模型限幅不同 |
| `opposite_wheel_directions` | 一正一负 | 前进命令变成原地转向 |
| `normalized_base_quaternion` | 范数为 1 | 非法姿态表示 |
| `sensor_contract_fields` | 六类状态字段齐全 | 估计器输入缺失 |
| `positive_timestep` | `dt>0`, `frame_skip>0` | 无效离散时间 |

这 12 项是当前课程的最低公共契约，不是所有机器人的完整安全标准。真实产品还需要质量、惯量、碰撞几何、自碰撞、时延、温升和通信失效等审计。

## 教科书级展开

### 展开一：为什么 `nq` 不等于 `nv`

### 1. 符号与单位

- `q`：广义位置，包含位置、姿态和关节角；位置单位为 m，角度单位为 rad，四元数无量纲；
- `v`：广义速度，包含线速度、角速度和关节速度；单位分别为 m/s 与 rad/s；
- `u`：执行器输入，本模型含四个腿部目标角和两个轮端力矩；单位分别为 rad 与 N*m；
- `nq`、`nv`、`nu`：三个向量的元素数，都是无量纲整数。

### 2. 不跳步推导

自由基座在三维空间有三维位置：

- `$p_base` — [x, y, z]，共 3 个数

姿态用单位四元数表示：

- `$q_base` — [qw, qx, qy, qz]，共 4 个数

机器人还有 6 个单自由度关节，因此：

nq = 3 + 4 + 6 = 13

速度不直接使用“四元数每个分量的变化率”，而用三维角速度表示基座转动：

- `$nv` — 3 个线速度 + 3 个角速度 + 6 个关节速度 = 12

最后，四个腿部执行器加两个轮端执行器：

$$
\nu = 4 + 2 = 6
$$

所以 `nq != nv` 不是异常，而是三维旋转表示的结果。若代码默认二者相等，根姿态后的所有关节索引都会错一位。

### 3. 假设、范围与失效条件

上述推导假设模型有一个三维自由基座、六个单自由度关节，并使用单位四元数。固定基座模型、平面模型、多自由度关节或不同姿态参数化都会改变维度，不能硬套 `13/12/6`。

### 展开二：轮端力矩语义

轮端命令经过对称限幅：

$$
tau_{\text{applied}} = clip(tau_{\text{command}}, -1, 1) N \cdot m
$$

假设 `tau_command=1.4 N*m`，则实际输入为 `1.0 N*m`；若命令为 `-0.3 N*m`，实际输入仍为 `-0.3 N*m`。这里的限幅保护仿真和实机接口，也让 PD、LQR、MPC、RL 与 FOC 使用同一种可解释的动作语义。

速度 `rad/s` 描述“转得多快”，力矩 `N*m` 描述“施加多大的转动作用”。二者量纲不同，不能靠调一个比例系数就把接口错误变成正确。若底层设备是速度环，应显式增加“力矩到速度目标”的适配层，并重新定义闭环和安全边界。

左右轮方向系数为 `[1, -1]`。它来自镜像安装的关节轴方向：相同的机器人前进意图，需要映射为模型坐标下符号相反的轮端转动。这个约定只适用于当前 URDF；换模型时必须根据关节轴和实测运动重新审计。

### 展开三：把十二项检查合成一个结论

令第 `i` 项检查结果为：

- `$I_i` — 1（通过）或 0（失败）

总通过条件是逻辑“与”：

$$
passed = I_{1} AND I_{2} AND \dots AND I_{12}
check_{\text{ratio}} = (I_{1} + I_{2} + \dots + I_{12}) / 12
$$

正常配置中 12 项全部通过，所以 `check_ratio=12/12=1.0`。故障示例只有 11 项通过，因此 `11/12=0.916666...`。注意：比例不是安全分数。即使达到 91.7%，只要轮端单位错误，模型仍必须被拒绝。

## 代码映射

核心数据流可以缩写为下面 15 行：

```python
raw_config = load_json_config("configs/robot/upkie.json")
spec = load_robot_spec()
model = build_mujoco_model(spec)
audit = audit_robot_contract(model, spec, raw_config)

write_experiment_result(
    result_path,
    chapter_id="11",
    seed=0,
    config={"robot": raw_config["name"]},
    metrics=audit["metrics"],
    pass_conditions={
        "contract_check_ratio": {"operator": "==", "value": 1.0},
        "failed_check_count": {"operator": "==", "value": 0.0},
    },
)
```

输入是原始 JSON、类型化 `RobotSpec` 和编译后的 `MjModel`；输出是包含逐项布尔值、量化指标和诊断细节的字典。构建模型会读取资产文件，实验函数还会写入 `outputs/`，这两处是显式副作用。未知故障类型会抛出 `ValueError`，契约失败则由脚本以非零退出码传给自动化系统。

## 动手检查点一：生成专属审计证据

在项目根目录运行：

```powershell
python scripts/11_model_contract_lab.py
```

本项目真实输出为：

nq: 13.0
nv: 12.0
nu: 6.0
free_joint_count: 1.0
controlled_joint_count: 6.0
wheel_torque_limit_nm: 1.0
contract_check_ratio: 1.0
failed_check_count: 0.0
模型契约审计通过

## 可视化证据

正常实验生成以下三重证据：

- 视觉：`outputs/plots/model_contract_11.png`，12 根横条应全部为绿色的 1；
- 日志：`outputs/logs/model_contract_11.json`，`failed_checks` 应为空列表；
- 结果：`outputs/results/model_contract_11.json`，`passed` 应为 `true`；
- 作品集：`outputs/portfolio/11/evidence.json`，汇总指标和证据路径。

## 动手检查点二：运行自动验收

```powershell
python scripts/course_checkpoint.py --chapter 11
```

该命令会真实执行 `tests/test_model_contract.py`，并生成：

```text
outputs/results/checkpoint_11.json
outputs/logs/checkpoint_11.log
outputs/plots/checkpoint_11.png
```

只有专属审计和自动测试都通过，才能把本关证据视为完整。

## 故障诊断挑战

下面两种失败都要求按“现象 -> 第一项失败检查 -> 配置根因 -> 修复后复测”记录。

### 失败一：`wheel_torque_semantics` 为假

先看 `outputs/logs/model_contract_11_wheel_semantics.json`。如果只有该项失败，检查：

```json
"wheel": {"command": "torque", "unit": "N*m", "limit": [-1.0, 1.0]}
```

不要通过删除该检查或把阈值改成 `0.9` 来“修复”。根因是接口定义错误。

### 失败二：`opposite_wheel_directions` 为假

运行：

```powershell
python scripts/11_model_contract_lab.py --inject-fault wheel_direction
```

真实结果同样是 `check_ratio=0.916666...`，但日志中的失败项变为 `opposite_wheel_directions`。此时应检查 URDF 关节轴、左右轮安装方向和前进实测，而不是盲目交换控制器输出。

故障练习写入 `fault_wheel_semantics.json` 或 `fault_wheel_direction.json`，不会覆盖正常通过的 `evidence.json`。

## 三档任务

### 基础任务

运行两个检查点，指出 12 项检查各读取了配置、`RobotSpec` 还是 `MjModel` 的什么事实，并解释 `nq=13, nv=12`。

### 岗位挑战

复制一份机器人配置作为候选模型，至少修改三项契约。每次只保留一个故障，记录“第一项异常证据 -> 根因 -> 修复 -> 复测”，不要一次修改多个变量后猜测原因。

### 开放探索

为另一台轮足机器人设计 v2 配置草案。允许维度不同，但必须明确哪些契约是课程通用约束，哪些是 Upkie 专属常量，并为新增字段写出可自动判定的通过条件。

## 专业里程碑

完成本关后，你获得的不是“又跑通一个脚本”，而是一项真实的模型接入能力：能在控制算法运行前，用证据阻断维度、单位、方向和限幅错误。作品集可以展示正常审计图、一个故障日志和一页根因复盘。

## 复盘与面试

1. 为什么 `nq` 与 `nv` 不相等？回答时必须提到四元数和三维角速度。

<!-- upkie-qa:11-q1 -->
自由基座的姿态在 `qpos` 里用四元数表示，占 4 个数；而它的旋转速率在 `qvel` 里用三维角速度表示，只占 3 个数。四元数多出的那 1 维被「模长等于 1」的归一化约束消掉，真实旋转自由度仍是 3。所以 Upkie 的自由基座贡献 7 维 qpos（3 平移 + 4 四元数）和 6 维 qvel（3 线速度 + 3 角速度），加上 6 个受控关节后 nq=13、nv=12，永远差 1。审计时把「nq = nv + 1」当作自由基座存在的指纹来验证。
<!-- /upkie-qa -->

2. 模型成功编译为什么不能证明执行器语义正确？

<!-- upkie-qa:11-q2 -->
编译只验证语法和引用完整性：XML 能解析、引用的 body/joint 存在、数值字段合法。但「轮端执行器接收的是力矩还是目标角度」「单位是 N·m 还是 A」这类语义约定，对编译器来说都只是合法的数字。本关的故障注入实验就是证据：把轮端语义改错后模型照样编译、nq/nv/nu 不变、画面仍能渲染，唯一报警的是契约审计的 `wheel_torque_semantics` 检查项。模型替换最难发现的问题往往不是文件损坏，而是同一个数字被双方理解成不同物理量。
<!-- /upkie-qa -->

3. `check_ratio=0.9167` 是否可以上线？为什么比例不能替代关键项门禁？

<!-- upkie-qa:11-q3 -->
不可以。`check_ratio=11/12=0.9167` 只说明「有一项失败」，而不说明失败的是哪一项、后果有多严重。如果失败的是轮端力矩语义，控制器发出的每一个命令都会被错误解释，机器人上电就可能飞车——这不是 8.3% 的小瑕疵，而是 100% 的事故。所以契约门禁必须是「全部通过才放行」（`passed = I1 AND ... AND I12`），比例只能用作诊断进度的参考指标。这和考试不同：安全关键系统里没有「及格线」，只有「零容忍项全部通过」。
<!-- /upkie-qa -->

4. 如果新机器人轮端只能接收电流命令，你会怎样定义从 `N*m` 到 A 的显式接口？还需要哪些电机参数？

<!-- upkie-qa:11-q4 -->
在接口层加一个显式的单位换算函数 `current = torque / (Kt * gear_ratio * eta)`，并把它写进契约：控制器侧统一用 N·m，驱动器侧用 A，换算只在这一处发生、双向可逆。需要的电机参数至少有：转矩常数 Kt（N·m/A，核心参数）、减速比 gear_ratio、传动效率 eta，以及用于限幅的最大连续电流/峰值电流。契约里还应追加一个自动检查项：用额定力矩换算出的电流必须落在电机额定电流范围内，否则参数必有一错。绝对不能把换算系数隐藏在控制器增益里——那会让换电机时所有增益都失效且无从审计。
<!-- /upkie-qa -->

5. 为什么故障练习不能覆盖通过证据？这与实验可追溯性有什么关系？

<!-- upkie-qa:11-q5 -->
因为两者回答的是不同问题：`evidence.json` 证明「正常配置通过全部契约」，`fault_*.json` 证明「审计器能捕获对应故障」。如果故障练习覆盖了通过证据，你就无法同时拿出这两份证明，也无法判断当前磁盘上的结果文件对应哪次运行、哪个配置。可追溯性要求每份证据都能回答「它是在什么条件下产生的」：输入配置、注入的故障类型、commit 版本都要能对得上。这就是为什么故障实验写入独立的 `fault_wheel_semantics.json`，而不是复用正常路径的文件名——同一个原则也适用于训练实验：不同超参数的运行结果必须分开存。
<!-- /upkie-qa -->

## 下一关

关卡 `12` 会把已经审计过的状态、平衡点和轮端力矩接口交给反馈控制器。模型契约解决“控制器面对的对象是否可信”，下一关开始解决“对象偏离目标时，动作应该怎样变化”。
