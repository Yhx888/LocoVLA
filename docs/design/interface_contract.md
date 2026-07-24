# 44 接口契约

> 关卡：44（documentation 毕业门槛）
> 文档目的：列出所有公开接口的契约——话题、服务、参数、消息类型、QoS、单位、限幅、坐标系。

本文档与 `system_design.md` 配套使用。系统设计文档描述"为什么这样设计"，本文档描述"接口长什么样"。任何对接口的修改必须先更新本文档，再修改代码，避免代码与文档脱节。

---

## 1. 话题清单

| 名称 | 类型 | 方向 | QoS | 频率 | 单位 | 范围 | 坐标系 |
|---|---|---|---|---|---|---|---|
| `/imu` | `sensor_msgs/Imu` | 输入（订阅） | `rclcpp::SensorDataQoS()`（BEST_EFFORT + KEEP_LAST + depth=5） | 100Hz | orientation 无单位，angular_velocity 为 rad/s | 四元数模长为 1 | 机身坐标系 |
| `/yaw_rate_command` | `std_msgs/Float64` | 输入（订阅） | 默认 QoS（RELIABLE + KEEP_LAST + depth=10） | 上层按需发布，控制环以 100Hz 读取最新值 | rad/s | 必须为有限值；对应差动力矩受 `yaw_torque_limit` 限制 | 机身 `z` 轴，正值左转 |
| `/wheel_torque` | `std_msgs/Float64MultiArray` | 输出（发布） | 默认 QoS（RELIABLE + KEEP_LAST + depth=10） | 100Hz | N·m | `[-1.0, 1.0]` × 2 | 机身坐标系 |
| `/safety_state` | `std_msgs/String` | 输出（发布） | 默认 QoS（RELIABLE + KEEP_LAST + depth=10） | 每个控制 tick 发布一次（100Hz） | 无（字符串枚举） | 5 种枚举值 | 不适用 |

**话题顺序约定**：

- `/wheel_torque.data` 数组长度恒为 2，顺序固定为 `[left, right]`，不允许调整顺序；
- `/yaw_rate_command.data` 非有限值会触发故障标志，不会覆盖上一帧有效指令；
- `/safety_state.data` 每个控制 tick（100Hz）发布一次当前安全状态字符串，订阅方可直接作为心跳使用；状态变化与未变化均会发布，便于监控节点检测控制节点是否在线。

> 实现位置：`ros2_ws/src/upkie_control/src/control_node.cpp` 的 `control_tick()` 中调用 `safety_state_pub_->publish(state_msg)`（参见该文件第 290-294 行）。

---

## 2. 服务清单

| 名称 | 类型 | QoS | 请求 | 响应 | 触发动作 |
|---|---|---|---|---|---|
| `/estop` | `std_srvs/Trigger` | 默认服务 QoS（RELIABLE + KEEP_LAST + depth=10） | 空 | `success: bool, message: string` | 立即转 FAULT，所有执行器输出归零 |
| `/arm` | `std_srvs/Trigger` | 默认服务 QoS（RELIABLE + KEEP_LAST + depth=10） | 空 | `success: bool, message: string` | DISARMED→ARMED（前置条件全满足时） |
| `/reset` | `std_srvs/Trigger` | 默认服务 QoS（RELIABLE + KEEP_LAST + depth=10） | 空 | `success: bool, message: string` | FAULT→BOOT，重置状态机 |

> 实现位置：`ros2_ws/src/upkie_control/src/control_node.cpp` 构造函数中通过 `create_service<std_srvs::srv::Trigger>("estop"|"arm"|"reset", ...)` 注册三个服务（参见该文件第 146-178 行）。

**服务响应约定**：

- `success=true` 表示状态转换已执行；
- `success=false` 表示前置条件不满足，`message` 字段说明原因，例如：
  - `/arm` 在非 DISARMED 状态调用：`"current state is ARMED, cannot arm"`；
  - `/reset` 在非 FAULT 状态调用：`"current state is DISARMED, reset only allowed from FAULT"`；
  - `/estop` 在任何状态均可成功，返回 `success=true`。

**服务调用语义**：所有服务均为幂等，重复调用 `/estop` 不会产生副作用，重复调用 `/reset` 在非 FAULT 状态返回 `success=false`。

---

## 3. 参数清单

| 名称 | 类型 | 默认值 | 单位 | 说明 |
|---|---|---|---|---|
| `record_timing` | `bool` | `false` | - | 是否记录周期时间戳到 JSON |
| `record_timing_path` | `string` | `/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/outputs/logs/engineering_40_timing.json` | 路径 | 时序数据文件路径 |
| `record_log` | `bool` | `false` | - | 是否启用日志契约（关卡 42） |
| `log_path` | `string` | `/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/outputs/logs/engineering_42_log.jsonl` | 路径 | 日志契约文件路径 |
| `episode_id` | `int` | `0` | - | 实验回合 ID，写入日志 |
| `pitch_safety_limit` | `double` | `0.3` | rad | 俯仰角安全阈值 |
| `yaw_rate_gain` | `double` | `0.05` | N·m/(rad/s) | 偏航角速度误差到左右轮差动力矩的比例增益 |
| `yaw_torque_limit` | `double` | `0.15` | N·m | 偏航差动力矩的绝对限幅，之后每侧轮矩仍受 `±1 N·m` 总限幅 |

**参数约束**：

- `pitch_safety_limit` 取值范围 `[0.1, 0.5]`，超出范围节点启动报错退出；
- `episode_id` 必须为非负整数，负值视为 0；
- `record_timing_path` 与 `log_path` 必须为可写路径，启动时检查父目录是否存在，不存在则创建；
- 所有参数在节点启动时读取，运行期不支持动态修改（避免运行期参数漂移导致日志语义不一致）。

---

## 4. 消息类型契约

### 4.1 `sensor_msgs/Imu`

仅使用以下字段，其余字段忽略：

| 字段 | 类型 | 单位 | 使用方式 |
|---|---|---|---|
| `orientation` | `geometry_msgs/Quaternion` | 无（四元数） | 由 `quaternion_to_pitch` 提取俯仰角 |
| `angular_velocity` | `geometry_msgs/Vector3` | rad/s | 取 `y` 分量作为 `pitch_rate` |
| `orientation_covariance` | `std::array<double,9>` | 无 | 由 `orientation_covariance_valid` 检查有效性 |

**字段约束**：

- `orientation` 四元数模长必须接近 1（`|‖q‖ - 1| < 1e-3`），否则视为异常；
- `angular_velocity.y` 即 `pitch_rate`，符号约定：正值为抬头方向；
- `orientation_covariance` 全零表示 IMU 未提供协方差，视为无效；
- `orientation_covariance` 含 NaN 视为无效；
- `linear_acceleration` 字段不使用，忽略其值。

### 4.2 `std_msgs/Float64MultiArray`

| 字段 | 类型 | 语义 |
|---|---|---|
| `data` | `float64[]` | 长度恒为 2，`[left_torque, right_torque]`，单位 N·m |

**约束**：

- `data` 数组长度必须为 2，长度不符视为发布方异常，订阅方记录告警但不崩溃；
- `data[0]`（左轮）与 `data[1]`（右轮）取值范围 `[-1.0, 1.0]`，由 `clamp_torque` 保证；
- `layout` 字段不使用，保持默认值。

### 4.3 `std_msgs/String`

| 字段 | 类型 | 取值 |
|---|---|---|
| `data` | `string` | `"BOOT"` / `"SELF_CHECK"` / `"DISARMED"` / `"ARMED"` / `"FAULT"` |

**约束**：

- `data` 必须为上述 5 种枚举值之一，大小写敏感；
- 订阅方解析未知枚举值时记录告警并忽略，不触发状态转换。

### 4.4 `std_srvs/Trigger`

**Request**：空（无字段）。

**Response**：

| 字段 | 类型 | 语义 |
|---|---|---|
| `success` | `bool` | 是否成功执行 |
| `message` | `string` | 人类可读的说明，失败时必填 |

**约束**：

- `success=true` 时 `message` 可为空字符串；
- `success=false` 时 `message` 必须非空，说明失败原因。

---

## 5. QoS 策略

### 5.1 SensorDataQoS（用于 `/imu`）

| 策略 | 值 | 理由 |
|---|---|---|
| Reliability | `BEST_EFFORT` | IMU 数据高频且对实时性敏感，丢包优于堆积 |
| History | `KEEP_LAST` | 只保留最新数据 |
| Depth | `5` | 缓冲 5 帧以应对短时调度抖动 |
| Durability | `VOLATILE` | 不保留历史数据，新订阅者从当前帧开始接收 |

SensorDataQoS 是 ROS2 对传感器数据的标准约定，避免 RELIABLE 模式下重传导致的延迟累积。

### 5.2 默认 QoS（用于 `/wheel_torque` 与 `/safety_state`）

| 策略 | 值 | 理由 |
|---|---|---|
| Reliability | `RELIABLE` | 力矩指令与状态变更不能丢失 |
| History | `KEEP_LAST` | 保留最近消息 |
| Depth | `10` | 缓冲 10 帧以应对订阅方短时阻塞 |
| Durability | `VOLATILE` | 不保留历史，避免新订阅者收到过期指令 |

**选择理由**：

- `/wheel_torque` 使用 RELIABLE：力矩指令丢失会导致机器人失稳，必须保证送达；
- `/safety_state` 使用 RELIABLE：状态变更（尤其是 FAULT）必须被监控节点收到，丢失可能导致操作员误判；
- 不使用 TRANSIENT_LOCAL durability：避免新订阅者收到过期指令（如已经从 FAULT 恢复后仍收到旧 FAULT 消息）。

---

## 6. 单位与坐标系

### 6.1 单位约定

| 物理量 | 单位 | 说明 |
|---|---|---|
| 角度 | rad | 弧度，不用度；与 MuJoCo、ROS2 标准一致 |
| 角速度 | rad/s | 弧度每秒 |
| 力矩 | N·m | 牛·米 |
| 时间 | ns | 纳秒，steady_clock，单调递增 |
| 频率 | Hz | 赫兹 |

**禁止混用单位**：所有接口字段在文档与代码中统一使用上述单位，禁止在日志中混用度与弧度。

### 6.2 坐标系

**机身坐标系**（body frame）：

- 原点：机器人质心
- +x：前向（机器人前进方向）
- +y：左向
- +z：上向

**欧拉角顺序**：ZYX（即先 yaw、再 pitch、再 roll），与 `quaternion_to_pitch` 实现一致。

**俯仰角符号**：

- `pitch > 0`：机器人前倾（重心前移）
- `pitch < 0`：机器人后倾（重心后移）

### 6.3 轮端符号约定

| 轮 | 符号 | 说明 |
|---|---|---|
| 左轮 | `+1.0` | 正向力矩使轮子前转（机器人前进） |
| 右轮 | `-1.0` | 坐标系镜像，需取反才能使轮子前转 |

符号约定在 `control_node.cpp` 中硬编码：

```cpp
wheel_torque.data[0] = clamped_torque * 1.0;   // 左轮
wheel_torque.data[1] = clamped_torque * -1.0;  // 右轮
```

> 注意：符号约定不允许通过参数修改，避免运行期错配。修改符号必须改代码并重新编译。

---

## 7. 限幅与饱和

### 7.1 PD 力矩限幅

| 参数 | 值 | 说明 |
|---|---|---|
| 限幅阈值 | `±1.0 N·m` | 由 `clamp_torque(raw, 1.0)` 强制 |
| 限幅顺序 | 先限幅，后门控 | `raw_torque → clamped_torque → gated_torque` |
| 饱和标记 | `safety_flag=2` | `raw != clamped` 时记录 |

限幅发生在控制律计算之后、安全状态机门控之前，确保门控逻辑只处理已限幅的力矩。

### 7.2 俯仰角安全阈值

| 参数 | 值 | 说明 |
|---|---|---|
| 阈值 | `±0.3 rad`（约 17.2°） | 编译期常量 `PITCH_SAFETY_LIMIT_RAD` |
| 触发动作 | 立即转 FAULT | 任何状态下 |
| 恢复方式 | 仅 `/reset` | 禁止自动恢复 |

阈值由编译期常量兜底，参数 `pitch_safety_limit` 仅在 `[0.1, 0.5]` 范围内可调，超过 0.5 启动报错。

### 7.3 安全状态机门控

| 状态 | 输出力矩 | 说明 |
|---|---|---|
| BOOT | 0.0 | 上电初始 |
| SELF_CHECK | 0.0 | 自检中 |
| DISARMED | 0.0 | 待 arm |
| ARMED | `clamped_torque` | 唯一输出力矩的状态 |
| FAULT | 0.0 | 故障锁定 |

门控逻辑：

```cpp
double gated_torque = (state_ == ARMED) ? clamped_torque : 0.0;
```

门控是力矩输出的最后一道闸门，独立于控制律实现，确保任何控制律异常都不能绕过安全约束。

---

## 8. 错误码与安全标志

### 8.1 `safety_flag` 字段

`safety_flag` 是日志契约中的 `uint8` 字段，取值如下：

| 值 | 含义 | 触发条件 |
|---|---|---|
| 0 | 正常 | 无异常 |
| 1 | 协方差无效 | `orientation_covariance_valid` 返回 `false` |
| 2 | 力矩饱和 | `raw_torque != clamped_torque` |
| 3 | FAULT | 安全状态机处于 FAULT 状态 |

**优先级**：FAULT > 协方差无效 > 力矩饱和 > 正常。同一时刻只记录最高优先级。

**与安全状态机的关系**：

- `safety_flag=3` 等价于 `safety_state == FAULT`；
- `safety_flag=1` 或 `2` 时安全状态机可能仍为 ARMED（不强制转 FAULT）；
- `safety_flag=0` 时安全状态机必然为 ARMED（其他状态不会写入日志或写入时 `safety_flag=3`）。

### 8.2 安全状态枚举

| 状态 | 值 | 含义 | 力矩输出 |
|---|---|---|---|
| `BOOT` | 0 | 上电初始 | 0.0 |
| `SELF_CHECK` | 1 | 自检中 | 0.0 |
| `DISARMED` | 2 | 自检通过，待 arm | 0.0 |
| `ARMED` | 3 | 运行中 | `clamped_torque` |
| `FAULT` | 4 | 故障锁定 | 0.0 |

**状态值约定**：值严格递增表示状态推进，但 `FAULT=4` 是终态，不保证值大小与严重度一一对应。

**与 `/safety_state` 话题的关系**：话题发布的是状态名字符串（如 `"ARMED"`），枚举值仅在代码内部使用，不通过话题直接传输，避免订阅方依赖具体数值。

---

## 9. 配置文件引用

本节列出接口契约关联的配置文件路径，所有路径均为仓库相对路径，且全部使用 JSON 格式（不存在 YAML 配置）。配置文件路径与代码实现一一对应，由 `scripts/tools/check_doc_code_consistency.py` 自动校验。

| 配置文件路径 | 用途 | 关键字段 |
|---|---|---|
| `configs/robot/upkie.json` | Upkie 机器人模型配置（关节/执行器/传感器契约） | `nq=13, nv=12, nu=6`；6 关节；4 位置执行器 + 2 力矩执行器（轮端范围 `[-1.0, 1.0]`） |
| `configs/control/pd.json` | PD 控制器增益配置 | `Kp=3.0, Kd=0.8`，限幅 `±1.0 N·m` |
| `configs/control/lqr.json` | LQR 控制器权重矩阵配置 | 基于线性化倒立摆模型 |
| `configs/env/standing.json` | 站立环境配置 | 100Hz 仿真步长，18 维观测 |
| `configs/env/velocity.json` | 速度跟踪环境配置 | 6 维连续动作空间 |

> 注意：项目自 v2 起统一使用 JSON 配置，旧版文档曾引用 YAML 风格路径（如 lqr、standing、velocity 三处控制器与环境配置），实际仓库中并不存在 YAML 文件，已统一修正为上述 JSON 路径。

---

## 10. 文档-代码一致性校验

本接口契约由 `scripts/tools/check_doc_code_consistency.py` 在每次提交前自动校验：

- 话题名称必须与 `ros2_ws/src/upkie_control/src/control_node.cpp` 中的 `create_publisher` / `create_subscription` 调用一致；
- 服务名称必须与 `create_service` 调用一致；
- 第 9 节列出的配置文件路径必须真实存在；
- 校验结果写入 `outputs/results/doc_code_consistency_44.json`，退出码 0=一致，1=不一致。
