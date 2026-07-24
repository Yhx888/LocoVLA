# 29 域随机化与鲁棒性

> 建设状态：可执行
> 阶段：学习控制
> 作品集目录：`outputs/portfolio/29`

## 岗位任务

你的交付物是一份"域随机化运行时审计报告"：证明质量、惯量、质心偏移、摩擦、关节阻尼、执行器强度、观测噪声和动作延迟 8 个字段不但被采样，而且确实进入 MuJoCo 模型或环境控制链。面试官会问："配置写了区间，怎样证明环境真的用了？"

具体交付：

1. 一组带单位和边界的 8 字段运行时随机化规格。
2. 一张 200 个真实 `StandingEnv.reset/step` 回合的字段均值/标准差图，以及每回合 reset/step 原始值。
3. 一段可选 PPO 鲁棒评估代码，使用 checkpoint 元数据匹配动作空间，并报告 return、success、fall，而不是用任意回报阈值猜成功。

## 学习目标

- **能理解**：解释域随机化如何通过扩大训练分布来弥合 sim-to-real gap，以及它的代价（训练更慢、性能上限降低）。
- **能推导**：计算均匀分布的范围覆盖、均值、方差与范围利用率，并解释有限样本误差。
- **能实现**：验证随机化参数真正进入 MuJoCo reset/step，并用固定 seed 调用匹配 checkpoint 契约的评估器。

## 前置关卡

完成 `28`（PPO 训练与诊断）的证据验收。你需要理解：

- PPO 训练流程和超参数选择
- TensorBoard 日志解读
- episode reward 和 survival time 指标

## 先观察现象

先运行专属实验，确认随机化不是“配置写了区间，实际每回合仍固定”：

```powershell
python scripts/run_rl_lab.py --chapter 29
```

固定 seed `29` 创建真实 `StandingEnv`，连续执行 200 次 reset 和 step。实验从 `model` 数组、环境噪声状态和动作延迟队列反算实际应用值，不读取 info 中的自报标签：

field_count=8.0
runtime_verified_field_count=8.0
runtime_sample_count=200.0
boundary_violation_count=0.0
covered_field_count=8.0
coverage_ratio=1.0
reset_step_consistency_max_abs=0.0
seed_reproducibility_max_abs=0.0
mean_range_utilization=0.987921790987458

`runtime_verified_field_count=8.0` 表示 8 个字段都由实际模型或环境状态复核；它仍不证明任何策略已经具有鲁棒性。

## 直觉与概念

<!-- upkie-animation:29-intuition -->

### Sim-to-Real Gap：仿真不等于现实

仿真和现实之间永远存在差距：

| 维度 | 仿真值 | 真实值 | 差距来源 |
|---|---|---|---|
| 质量 | 5.0 kg | 5.2 kg（含螺丝、线缆） | 建模误差 |
| 摩擦系数 | 0.7 | 0.5-0.9（地面条件变化） | 环境不确定性 |
| 关节刚度 | kp=100 | kp=80-120（齿轮间隙） | 制造公差 |
| 传感器噪声 | 0 | 0.01-0.05 rad | 传感器不完美 |
| 控制延迟 | 0 ms | 2-5 ms | 通信和处理延迟 |

域随机化的策略是：既然我们不知道真实参数是什么，就让策略在所有"合理"的参数下都能工作。

### 域随机化的直觉：考试准备

想象你要参加一场数学考试，但你不知道题目会出什么。两种准备方式：

- **标准训练**：只做历年真题（固定参数训练）——如果今年出题风格变了，你就抓瞎
- **域随机化**：做各种变体题（参数随机化训练）——虽然每道题做得不那么精，但面对新题更从容

## 教科书级展开

<!-- upkie-animation:29-parameter -->

### 随机化参数选择

`configs/randomization/default.json` 的默认值是标量，即关闭随机化。第 29 关运行时审计使用以下 8 个字段区间，目标是验证它们确实进入模型或环境状态；第 31 关 Sim2Real 使用另一套含初始状态和外力的 8 字段规格，目标是比较标称与随机化回报，不能把两套规格视为共用区间：

| 参数 | 默认值 | 随机化范围示例 | 类型 | 说明 |
|---|---|---|---|---|
| `mass_scale` | 1.0 | `[0.90, 1.10]` | float | 整体质量缩放倍率 |
| `inertia_scale` | 1.0 | `[0.90, 1.10]` | float | 刚体惯量缩放倍率 |
| `com_offset_m` | 0.0 | `[-0.01, 0.01]` | float | 基座质心 x 方向偏移，m |
| `friction_scale` | 1.0 | `[0.75, 1.20]` | float | 地面摩擦缩放倍率 |
| `joint_damping` | 模型标称值 | `[0.01, 0.10]` | float | 受控关节阻尼 |
| `actuator_strength_scale` | 1.0 | `[0.85, 1.15]` | float | 执行器 gain/bias 强度缩放 |
| `sensor_noise_std` | 0.0 | `[0.001, 0.004]` | float | 观测噪声标准差 |
| `action_delay_steps` | 0 | `[0, 2]` | int | 动作延迟步数 |

### 随机化代码

实际实现位于 `src/upkie_mujoco_course/randomization/dynamics.py`，采用配置验证 + 逐回合采样的架构：

```python
# 实际实现：configs/randomization/default.json
# 默认配置（所有参数均为标量，即无随机化）
{
    "sensor_noise_std": 0.0,
    "initial_state_std": 0.0,
    "action_delay_steps": 0,
    "push_force": 0.0,
    "push_step": -1,
    "push_duration_steps": 0,
    "friction_scale": 1.0,
    "mass_scale": 1.0
}

# 第 29 关运行时审计固定区间；第 31 关 Sim2Real 规格见对应教程：
{
    "mass_scale": [0.90, 1.10],
    "inertia_scale": [0.90, 1.10],
    "com_offset_m": [-0.01, 0.01],
    "friction_scale": [0.75, 1.2],
    "joint_damping": [0.01, 0.10],
    "actuator_strength_scale": [0.85, 1.15],
    "sensor_noise_std": [0.001, 0.004],
    "action_delay_steps": [0, 2]
}
```

```python
# 实际实现：src/upkie_mujoco_course/randomization/dynamics.py
from typing import Any
import numpy as np

# 支持的浮点字段（每次 episode 采样一个值）
_FLOAT_FIELDS = {
    "mass_scale": {"minimum": 1e-8},
    "inertia_scale": {"minimum": 1e-8},
    "com_offset_m": {"minimum": None},
    "friction_scale": {"minimum": 1e-8},
    "joint_damping": {"minimum": 0.0},
    "actuator_strength_scale": {"minimum": 1e-8},
    "sensor_noise_std": {"minimum": 0.0},
}
_INTEGER_FIELDS = {
    "action_delay_steps": {"minimum": 0},
}

def validate_randomization_config(config: dict[str, Any]) -> None:
    """验证配置，防止负质量、负延迟等没有物理语义的实验设置。"""
    # 检查未知字段、验证区间合法性、确保整数字段使用整数步数

def sample_episode_randomization(config: dict[str, Any], rng: np.random.Generator) -> dict[str, float | int]:
    """按固定 RNG 从配置中采样一组真正写入仿真器的回合参数。"""
    # 对每个字段：如果是标量则直接返回，如果是区间则均匀采样
```

环境内部的应用流程（`BaseUpkieEnv._apply_reset_randomization()`）：

```python
# 实际实现：base_env.py 中每个 episode reset 时自动调用
def _apply_reset_randomization(self):
    self.last_randomization = sample_episode_randomization(self.randomization, self.np_random)
    # 物理量直接写入 MuJoCo model
    self.runner.model.body_mass[:] = self._base_mass * mass_scale
    self.runner.model.body_inertia[:] = self._base_inertia * inertia_scale
    self.runner.model.body_ipos[base_id, 0] = self._base_ipos[base_id, 0] + com_offset_m
    self.runner.model.geom_friction[:, 0] *= friction_scale
    self.runner.model.dof_damping[controlled_dofs] = joint_damping
    self.runner.model.actuator_gainprm[:, 0] *= actuator_strength_scale
    # 环境状态进入观测与控制链
    self._sensor_noise_std = sensor_noise_std
    self._action_delay_steps = action_delay_steps
```

第 29 关结果以 `audit_source=mujoco_model_and_environment_state` 标识审计来源，不信任 `reset_info["runtime_randomization"]`。质量、惯量、质心、摩擦、阻尼和执行器强度均从 MuJoCo model 与保存的基线反算；噪声和延迟从实际驱动观测及动作队列的环境状态读取。随后执行一步并再次读取，要求 reset/step 最大差为 0。

关键行设计原因：

- `rng.uniform(lower, upper)`：均匀采样确保范围内的每个值等概率。如果用正态分布，大部分采样集中在均值附近，极端值被低估。
- 配置验证：防止用户传入未知字段或非法区间（如负质量、负延迟）。
- 每个 episode reset 时采样一次：真实世界的参数在一个 episode 内是固定的。

### 鲁棒性评估协议

```python
import sys
sys.path.insert(0, 'src')
from upkie_mujoco_course.rl.evaluate import evaluate_policy

randomization = {
    "mass_scale": [0.90, 1.10],
    "inertia_scale": [0.90, 1.10],
    "com_offset_m": [-0.01, 0.01],
    "friction_scale": [0.75, 1.2],
    "joint_damping": [0.01, 0.10],
    "actuator_strength_scale": [0.85, 1.15],
    "sensor_noise_std": [0.001, 0.004],
    "action_delay_steps": [0, 2],
}
records = evaluate_policy(
    "outputs/checkpoints/ppo_standing_latest.zip",
    episodes=20,
    mode="rl",
    seed=0,
    randomization=randomization,
    return_records=True,
)
mean_return = sum(record["return"] for record in records) / len(records)
success_rate = sum(record["success"] for record in records) / len(records)
fall_rate = sum(record["fell"] for record in records) / len(records)
print(mean_return, success_rate, fall_rate)
```

不要手动 `PPO.load(..., env=StandingEnv(...))`：当前 `ppo_standing_latest.zip` 是 2 动作 `WheelTorqueStandingEnv` 模型。`evaluate_policy` 会同时校验 zip 内嵌模式与 sidecar，再创建动作维度匹配的环境。

## 动手检查点

### 检查点 1：随机化运行时覆盖

```powershell
python scripts/run_rl_lab.py --chapter 29
```

该命令验证 200 组真实 reset/step 的应用值、边界、seed 重放和范围利用率，不训练策略，也不会覆盖第 28 关固定 checkpoint。

### 检查点 2：可选的域随机化训练与评估

修改 `configs/randomization/default.json`，将需要随机化的参数改为区间：

```json
{
    "mass_scale": [0.90, 1.10],
    "inertia_scale": [0.90, 1.10],
    "com_offset_m": [-0.01, 0.01],
    "friction_scale": [0.75, 1.2],
    "joint_damping": [0.01, 0.10],
    "actuator_strength_scale": [0.85, 1.15],
    "sensor_noise_std": [0.001, 0.004],
    "action_delay_steps": [0, 2]
}
```

然后运行训练：

```powershell
python scripts/06_train_ppo_standing.py --total-timesteps 50000 --profile reference --mode full_action
```

预期：训练比标准训练慢（每个 episode 参数不同，需要更多样本才能收敛），但最终策略在多种参数下都能工作。

使用 `08_eval_policy.py` 按当前 `configs/randomization/default.json` 评估训练好的策略：

```powershell
python scripts/08_eval_policy.py --model outputs/checkpoints/ppo_standing_latest.zip --episodes 10 --mode rl
```

如需不修改全局配置，使用上方 Python API 显式传 `randomization`。当前固定第 29 关没有“标准训练 95%、随机化训练 82%”这类策略对照证据，不能预设改善结论。

### 专属实验与统一验收

```powershell
python scripts/run_rl_lab.py --chapter 29
python scripts/course_checkpoint.py --chapter 29
```

## 可视化证据

<!-- upkie-animation:29-evidence -->

固定证据为：

1. `outputs/plots/rl_29.png`：8 个运行时字段的 200 次均值与标准差；
2. `outputs/logs/rl_29.json`：两次固定 seed 的 reset/step 原始值，以及每字段 mean/std/min/max 和声明边界；
3. `outputs/results/rl_29.json`：`runtime_verified_field_count=8.0`、`coverage_ratio=1.0`、`reset_step_consistency_max_abs=0.0`、`seed_reproducibility_max_abs=0.0`、`mean_range_utilization=0.987921790987458`；
4. `outputs/portfolio/29/evidence.json`：作品集索引。

## 故障诊断挑战

<!-- upkie-animation:29-comparison -->

**破坏**：在域随机化配置中，把摩擦系数范围从 `[0.5, 1.5]` 改为 `[0.01, 0.05]`（极低摩擦，几乎冰面）。

**第一处异常**：策略在训练中学不到有效的平衡行为——因为几乎任何动作都导致打滑，episode reward 始终很低且不收敛。

**根因假设**：极低摩擦使得轮子无法提供有效的推进力。在这种物理条件下，Upkie 本质上是不可控的（控制不了水平运动），RL 无法学到有效策略。

**最小修复**：恢复合理的摩擦范围 `[0.5, 1.5]`。

**验证**：训练恢复正常，策略在合理摩擦范围内鲁棒。

## 三档任务

### 基础任务

- 用域随机化训练 PPO 50000 步，与标准训练对比性能。
- 在 5 种未见参数组合上评估鲁棒性。

### 岗位挑战

- 设计一个"最坏情况搜索"：用优化方法（如 CMA-ES）找到让策略性能最差的参数组合，分析策略在什么条件下会失败。
- 实现渐进式域随机化（Progressive Domain Randomization）：从窄范围开始训练，逐步扩大范围，观察每个阶段的性能变化。

### 开放探索

- 研究 System Identification（系统辨识）如何缩小 sim-to-real gap——与其随机化所有参数，不如用真实数据辨识关键参数。
- 写一段 200 字分析：域随机化的极限在哪里？什么情况下域随机化完全不够，必须用 Sim2Real 迁移方法？

## 复盘与面试

1. **域随机化的代价是什么？** (a) 训练更慢（每次 episode 参数不同，梯度方差更大）；(b) 标称性能降低（策略必须兼顾所有参数，不能针对某一组参数最优化）；(c) 随机化范围选择不当可能导致策略在所有参数下都很差。

2. **随机化范围怎么选？** 基于物理知识：(a) 质量范围 = 标称值 +/- 制造公差 + 附件重量；(b) 摩擦范围 = 可能的地面材质范围；(c) 刚度范围 = 齿轮间隙和温度效应。不能凭空猜。

3. **怎样判断域随机化是否足够？** 在真实机器人上测试。如果真实性能与域随机化训练中最差的仿真配置性能一致，说明随机化范围合理。如果真实性能比最差的仿真还差，说明有未被覆盖的 sim-to-real gap。

4. **为什么不在每个 time step 随机化参数？** 因为真实世界的参数在一个 episode 内是固定的（质量不会突然变化）。每步随机化会引入不物理的高频参数变化，策略学到的行为不自然。

## 下一关

关卡 `30`（残差强化学习）会假设你已经理解域随机化对策略鲁棒性的影响。本关产出的域随机化框架将成为下一关的"训练环境"——残差 RL 策略也需要在域随机化条件下训练，才能在实际部署时鲁棒。
