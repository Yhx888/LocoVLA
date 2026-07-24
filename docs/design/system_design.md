# 44 系统设计与接口评审

> 关卡：44（documentation 工程证据门槛）
> 阶段：岗位毕业项目
> 文档目的：把课程已建成的 MuJoCo 仿真链路、C++/ROS2 控制链路、安全状态机、日志契约串联成可解释的工程系统设计。

本系统由四个独立但耦合的子系统组成：Python 端 MuJoCo 仿真链路（用于策略训练与算法验证）、C++ 端实时控制节点（用于部署）、ROS2 通信中间件（用于解耦节点）、安全状态机与日志契约（用于可审计性）。本文档按"需求 → 接口 → 风险 → 验证证据"四层链路组织，下层为上层提供可验证证据。

---

## 1. 需求层

### 1.1 岗位能力矩阵

课程 v2 用 8 类证据维度组织岗位能力。前 7 类可以由仓库自动核验，`oral_defense` 只能由仓库外部人工答辩判定；本地结果不能自动解锁学习者毕业资格。

| 序号 | 能力类别 | 关卡 | 关卡主题 | 主验证物 |
|---|---|---|---|---|
| 1 | code_tests | 37 | VLA 集成测试 | `tests/test_vla.py` |
| 2 | physical_metrics | 18 | 经典控制实验室 | `tests/test_classical_control_labs.py` |
| 3 | robustness | 31 | RL 鲁棒性 | `tests/test_rl_labs.py` |
| 4 | realtime | 42 | 实时性与时序 | `test_log_contract.cpp` + `test_engineering_42.py` |
| 5 | safety | 43 | 安全状态机 | `test_safety_state_machine.cpp` |
| 6 | documentation | 44 | 设计文档评审 | `test_design_docs.py` |
| 7 | design_review | 46 | 故障演练 | `test_fault_drill.py` |
| 8 | oral_defense | 47 | 代码评审与答辩 | 外部答辩记录；`test_code_review.py` 仅验证本地准备材料 |

每类工程证据有独立的通过条件（pytest 通过 + 专属实验 `passed=true` + portfolio 报告存在），不允许互相替代。上述自动条件不适用于 `oral_defense`。

### 1.2 毕业门槛

`graduation_gates.json` 汇总 8 类证据维度，规则如下：

- 自动流程只计算 7 类工程证据的 `course_engineering_ready`；
- `oral_defense.passed` 在仓库内始终为 `false`，`learner_graduated` 与 `overall_passed` 也始终为 `false`；
- 本文档与 `interface_contract.md` 只能满足 `documentation` 工程证据，不能替代外部口头答辩；
- 任何内联 JSON、本地签名文件或自动代码评审都不能把 `oral_defense` 改为通过。

`graduation_gates.json` 的更新由 `scripts/46_*` 系列脚本读取实验结果后写回，不允许人工手改 JSON 字段。

### 1.3 安全要求

安全是本系统不可妥协的硬约束，所有控制逻辑必须先满足安全要求再追求性能：

- **安全状态机五状态**：`BOOT → SELF_CHECK → DISARMED → ARMED → FAULT`。系统上电即进入 BOOT，禁止直接输出力矩。
- **俯仰角安全阈值**：`|pitch| < 0.3 rad`（约 17.2°）。任何状态下若 `|pitch| ≥ 0.3 rad`，立即转入 FAULT。
- **急停 `/estop`**：触发后立即转 FAULT，所有执行器输出强制归零，时延不超过一个控制周期（10ms）。
- **FAULT 恢复**：必须人工调用 `/reset` 服务才能从 FAULT 回到 BOOT，禁止自动恢复，避免振荡型故障反复重启。
- **力矩门控**：仅 ARMED 状态输出 PD 力矩，BOOT/SELF_CHECK/DISARMED/FAULT 四种状态强制输出零力矩。
- **NaN 防御**：IMU 数据出现 NaN 时立即转 FAULT，不允许 NaN 进入控制律。

---

## 2. 接口层

### 2.1 MuJoCo 仿真链路（Python 端，关卡 06-37）

Python 仿真链路承担策略训练、算法验证、教学演示三类任务，与 C++ 部署链路在数学上等价但运行环境不同。

**模型配置**（`configs/robot/upkie.json`）：

| 字段 | 值 | 说明 |
|---|---|---|
| `nq` | 13 | 广义坐标维数，含 7 维根部自由基座（quaternion × position） |
| `nv` | 12 | 广义速度维数，含 6 维根部速度 |
| `nu` | 6 | 执行器数量 |
| 根部类型 | `root` | 真实自由基座，无控制时允许位移和跌倒 |

**关节清单**（顺序即 `qpos`/`qvel` 索引顺序）：

1. `left_hip`（左髋）
2. `left_knee`（左膝）
3. `left_wheel`（左轮）
4. `right_hip`（右髋）
5. `right_knee`（右膝）
6. `right_wheel`（右轮）

**执行器配置**：

| 执行器 | 类型 | 单位 | 范围 |
|---|---|---|---|
| left_hip / right_hip / left_knee / right_knee | 位置执行器 | rad | 不限 |
| left_wheel / right_wheel | 力矩执行器 | N·m | `[-1.0, 1.0]` |

> 注意：轮端不再使用速度控制语义，自关卡 09 模型契约刷新后统一为力矩执行器。

**控制器栈**：

- **PD 控制器**：`Kp=3.0`，`Kd=0.8`，目标力矩 `τ = 3.0*pitch + 0.8*pitch_rate`，限幅 `±1.0 N·m`。
- **LQR 控制器**：基于线性化倒立摆模型，权重矩阵在 `configs/control/lqr.json` 中维护。
- **残差 RL**：在 PD 基线上叠加策略网络输出，公式 `τ = τ_PD + clip(π(s), -0.3, 0.3)`，残差限幅防止策略覆盖安全边界。

**环境接口**：

- 框架：Gymnasium
- 仿真步长：100Hz（dt=0.01s）
- 观测空间：18 维（关节位置、速度、根部姿态）
- 动作空间：6 维连续 `[-1, 1]^6`
- 配置文件：`configs/env/standing.json`、`configs/env/velocity.json`

### 2.2 C++ 控制链路（关卡 38-41）

C++ 链路是 ROS2 节点的核心，承担实时控制律计算与安全检查。

**入口文件**：`ros2_ws/src/upkie_control/src/control_node.cpp`

**数学库**：`control_math.hpp/cpp`，提供三个纯函数：

| 函数 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `quaternion_to_pitch` | `geometry_msgs/Quaternion` | `double`（rad） | 由四元数提取俯仰角，ZYX 顺序 |
| `clamp_torque` | `double raw, double limit` | `double` | 限幅到 `[-limit, limit]` |
| `orientation_covariance_valid` | `std::array<double,9>` | `bool` | 检查协方差矩阵无 NaN 且非全零 |

**PD 控制律**（与 Python 端数值一致）：

```
raw_torque = 3.0 * pitch + 0.8 * pitch_rate;
clamped_torque = clamp_torque(raw_torque, 1.0);
```

**轮端力矩符号约定**：

- 左轮：`+1.0`（正向力矩使轮子前转）
- 右轮：`-1.0`（坐标系镜像，需取反）

符号约定在 `control_node.cpp` 的 `publish_wheel_torque` 中硬编码，不允许通过参数修改，避免运行期符号错配。

**实时性约束**：

- 单次控制循环预算：10ms
- IMU 数据新鲜度阈值：20ms（两个周期）
- 超过预算即记 `loop_cycle_ms` 字段，连续 3 次超阈值触发性能告警（不直接 FAULT）。

### 2.3 ROS2 部署链路（关卡 40-43）

ROS2 中间件解耦控制节点与传感器/执行器，所有跨节点通信走话题或服务，禁止共享内存。

**话题输入**：

| 话题 | 类型 | QoS | 频率 | 发布方 |
|---|---|---|---|---|
| `/imu` | `sensor_msgs/Imu` | SensorDataQoS | 100Hz | IMU 驱动节点 |

**话题输出**：

| 话题 | 类型 | QoS | 频率 | 订阅方 |
|---|---|---|---|---|
| `/wheel_torque` | `std_msgs/Float64MultiArray` | 默认 QoS | 100Hz | 轮端驱动节点 |
| `/safety_state` | `std_msgs/String` | 默认 QoS | 每个控制 tick（100Hz） | 监控/日志节点 |

`/wheel_torque.data` 数组语义：`[left_torque, right_torque]`，顺序固定，长度恒为 2。

`/safety_state.data` 取值：`"BOOT"` / `"SELF_CHECK"` / `"DISARMED"` / `"ARMED"` / `"FAULT"` 五选一。

**服务**：

| 服务 | 类型 | 请求 | 响应 | 触发动作 |
|---|---|---|---|---|
| `/estop` | `std_srvs/Trigger` | 空 | `success: bool, message: string` | 立即转 FAULT，输出零力矩 |
| `/arm` | `std_srvs/Trigger` | 空 | `success: bool, message: string` | DISARMED→ARMED（前置条件全部满足时） |
| `/reset` | `std_srvs/Trigger` | 空 | `success: bool, message: string` | FAULT→BOOT |

服务响应 `success=false` 时 `message` 字段说明失败原因（如"当前状态非 DISARMED，无法 arm"）。

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `record_timing` | `bool` | `false` | 是否记录时序数据 |
| `record_timing_path` | `string` | `~/upkie-logs/timing.csv` | 时序文件路径 |
| `record_log` | `bool` | `true` | 是否启用日志契约 |
| `log_path` | `string` | `~/upkie-logs/control.jsonl` | 日志文件路径 |
| `episode_id` | `int` | `0` | 实验回合 ID，写入日志 |
| `pitch_safety_limit` | `double` | `0.3` | 俯仰角安全阈值（rad） |

`pitch_safety_limit` 虽然可配，但编译期常量 `PITCH_SAFETY_LIMIT_RAD = 0.3` 作为兜底，参数值大于 0.5 时节点启动报错退出。

**定时器周期**：10ms（100Hz），由 `rclcpp::create_wall_timer` 创建。

**部署环境**：

- 操作系统：WSL2 Ubuntu 24.04
- ROS2 版本：Jazzy Jalisco
- 构建工具：colcon
- 构建产物路径：`~/upkie-ros2-build/`
- 启动命令：`ros2 run upkie_control control_node`

### 2.4 安全状态机（关卡 43）

安全状态机是所有控制输出的最后一道闸门，独立于控制律实现，确保任何控制律异常都不能绕过安全约束。

**模块文件**：`safety_state_machine.hpp/cpp`

**状态枚举**（`uint8_t`）：

| 状态 | 值 | 含义 |
|---|---|---|
| `BOOT` | 0 | 上电初始状态，等待自检 |
| `SELF_CHECK` | 1 | 自检进行中 |
| `DISARMED` | 2 | 自检通过，待 arm |
| `ARMED` | 3 | 唯一允许输出力矩的状态 |
| `FAULT` | 4 | 故障锁定，输出零力矩 |

**状态转换规则**：

| 起始状态 | 目标状态 | 触发条件 |
|---|---|---|
| BOOT | SELF_CHECK | 自动（启动后立即转换） |
| SELF_CHECK | DISARMED | 传感器新鲜 + 无 NaN + 通信正常 |
| SELF_CHECK | FAULT | 自检超时（5s）或传感器异常 |
| DISARMED | ARMED | 传感器新鲜 + `|pitch|<0.3` + 急停释放 + 显式 `/arm` |
| DISARMED | FAULT | NaN / 通信失联 / `|pitch|≥0.3` / 急停触发 |
| ARMED | FAULT | NaN / 通信失联 / `|pitch|≥0.3` / 急停触发 |
| ARMED | DISARMED | 显式 disarm（预留，当前未实现） |
| FAULT | BOOT | 仅显式 `/reset` |

**编译期常量**：

```cpp
constexpr double PITCH_SAFETY_LIMIT_RAD = 0.3;
constexpr double IMU_FRESHNESS_TIMEOUT_MS = 20.0;
constexpr double SELF_CHECK_TIMEOUT_S = 5.0;
```

**力矩门控逻辑**：

```cpp
double gated_torque = (state_ == ARMED) ? clamped_torque : 0.0;
```

门控发生在 `clamp_torque` 之后、`publish_wheel_torque` 之前，确保限幅与门控顺序固定。

### 2.5 日志契约（关卡 42）

日志契约保证每次控制循环的输出可被离线分析脚本无歧义解析，是实时性验证（关卡 42）与故障演练（关卡 46）的数据基础。

**模块文件**：`log_contract.hpp/cpp`

**字段清单**（9 字段 JSON lines，每行一个完整 JSON 对象）：

| 字段 | 类型 | 单位 | 说明 |
|---|---|---|---|
| `timestamp_ns` | `uint64` | ns | steady_clock 时间戳，单调递增 |
| `episode_id` | `int` | - | 实验回合 ID |
| `git_commit` | `string` | - | 构建时的 git commit hash |
| `pitch_rad` | `double` | rad | 俯仰角 |
| `pitch_rate_rad_s` | `double` | rad/s | 俯仰角速度 |
| `raw_torque_common_nm` | `double` | N·m | 限幅前力矩（公共值） |
| `clamped_torque_common_nm` | `double` | N·m | 限幅后力矩（公共值） |
| `safety_flag` | `uint8` | - | 0/1/2/3 |
| `loop_cycle_ms` | `double` | ms | 本次循环耗时 |

**`safety_flag` 含义**：

| 值 | 含义 |
|---|---|
| 0 | 正常 |
| 1 | 协方差无效 |
| 2 | 力矩饱和（`raw != clamped`） |
| 3 | FAULT 状态 |

`safety_flag` 是位标志的简化版，同一时刻只记录最高优先级（FAULT > 协方差无效 > 力矩饱和 > 正常）。

**单调性约束**：`timestamp_ns` 严格递增，相等即视为乱序，分析脚本返回 `false`。

**失效字段拒绝规则**：

- 缺失 9 字段中任一字段 → 分析脚本退出码 1；
- `timestamp_ns` 出现倒退或相等 → 分析脚本退出码 1；
- 字段类型不符（如 `pitch_rad` 为字符串）→ 分析脚本退出码 1；
- 任一行解析失败 → 整个文件视为不可信，退出码 1。

**文件路径**：由参数 `log_path` 指定，默认 `~/upkie-logs/control.jsonl`，按 `episode_id` 切分文件。

---

## 3. 风险层

### 3.1 故障模式与影响分析（FMEA）

下表列出 8 种典型故障模式，按"故障现象 → 第一处异常证据 → 检测延迟 → 制动延迟 → 最终状态 → 纠正动作"六列展开。

| 编号 | 故障模式 | 故障现象 | 第一处异常证据 | 检测延迟 | 制动延迟 | 最终状态 | 纠正动作 |
|---|---|---|---|---|---|---|---|
| F-01 | IMU 断流 | `/imu` 话题停发 | IMU 数据时间戳超过 20ms 新鲜度阈值 | ≤10ms（一个周期） | ≤10ms | FAULT | 检查 IMU 驱动节点，重启驱动或 `/reset` |
| F-02 | 时间戳倒退 | `timestamp_ns` 非单调 | 日志分析脚本检测到 `t[i] ≤ t[i-1]` | 离线（事后分析） | - | 不影响运行态，但日志判废 | 排查 steady_clock 是否被系统时间漂移污染；重启节点 |
| F-03 | 协方差无效 | `orientation_covariance` 全零或含 NaN | `orientation_covariance_valid` 返回 `false` | ≤10ms | ≤10ms | DISARMED→FAULT（若 ARMED） | `safety_flag=1`；检查 IMU 校准；触发 `/reset` 后重新自检 |
| F-04 | 力矩饱和 | PD 输出超过 ±1.0 N·m | `raw_torque_common_nm != clamped_torque_common_nm` | 即时（同周期记录） | - | 不触发 FAULT，但 `safety_flag=2` | 检查 PD 增益；降低参考姿态；若持续饱和考虑降速 |
| F-05 | 左右轮符号互换 | 机器人原地打转而非前进 | `wheel_torque[0]` 与 `wheel_torque[1]` 同号 | 离线（录像分析） | - | 不自动检测，依赖人工 | 检查 `control_node.cpp` 中符号硬编码；运行 `test_wheel_sign.py` |
| F-06 | CPU 过载 | 控制循环耗时超过 10ms | `loop_cycle_ms > 10.0` | ≤10ms | - | 连续 3 次超阈值记告警，不 FAULT | 降低日志写入频率；隔离 CPU 核心；排查其他进程抢占 |
| F-07 | 高层命令失联 | 上游指令节点停止发布 | 当前无自动检测（预留） | - | - | 不影响 ARMED 状态保持 | 降级到 PD 保持当前姿态；预留 watchdog 后续关卡实现 |
| F-08 | NaN 检测 | IMU 数据含 NaN | `std::isnan(pitch)` 或 `std::isnan(pitch_rate)` | ≤10ms | ≤10ms | FAULT | `safety_flag=3`；必须 `/reset`；排查 IMU 硬件或驱动 |

**FMEA 优先级排序**（按"严重度 × 检测难度"）：

1. F-05（符号互换）：严重度高（直接导致机器人失控），检测难度高（无自动检测），优先级最高。
2. F-01（IMU 断流）：严重度高，检测难度低（已有新鲜度检查）。
3. F-08（NaN）：严重度高，检测难度低。
4. F-03（协方差无效）：严重度中，检测难度低。
5. F-04（力矩饱和）：严重度低，检测难度低。
6. F-06（CPU 过载）：严重度中，检测难度中。
7. F-02（时间戳倒退）：严重度低（仅影响日志），检测难度低。
8. F-07（命令失联）：严重度中，检测难度高（无 watchdog），预留后续关卡。

### 3.2 风险矩阵

按"严重度 × 发生概率"评级，分高/中/低三档。

| 编号 | 故障模式 | 严重度 | 发生概率 | 风险等级 |
|---|---|---|---|---|
| F-01 | IMU 断流 | 高 | 中 | **高** |
| F-02 | 时间戳倒退 | 低 | 低 | 低 |
| F-03 | 协方差无效 | 中 | 中 | **中** |
| F-04 | 力矩饱和 | 低 | 高 | **中** |
| F-05 | 左右轮符号互换 | 高 | 低 | **高** |
| F-06 | CPU 过载 | 中 | 中 | **中** |
| F-07 | 高层命令失联 | 中 | 低 | 低 |
| F-08 | NaN 检测 | 高 | 低 | **中** |

**风险等级分布**：

- 高风险：F-01、F-05（2 项）—— 必须有自动检测与制动，F-05 需补单元测试。
- 中风险：F-03、F-04、F-06、F-08（4 项）—— 已有检测或仅影响日志，无需新增制动。
- 低风险：F-02、F-07（2 项）—— F-02 离线分析即可，F-07 预留 watchdog。

** mitigation 优先级**：F-05 > F-01 > F-08 > F-03 > F-04 > F-06 > F-02 > F-07。

---

## 4. 验证证据层

### 4.1 测试矩阵

每个关卡对应一个或多个测试文件，测试通过是门槛 `passed=true` 的必要条件。

| 关卡 | 测试文件 | 测试类型 | 通过条件 |
|---|---|---|---|
| 37 | `tests/test_vla.py` | pytest | VLA 集成用例全部通过 |
| 18 | `tests/test_classical_control_labs.py` | pytest | PD/LQR 实验室全部通过 |
| 31 | `tests/test_rl_labs.py` | pytest | RL 鲁棒性指标达标 |
| 42 | `test_log_contract.cpp` + `test_engineering_42.py` | C++ gtest + pytest | 日志契约 9 字段全部通过 + Python 侧实时性分析通过 |
| 43 | `test_safety_state_machine.cpp` | C++ gtest | 五状态转换全部覆盖 |
| 44 | `test_design_docs.py` | pytest | 本文档与 `interface_contract.md` 字段齐全 |
| 46 | `test_fault_drill.py` | pytest | 8 种故障演练全部通过 |
| 47 | `test_code_review.py` | pytest | 代码评审检查清单全部通过 |

C++ 测试由 colcon 编译后执行，Python 测试由 pytest 直接执行。两类测试结果统一写入 `outputs/results/engineering_*.json`。

### 4.2 实验结果

所有关卡的实验结果统一写入 `outputs/results/engineering_{N}.json`，遵循统一结果契约：

```json
{
  "chapter_id": 42,
  "passed": true,
  "metrics": {
    "loop_cycle_ms_p99": 8.7,
    "log_fields_valid": 9,
    "log_monotonic": true
  },
  "pass_conditions": [
    "loop_cycle_ms_p99 < 10.0",
    "log_fields_valid == 9",
    "log_monotonic == true"
  ]
}
```

**已规划结果文件清单**：

| 文件 | 关卡 | 关键 metrics 字段 |
|---|---|---|
| `engineering_38.json` | 38 | C++ 节点启动成功、话题发布频率 |
| `engineering_39.json` | 39 | 数学库函数单元测试覆盖率 |
| `engineering_41.json` | 41 | PD 力矩数值与 Python 端一致性误差 |
| `engineering_42.json` | 42 | `loop_cycle_ms_p99`、`log_fields_valid`、`log_monotonic` |
| `engineering_43.json` | 43 | 状态转换覆盖率、FAULT 触发延迟 |
| `engineering_44.json` | 44 | 本文档字段齐全、接口契约字段齐全 |
| `engineering_45.json` | 45 | portfolio 报告存在性 |
| `engineering_46.json` | 46 | 8 种故障演练通过数 |
| `engineering_47.json` | 47 | 代码评审检查项通过数 |

`passed` 字段由 `pass_conditions` 中所有条件求值后取逻辑与得到，不允许人工覆盖。

### 4.3 毕业门槛映射

8 类门槛 → 关卡 → 通过条件的完整映射：

| 门槛类别 | 关卡 | 通过条件 |
|---|---|---|
| code_tests | 37 | `pytest tests/test_vla.py` 通过 + `engineering_37.json` 的 `passed=true` |
| physical_metrics | 18 | `pytest tests/test_classical_control_labs.py` 通过 + `engineering_18.json` 的 `passed=true` |
| robustness | 31 | `pytest tests/test_rl_labs.py` 通过 + `engineering_31.json` 的 `passed=true` |
| realtime | 42 | `colcon test` 通过 `test_log_contract.cpp` + `pytest test_engineering_42.py` 通过 + `engineering_42.json` 的 `passed=true` |
| safety | 43 | `colcon test` 通过 `test_safety_state_machine.cpp` + `engineering_43.json` 的 `passed=true` |
| documentation | 44 | `pytest tests/test_design_docs.py` 通过 + `engineering_44.json` 的 `passed=true` + portfolio 报告 `docs/portfolio/report.md` 存在 |
| design_review | 46 | `pytest tests/test_fault_drill.py` 通过 + `engineering_46.json` 的 `passed=true`（8 种故障演练全过） |
| oral_defense | 47 | 仓库外部真人答辩与独立评审；本地 `test_code_review.py`、`engineering_47.json` 和答辩材料只证明答辩入口就绪 |

`graduation_gates.json` 的更新流程：

1. 各关卡脚本运行后写入 `engineering_{N}.json`；
2. 验收脚本读取所有 `engineering_*.json`，按映射表核验 7 类自动工程证据；
3. 写回 `graduation_gates.json`，同时保持 `oral_defense.passed=false`；
4. 7 类自动证据全部通过时只能得到 `course_engineering_ready=true`，`overall_passed` 与 `learner_graduated` 仍为 `false`。

**本文档完成后**：`documentation` 维度具备被自动核验的输入，并可继续关卡 45（portfolio）与关卡 46（故障演练）。这不产生学习者毕业结论。
