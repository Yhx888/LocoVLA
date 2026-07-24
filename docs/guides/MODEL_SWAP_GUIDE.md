# 模型替换指南

## 准备工作

- `configs/robot/<name>.json`
- `assets/<name>/`
- `RobotSpec`
- joint、actuator、sensor 和 frame 映射
- 默认姿态参数

## 替换步骤

1. 参考 Upkie 的配置创建新的 JSON 文件
2. 准备 URDF/MJCF 文件并放置到对应目录
3. 运行 `python scripts/01_check_model.py --config configs/robot/<name>.json`
4. 根据输出调整 joint、actuator、sensor 映射
5. 更新控制器和环境中的相关配置
6. **必跑校验**：运行 `python scripts/11_model_contract_lab.py` 验证物理契约一致性
7. 同步教程与飞书事实（修改模型后必须同步更新所有教程文档和飞书文档）

## v2 物理契约清单

替换模型时，新 JSON 必须覆盖以下字段（对照 `configs/robot/upkie.json` 全字段）：

### 1. 基础元信息

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | `string` | 配置 schema 版本（当前 `2.0`） |
| `name` | `string` | 机器人名（用作 `package_dir`、`assets/<name>/` 的标识） |
| `package_dir` | `string` | 资源目录相对路径 |
| `model_path` | `string` | URDF/MJCF 文件相对路径 |
| `model_format` | `string` | `urdf` 或 `mjcf` |

### 2. 基座与维度

| 字段 | 类型 | 说明 |
|---|---|---|
| `base_body` | `string` | 基座 body 名（如 `base`） |
| `floating_base` | `bool` | 是否为自由基座；v2 默认 `true` |
| `root_joint_name` | `string` | 自由基座 joint 名（如 `root`） |
| `default_base_position` | `[float, float, float]` | 默认基座位置（m） |
| `default_base_quaternion` | `[float, float, float, float]` | 默认基座姿态（wxyz 顺序） |
| `equilibrium_pitch_rad` | `float` | **关键**：站立平衡点俯仰角（rad），由质心/轮轴几何审计得到；观测和奖励统一使用 `pitch_error = pitch - equilibrium_pitch_rad` |
| `floor_z` | `float` | 地面 z 坐标 |
| `timestep` | `float` | MuJoCo 仿真步长（s） |
| `frame_skip` | `int` | 每个控制步的仿真子步数 |
| `state_dimensions` | `{nq, nv, nu}` | 广义坐标/速度/执行器维度；v2 Upkie 为 `{13, 12, 6}` |

### 3. 执行器语义（actuator_semantics）

> **关键**：v2 轮端使用**力矩控制**（`command: torque`, `unit: N*m`, `limit: [-1.0, 1.0]`），不再使用速度控制语义。腿部使用位置控制（`command: position`, `unit: rad`）。

```json
"actuator_semantics": {
  "leg": {"command": "position", "unit": "rad"},
  "wheel": {"command": "torque", "unit": "N*m", "limit": [-1.0, 1.0]}
}
```

### 4. 传感器契约（sensor_contract）

> **关键**：传感器来源与字段以 `sensor_contract` 为准，不在代码中硬编码字段名。

| 子字段 | 说明 |
|---|---|
| `source` | 数据来源（`mujoco_state` 或自定义传感器） |
| `fields[].name` | 字段名（如 `base_position`、`joint_position`） |
| `fields[].unit` | SI 单位 |
| `fields[].shape` | 数组形状 |
| `fields[].order` | 顺序约定（如 `base_quaternion` 的 `wxyz`） |

### 5. 轮子契约

| 字段 | 类型 | 说明 |
|---|---|---|
| `wheel_radius_fallback` | `float` | 轮半径回退值（m），用于 `F = tau/r` 换算 |
| `wheel_joints` | `[string, string]` | 左右轮 joint 名 |
| `wheel_directions` | `[float, float]` | **关键**：左右轮方向系数（Upkie 为 `[1.0, -1.0]`，右轮需取反才能前转）；修改后必须同步 `interface_contract.md` §6.3 与 C++ `control_node.cpp` 中的 `data[0] * 1.0, data[1] * -1.0` |

### 6. 关节与执行器列表

| 字段 | 说明 |
|---|---|
| `leg_joints` | 腿部 joint 名列表 |
| `controlled_joints` | 全部受控 joint 名（顺序与 `qpos`/`qvel` 子段对应） |
| `position_actuators` | 位置执行器列表，每项含 `name`、`joint`、`kp`、`ctrlrange`（rad） |
| `torque_actuators` | 力矩执行器列表，每项含 `name`、`joint`、`gear`、`ctrlrange`（N·m） |

### 7. 默认姿态

| 字段 | 说明 |
|---|---|
| `default_pose` | 命名姿态字典（如 `stand`、`crouch`），每个姿态是 `{joint_name: angle_rad}` |
| `sensor_names` | 附加传感器名列表（可为空） |

## 必跑校验脚本

| 脚本 | 用途 | 通过条件 |
|---|---|---|
| `python scripts/01_check_model.py --config configs/robot/<name>.json` | 模型审计：检查 nq/nv/nu、joint/actuator/sensor 映射 | 无 error，所有映射齐全 |
| `python scripts/11_model_contract_lab.py` | **关键**：物理契约一致性校验（`sensor_contract`、`actuator_semantics`、`equilibrium_pitch_rad`、`wheel_directions` 等字段） | 0 项不一致 |

修改 `equilibrium_pitch_rad`、`wheel_directions`、`actuator_semantics` 任一字段后，必须运行 `scripts/11_model_contract_lab.py` 重新校验，并同步更新：

- `docs/design/interface_contract.md` §6.3（轮端符号约定）与 §9（配置文件引用）
- `ros2_ws/src/upkie_control/src/control_node.cpp` 中的 `data[0] * 1.0, data[1] * -1.0` 硬编码
- 所有教程与飞书文档中的事实性陈述（参数、单位、方向）
