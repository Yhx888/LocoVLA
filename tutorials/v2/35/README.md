# 35 示范数据与脚本专家

> 建设状态：可执行
> 阶段：应用型 VLA
> 作品集目录：`outputs/portfolio/35`

## 岗位任务

你的交付物是一份"示范数据质量报告"：用关卡 34 的语言条件控制器（脚本专家）收集高质量示范数据，并验证数据的质量、多样性和覆盖度。面试官会问："你的示范数据覆盖了哪些场景？怎样证明数据足够训练一个能泛化的策略？"

具体交付：

1. 一个数据集（`outputs/datasets/vla/`），包含红、绿、蓝三色各 2 个、共 6 个真实 MuJoCo RGB-D episode，以及本体感觉、高层动作和语言指令。
2. 一张 6 个 episode 的轨迹长度柱状图。
3. 一段数据质量分析：三色覆盖、独立 seed、时间维一致性和保存/加载往返检查。

## 学习目标

- **能理解**：解释为什么行为克隆的数据质量比数量更重要，以及"分布偏移"问题为什么是 BC 的核心挑战。
- **能推导**：从 MDP 的轨迹分布出发，证明专家数据的状态分布和策略执行时的状态分布不同，以及这种差异如何导致性能退化。
- **能实现**：用脚本专家自动收集示范数据，并实现数据质量检查管线。

## 前置关卡

完成 `34`（语言任务与安全命令）的证据验收。你需要理解：

- 语言条件控制器的输入/输出接口
- 任务命令的结构化表示
- 安全层的拦截机制

## 先观察现象

**错误基线实验**：只用一个固定场景收集示范数据。

```python
# 所有示范都是"前往正前方的红色目标"
for ep in range(50):
    instruction = "前往红色目标并停车"
    episode = generate_scripted_demonstration(instruction, seed=0)  # 固定 seed！
```

**记录观察**：所有示范高度相似——策略只见过"正前方 1m 的红色目标"，遇到"左侧 0.5m 的蓝色目标"时完全不知道怎么做。

## 直觉与概念

<!-- upkie-animation:35-intuition -->

### 脚本专家：确定性规则基线

"脚本专家"是一个用规则（不是学习）编写的确定性规则基线。它仅在已验证场景中提供可复现示范；遇到遮挡、未建模障碍或分布外目标时仍可能失败，因此示范是带适用边界的训练标签，不是无条件正确的"标准答案"。

脚本专家的优势：

1. **确定性**：同样的输入总是产生同样的输出（可复现）
2. **安全门控**：输出仍经过 `VLASafetyController` 的限速、俯仰门槛和停止逻辑，但这不等于对所有场景作安全保证
3. **效率**：可以快速生成大量数据（不需要人类操控）

脚本专家的局限：

1. **覆盖有限**：只能处理预编程的场景
2. **不灵活**：遇到没编程的场景就失败
3. **次优**：规则不一定是最优的控制方式

### 数据集格式

每个 episode 是一个 `DemonstrationEpisode` 不可变 dataclass，所有数据以 numpy 数组存储：

```python
from dataclasses import dataclass, field
import numpy as np

@dataclass(frozen=True)
class DemonstrationEpisode:
    """一条完整的示范轨迹。"""
    rgb: np.ndarray              # (T, H, W, 3) uint8, RGB 帧序列
    depth: np.ndarray            # (T, H, W) float32, 深度帧序列
    proprioception: np.ndarray   # (T, obs_dim) float32, 本体感觉
    action: np.ndarray           # (T, 6) float32, 归一化高层命令
    instruction: str             # 语言指令原文
    timestamp: np.ndarray        # (T,) float64, 时间戳
    metadata: dict = field(default_factory=dict)  # episode_id, seed, target_color 等
```

当前动作契约不是 6 个执行器力矩。它的有效高层语义是 `[forward_velocity, yaw_rate, stop]`：前两项分别归一化表示前向速度和偏航角速度，第三项表示停止请求；后 3 项为接口预留位并固定为 0。`VLASafetyController` 再把高层命令转换成受限的 6 维执行器动作，避免学习策略绕过安全层。

保存和加载使用 `contracts.py` 中的函数，格式为 `.npz`：

```python
from upkie_mujoco_course.vla.contracts import save_episode, load_episode

# 保存
path = save_episode(episode, "outputs/datasets/vla/episode_0000.npz")

# 加载
episode = load_episode("outputs/datasets/vla/episode_0000.npz")
print(f"步数: {episode.timestamp.shape[0]}")
print(f"指令: {episode.instruction}")
print(f"RGB 形状: {episode.rgb.shape}")
```

## 教科书级展开

<!-- upkie-animation:35-parameter -->

### 分布偏移问题

**核心挑战**：行为克隆训练时，策略学习的是在专家状态分布 `d_pi_expert(s)` 下模仿专家动作。但部署时，策略在自己的状态分布 `d_pi_theta(s)` 下运行。

训练时: s ~ d_pi_expert  →  a = pi_expert(s)  →  theta 学习 pi_theta(s) ≈ a
部署时: s ~ d_pi_theta   →  a = pi_theta(s)   →  但 d_pi_theta ≠ d_pi_expert!

**直觉**：专家开车总是走在路中间，学生只在"路中间"的状态下见过专家的驾驶方式。一旦学生稍微偏离路中间（到了路边），他不知道怎么回到路中间——因为训练数据里没有这种情况。

**数学后果**：

误差上界 ≈ epsilon * T^2
- `$epsilon` — 单步模仿误差（每步差一点）
- `$T` — episode 长度
误差随时间的平方增长！100 步后，单步误差 0.01 累积到 1.0。

### 示范数据收集代码

```python
from upkie_mujoco_course.vla.demonstrations import generate_scripted_demonstration
from upkie_mujoco_course.vla.contracts import save_episode

# 收集一条示范：内部自动完成语言解析 → 感知 → 专家决策 → 安全控制 → 环境闭环
episode = generate_scripted_demonstration(
    "前往红色目标并停车",
    max_steps=600,
    width=160,
    height=120,
    seed=0,
)
print(f"步数: {episode.timestamp.shape[0]}")
print(f"指令: {episode.instruction}")
print(f"元数据: {episode.metadata}")

# 保存到磁盘
path = save_episode(episode, "outputs/datasets/vla/episode_0000.npz")
```

`generate_scripted_demonstration()` 的完整流程：
1. 调用 `parse_task_instruction()` 解析语言指令
2. 创建 `StandingEnv` 环境和 MuJoCo 渲染器
3. 每步渲染 RGB-D → 颜色目标检测 → `ScriptedVLAExpert` 生成速度命令 → `VLASafetyController` 输出安全动作
4. 将每步的 rgb、depth、proprioception、action、timestamp 收集为 numpy 数组
5. 返回一个完整的 `DemonstrationEpisode`

### 场景多样性设计

```python
SCENARIOS = [
    ("前往红色目标并停车", "red", 0),
    ("前往红色目标并停车", "red", 1),
    ("Navigate to the green target and stop", "green", 10),
    ("Navigate to the green target and stop", "green", 11),
    ("Navigate to the blue target and stop", "blue", 20),
    ("Navigate to the blue target and stop", "blue", 21),
]
```

关键行设计原因：

- 三种颜色分别使用两个独立 seed，正好对应专属实验的 6 份示范。seed 的十位由颜色索引区分，个位 `0/1` 用于训练/验证划分；只在一种颜色或一个 seed 下收集会让覆盖证据失真。

### 数据质量检查

```python
import numpy as np
from pathlib import Path
from upkie_mujoco_course.vla.contracts import load_episode

def check_data_quality(episode_paths):
    """检查示范数据质量。"""
    episodes = [load_episode(p) for p in episode_paths]
    report = {
        "total_episodes": len(episodes),
        "mean_steps": np.mean([e.timestamp.shape[0] for e in episodes]),
        "action_stats": {},
        "coverage": {},
    }

    # 动作统计
    all_actions = np.concatenate([e.action for e in episodes], axis=0)
    report["action_stats"] = {
        "mean": all_actions.mean(axis=0).tolist(),
        "std": all_actions.std(axis=0).tolist(),
        "min": all_actions.min(axis=0).tolist(),
        "max": all_actions.max(axis=0).tolist(),
    }

    # 覆盖度检查
    instructions = set(e.instruction for e in episodes)
    colors = set(e.metadata.get("target_color", "unknown") for e in episodes)
    report["coverage"] = {
        "unique_instructions": len(instructions),
        "instructions": list(instructions),
        "target_colors": list(colors),
    }

    return report
```

## 动手检查点

### 检查点 1：数据收集

```powershell
python scripts/35_generate_vla_demos.py --instruction "前往红色目标并停车" --episodes 3 --max-steps 600
```

预期：收集 3 个 episode，输出路径和步数。

### 检查点 2：数据质量

```powershell
python scripts/run_vla_lab.py --chapter 35
```

预期：固定实验生成红、绿、蓝三色各 2 个、共 6 个真实 MuJoCo RGB-D episode；独立 seed 为每种颜色保留训练/验证差异，并报告保存/加载往返成功率 `1.0`。

### 统一关卡验收

```powershell
python scripts/course_checkpoint.py --chapter 35
```

## 可视化证据

<!-- upkie-animation:35-evidence -->

专属实验把 6 条轨迹的长度图写入 `outputs/plots/vla_35.png`；统一 checkpoint 另保存关卡级汇总证据。

横轴是 6 条示范的索引，纵轴是记录后的时间步数。柱高用于检查轨迹是否异常过短；三色覆盖、seed 和动作语义则从 `outputs/logs/vla_35.json` 与 `.npz` 元数据复核，不能从柱状图单独推断。

## 故障诊断挑战

<!-- upkie-animation:35-comparison -->

**破坏**：在数据收集中不重置环境 seed——所有 episode 从完全相同的初始状态开始。

**第一处异常**：所有 episode 的轨迹几乎完全相同（只有数值精度的微小差异）。数据多样性为零——训练出来的策略只见过一种初始状态。

**根因假设**：没有随机化初始状态（扰动方向、目标位置等），数据集缺乏多样性。

**最小修复**：在 `env.reset(seed=seed)` 中使用不同的 seed，并在目标位置中加入随机偏移。

**验证**：重新收集后 episode 轨迹有显著差异，状态空间覆盖率增大。

## 三档任务

### 基础任务

- 复现本关 6 个三色示范，核对每种颜色都有两个独立 seed，并解释高层动作契约的前三项。
- 运行质量检查脚本，保存报告。

### 岗位挑战

- 设计"对抗性场景"：故意制造困难情况（目标在机器人背后、多个颜色目标同时存在），测试脚本专家的处理能力。
- 实现数据增强：对已有的示范数据进行时间扭曲（time warping）和观测噪声注入，扩大数据集。

### 开放探索

- 研究 DAgger（Dataset Aggregation）算法如何在线解决分布偏移问题。
- 写一段 200 字分析：人类示范和脚本专家示范各有什么优缺点？

## 复盘与面试

1. **为什么数据质量比数量重要？** 1000 个质量差的示范（重复场景、不一致动作）不如 100 个高质量的示范（多样场景、一致动作）。BC 策略的上限由数据的多样性和一致性决定。

2. **分布偏移为什么是 BC 的核心挑战？** 因为 BC 只学了"在专家见过的状态下该做什么"，没学过"犯了错怎么恢复"。一旦策略偏离专家轨迹，它进入了从未见过的状态空间区域，行为不可预测。

3. **怎样评估数据覆盖度？** (a) 指令覆盖：多少种不同的指令被包含；(b) 状态覆盖：PCA 降维后状态空间的分布是否均匀；(c) 动作覆盖：动作空间的各区域是否都有样本。

4. **脚本专家的局限是什么？** 只能处理预编程的场景。如果遇到没见过的情况（比如障碍物），脚本专家可能失败，生成的示范数据就是错误的。

## 下一关

关卡 `36`（行为克隆与视觉语言融合）会假设你已经有一个高质量的示范数据集。本关产出的数据将成为下一关训练 BC 策略的"教材"——策略从这个数据集中学习"看到什么图像 + 听到什么指令 → 做什么动作"。
