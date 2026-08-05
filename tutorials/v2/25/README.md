# 25 Gymnasium 环境契约

> 建设状态：可执行
> 阶段：学习控制
> 作品集目录：`outputs/portfolio/25`

## 岗位任务

你的交付物是一份"环境契约验证报告"：证明你封装的 Upkie Gymnasium 环境满足 `step()`/`reset()` 接口的所有约定，包括观测空间、动作空间、奖励范围和终止条件的类型安全。面试官会问："你怎么确保 RL 算法拿到的观测值和发出的动作值都在预期范围内？如果环境偷偷修改了状态怎么办？"

具体交付：

1. 一段代码，用 `gymnasium.utils.env_checker.check_env` 验证环境合规性。
2. 一张表，列出 observation_space 的每个维度、物理含义、单位和范围。
3. 一段测试，证明 `reset()` 后观测值在 space 范围内，`step()` 的返回值类型正确。

## 学习目标

- **能理解**：解释 Gymnasium 的五元组返回值 `(observation, reward, terminated, truncated, info)` 各自的语义，区分 terminated（任务完成/失败）和 truncated（时间到/外部中断）。
- **能推导**：从 MuJoCo 的 `qpos`/`qvel`/`ctrl` 出发，设计观测空间和动作空间的归一化方案。
- **能实现**：用 `gymnasium.Env` 基类封装 Upkie MuJoCo 仿真，通过环境检查器验证。

## 前置关卡

完成 `24`（模型预测控制 MPC）的证据验收。你需要理解：

- Upkie 的状态向量（qpos 13 维 + qvel 12 维）和控制输入（ctrl 6 维）
- 经典控制器的输入/输出接口
- 离散时间仿真的步进流程

## 先观察现象

**错误基线实验**：不封装 Gymnasium 接口，直接用 MuJoCo 做 RL 训练。

```python
import mujoco
import numpy as np

model = mujoco.MjModel.from_xml_path("assets/upkie.xml")
data = mujoco.MjData(model)

# 直接操作 MuJoCo 数据
data.ctrl[:] = np.random.uniform(-1, 1, 6)
mujoco.mj_step(model, data)

# 问题 1：没有归一化——qpos 中位置是 m，角度是 rad，四元数无量纲
# 问题 2：没有终止条件——机器人倒了还在继续仿真
# 问题 3：没有奖励信号——不知道做得好不好
print(f"原始状态: {data.qpos[:5]}")  # 混合单位，不可比
```

**记录观察**：原始 MuJoCo 状态不适合作为 RL 的观测输入——不同维度量级差几个数量级，神经网络很难学习。

## 直觉与概念

<!-- upkie-animation:25-intuition -->

### Gymnasium 环境是什么

Gymnasium 环境是一个标准化的"黑盒"接口：

环境 = (观测空间, 动作空间, 转移动力学, 奖励函数, 终止条件)

你不需要知道环境内部怎么工作（黑盒），只需要知道：

- **输入**：你发出的动作 `action`
- **输出**：环境返回的观测 `observation`、奖励 `reward`、是否结束 `terminated/truncated`
- **契约**：输入输出必须满足空间和类型约束

这就像一个餐厅的菜单：你不需要知道厨房怎么做菜，但菜单告诉你"这道菜有什么、多少钱、多久上"。

### 五元组返回值

```python
observation, reward, terminated, truncated, info = env.step(action)
```

| 返回值 | 类型 | 含义 | Upkie 示例 |
|---|---|---|---|
| `observation` | np.ndarray | 当前状态观测 | 归一化的角度、角速度、位置 |
| `reward` | float | 即时奖励 | 保持直立的奖励，倒下的惩罚 |
| `terminated` | bool | 任务是否结束 | 机器人倒下 = True |
| `truncated` | bool | 是否被外部中断 | 达到最大步数 = True |
| `info` | dict | 调试信息 | 姿态状态、奖励分解、实际物理动作、急停、推力与地形 |

**关键区别**：`terminated` 是任务逻辑结束（成功或失败），`truncated` 是时间到了但任务没结束。RL 算法对两者的处理方式不同——terminated 时 value 归零，truncated 时 value 保留。

## 教科书级展开

<!-- upkie-animation:25-parameter -->

### 观测空间设计

**原始状态**（MuJoCo 内部：qpos 13 维 + qvel 12 维 = 25 维）：

qpos (13 维): 位置 m + 四元数 + 角度 rad
qvel (12 维): 速度 m/s + 角速度 rad/s

**问题**：

1. 位置可能无限大（没有边界），四元数在 [-1, 1]，角度范围各异
2. 神经网络对输入尺度敏感——位置 0.01 和角度 0.01 的含义完全不同
3. 四元数有 4 个分量但有归一化约束，实际只有 3 个自由度

**设计方案**：项目实际采用 15 维特征观测（而非直接拼接 qpos/qvel），从 MuJoCo 状态中提取物理意义明确的特征：

```python
# 实际实现：src/upkie_mujoco_course/envs/observation.py
OBSERVATION_NAMES = (
    "pitch_error",         # 俯仰角偏差 (rad)
    "pitch_rate",          # 俯仰角速度 (rad/s)
    "base_height",         # 基座高度 (m)
    "x_position",          # 水平位置 (m)
    "forward_velocity",    # 前向速度 (m/s)
    "left_hip_position",   # 左髋关节角度 (rad)
    "left_knee_position",  # 左膝关节角度 (rad)
    "right_hip_position",  # 右髋关节角度 (rad)
    "right_knee_position", # 右膝关节角度 (rad)
    "left_hip_velocity",   # 左髋关节角速度 (rad/s)
    "left_knee_velocity",  # 左膝关节角速度 (rad/s)
    "right_hip_velocity",  # 右髋关节角速度 (rad/s)
    "right_knee_velocity", # 右膝关节角速度 (rad/s)
    "left_wheel_velocity", # 左轮角速度 (rad/s)
    "right_wheel_velocity",# 右轮角速度 (rad/s)
)
```

每个维度都有明确的物理含义和裁剪范围：

```python
# 实际实现：observation.py 中的 observation_bounds()
low = np.array([
    -np.pi, -50.0, -1.0, -20.0, -10.0,   # pitch_error, pitch_rate, base_height, x_position, forward_velocity
    -np.pi, -np.pi, -np.pi, -np.pi,       # 4 个腿部关节位置
    -50.0, -50.0, -50.0, -50.0,           # 4 个腿部关节速度
    -100.0, -100.0,                        # 2 个轮子角速度
])
high = np.array([
    np.pi, 50.0, 2.0, 20.0, 10.0,
    np.pi, np.pi, np.pi, np.pi,
    50.0, 50.0, 50.0, 50.0,
    100.0, 100.0,
])
# dtype = np.float64
```

**为什么选 15 维而不是 25 维？**

- 去掉了四元数（4 维），改用 pitch_error 等欧拉角表示——避免四元数归一化约束带来的冗余
- 去掉了 y/z 方向的位置和速度——Upkie 主要在 x-z 平面运动
- 保留了所有关节和轮子的位置/速度——这些是控制直接需要的信息

### 动作空间设计

```python
# 实际实现：base_env.py 中的动作空间定义
action_space = gym.spaces.Box(-1.0, 1.0, shape=(6,), dtype=np.float64)
```

**设计原因**：

- 策略输出统一归一化到 `[-1, 1]`，由 `action_adapter.py` 映射为物理执行器命令。
- 4 个腿部执行器是 position actuator，归一化后乘以 `leg_position_scale=0.3` 再加上中立姿态角度。
- 2 个轮端执行器是 motor actuator，归一化后乘以 `wheel_torque_scale=1.0`（N*m）。
- 归一化的好处：RL 策略不需要知道物理单位，输出范围固定，训练更稳定。

```python
# 实际实现：src/upkie_mujoco_course/envs/action_adapter.py
def adapt_action(action, neutral, scale, low, high):
    """把 [-1, 1] 策略动作映射为物理执行器命令。"""
    normalized = np.clip(action, -1.0, 1.0)
    return np.clip(neutral + normalized * scale, low, high)
```

映射公式：`physical = neutral + normalized * scale`，其中 `neutral` 是站立中立姿态的关节角度/力矩，`scale` 控制策略的修正幅度。

### 环境封装代码

项目已实现 `StandingEnv`（继承自 `BaseUpkieEnv`），位于 `src/upkie_mujoco_course/envs/`。以下是核心封装流程：

```python
# 实际实现：src/upkie_mujoco_course/envs/base_env.py（关键流程摘要）
from upkie_mujoco_course.envs.observation import build_observation, observation_bounds
from upkie_mujoco_course.envs.termination import is_fallen
from upkie_mujoco_course.envs.action_adapter import adapt_action

class BaseUpkieEnv(gym.Env):
    def __init__(self, max_episode_steps=None, initial_pose="stand", ...):
        self.runner = SimulationRunner()        # MuJoCo 仿真器
        low, high = observation_bounds(self.runner)
        self.observation_space = spaces.Box(low, high, dtype=np.float64)  # 15 维
        self.action_space = spaces.Box(-1.0, 1.0, shape=(6,), dtype=np.float64)  # 归一化
        self.neutral_action = self._neutral_action()  # 站立中立姿态
        self.action_scale = [0.3]*4 + [1.0]*2  # 腿 0.3 rad + 轮 1.0 N*m

    def reset(self, *, seed=None, options=None):
        self.runner.reset(initial_pose)
        self._apply_reset_randomization()  # 域随机化
        return self._observation(), {
            "time": ...,
            "initial_pose": ...,
            "randomization": ...,
            "terrain": ...,
        }

    def step(self, action):
        # 1. 归一化 → 物理动作
        physical_action = adapt_action(action, self.neutral_action,
                                       self.action_scale, ctrl_low, ctrl_high)
        # 2. 仿真步进
        self.runner.step(physical_action)
        # 3. 奖励计算（6 项加权求和，权重来自 configs/env/standing.json）
        reward_terms = self.compute_reward_terms(state, action)
        reward = sum(scales[name] * value for name, value in reward_terms.items())
        # 4. 终止判断
        terminated = is_fallen(state, max_pitch_rad=0.8, min_height=-0.35)
        truncated = not terminated and self.elapsed_steps >= self.max_episode_steps
        return obs, reward, terminated, truncated, info

    def compute_reward_terms(self, state, action):
        """返回 6 个奖励项的字典。"""
        return {
            "alive": 1.0 if state["both_wheels_contact"] else 0.0,
            "upright": np.exp(-4.0 * pitch**2),
            "height": np.exp(-10.0 * (base_height - self.target_standing_height)**2),
            "position": -x_position**2,
            "effort": -np.mean(action**2),
            "smoothness": -np.mean((action - prev_action)**2),
        }
```

关键行设计原因：

- `adapt_action(...)`：即使 RL 策略输出 `[-1, 1]` 范围外的值，适配器也保证执行器不收到非法值。这是安全防线。
- `is_fallen(state, max_pitch_rad=0.8, min_height=-0.35)`：明确的失败条件——俯仰角超过 0.8 rad（约 46 度）或基座高度低于 -0.35 m 就认为倒了。
- `compute_reward_terms` 返回字典而非标量：方便调试和分析每项贡献。

## 动手检查点

### 检查点 1：环境合规性检查

```powershell
python scripts/05_check_gym_env.py
```

预期输出：

Gymnasium 环境检查通过

`check_env` 通过时不打印额外信息——这说明观测空间、动作空间和返回值类型全部合规。如需查看 space 详情，可用 Python 手动检查：

```python
env = StandingEnv(max_episode_steps=5)
print(f"observation_space: {env.observation_space}")  # Box(15,) float64
print(f"action_space: {env.action_space}")             # Box(6,) float64
```

### 检查点 2：随机策略测试

```powershell
python -c "
import sys
sys.path.insert(0, 'src')
from upkie_mujoco_course.envs.standing_env import StandingEnv

env = StandingEnv(max_episode_steps=200)
obs, info = env.reset(seed=42)
print(f'观测维度: {obs.shape}, 数据类型: {obs.dtype}')
print(f'动作维度: {env.action_space.shape}, 数据类型: {env.action_space.dtype}')
total_reward = 0
steps = 0
for _ in range(1000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    total_reward += reward
    steps += 1
    if terminated or truncated:
        break
print(f'总奖励: {total_reward:.2f}')
print(f'存活步数: {steps}')
env.close()
"
```

预期：随机策略通常会较早触发 `terminated=True`；总奖励的正负取决于倒下前累计的密集奖励，不能把“必须为负”写成接口契约。

### 专属实验与统一验收

```powershell
python scripts/run_rl_lab.py --chapter 25
python scripts/course_checkpoint.py --chapter 25
```

固定 `seed=25` 的专属实验结果为：

observation_dim=15
action_dim=6
reset_reproducibility_max_abs=0.0
step_time_ms_mean=0.27712812538993603
step_time_ms_max=0.5397000059019774

这些时延是本机一次固定运行记录，不是所有计算机的实时保证；自动门槛只要求平均 step 时间不超过 60 ms。

## 可视化证据

<!-- upkie-animation:25-evidence -->

实际证据为：

1. `outputs/plots/rl_25.png`：左图为 observation/action 维度，右图为 64 次 step 延迟；
2. `outputs/logs/rl_25.json`：观测/动作 shape、逐步时延与固定 seed；
3. `outputs/results/rl_25.json`：维度、复现误差和平均时延硬检查；
4. `outputs/portfolio/25/evidence.json`：作品集索引。

## 故障诊断挑战

<!-- upkie-animation:25-comparison -->

**破坏**：在 `step()` 中去掉动作归一化——直接把 RL 策略的原始输出传给 MuJoCo 的 `data.ctrl`，跳过 `adapt_action()` 的中立姿态偏移和缩放。

**第一处异常**：如果策略输出 `action[0] = 5.0`（远超 [-1, 1] 范围），position actuator 会尝试把关节转到 5 rad，远超合理关节范围，产生极大力矩，机器人在一步内被甩飞。

**根因假设**：`adapt_action()` 不仅做裁剪，还负责将归一化动作映射为物理命令（`neutral + normalized * scale`）。跳过这一步后，策略的 [-1, 1] 输出被当作物理弧度直接传给执行器，量级完全不匹配。

**最小修复**：恢复 `adapt_action(action, neutral_action, action_scale, ctrl_low, ctrl_high)` 调用。

**验证**：重新运行后动作值始终在执行器允许范围内，机器人不会一步被甩飞。

## 三档任务

### 基础任务

- 通过 `check_env` 验证环境合规性。
- 运行 10 次随机策略，记录存活步数和总奖励的均值/标准差。

### 岗位挑战

- 实现观测归一化：把每个维度映射到 [-1, 1] 范围，证明归一化后的观测能加速 RL 训练。
- 设计三种不同难度的环境变体（standing、walking、running），比较动作空间和奖励函数的差异。

### 开放探索

- 研究 Procgen 和 DM Control Suite 的环境设计哲学，写一段 200 字分析：一个好的 RL 环境应该具备哪些属性？
- 比较 Gymnasium 和 DeepMind Control Suite 的接口差异。

## 复盘与面试

1. terminated 和 truncated 的区别为什么重要？

<!-- upkie-qa:25-q1 -->
terminated 表示任务逻辑结束（机器人倒了，状态本身到达终止），truncated 表示时间到但任务没结束（只是人为截断）。RL 算法计算 value 时两者处理完全不同：terminated 的后续价值为零（倒了就真的没有未来回报），truncated 的后续价值需要用价值函数 bootstrapping（如果不截断本可以继续拿奖励）。如果混淆两者——比如把超时当成 terminated——value 估计会系统性偏低，策略会错误地认为"活到时间上限附近没有价值"，学出扭曲的行为。
<!-- /upkie-qa -->

2. 为什么需要 action clipping？

<!-- upkie-qa:25-q2 -->
RL 策略（尤其训练早期）可能输出任意大的值：高斯策略的采样没有硬边界，网络初始化后的输出也可能离谱。没有 clipping 会导致执行器收到非法输入，仿真发散甚至数值爆炸，训练直接崩溃。Clipping 是环境的安全防线：不管上层策略输出什么，进入仿真的动作永远在 `ctrlrange` 内。这与 18 章"VLA 不能直接输出未限幅力矩"是同一个工程原则：安全约束必须在环境/接口层强制执行，不能依赖学习组件自觉遵守。
<!-- /upkie-qa -->

3. 观测空间为什么不直接用 qpos/qvel？

<!-- upkie-qa:25-q3 -->
两个原因。一是尺度和单位混乱：qpos 混合了不同单位（m、无量纲四元数、rad），数值范围差异大，而神经网络对输入尺度敏感——一个维度比其他维度大 100 倍，梯度就会被它主导。二是表示冗余：qpos 包含四元数（4 维表示 3 个自由度），存在单位模长约束，网络很难利用。项目实际采用 15 维特征观测：从 qpos/qvel 中提取 pitch_error、base_height 等物理意义明确的特征，既消除四元数冗余，又为每个维度设置合理的裁剪范围。
<!-- /upkie-qa -->

4. 环境的 seed 为什么重要？

<!-- upkie-qa:25-q4 -->
可复现性是科学实验的基本要求：同一个 seed 应该产生完全相同的初始状态和随机扰动，否则无法区分"算法改进"和"运气好"，也无法调试只在特定初始条件下出现的故障。实现上最常见的陷阱：环境代码里用了全局 `np.random` 而不是 Gymnasium 提供的 `self.np_random`，seed 就不会生效——接口上看起来接受了 seed，随机数却走了另一条不受控的链路。本项目的实验约定（所有自动化实验必须指定 `--seed`，不可复现不计入课程证据）就建立在这一层之上。
<!-- /upkie-qa -->

## 下一关

关卡 `26`（奖励、终止与指标）会假设你已经有一个合规的 Gymnasium 环境。本关产出的环境接口将成为下一关设计奖励函数和评估指标的"实验平台"——没有标准化的环境接口，就无法公平比较不同的奖励设计。
