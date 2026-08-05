# 26 奖励、终止与指标

> 建设状态：可执行
> 阶段：学习控制
> 作品集目录：`outputs/portfolio/26`

## 岗位任务

你的交付物是一份"奖励工程报告"：设计三种不同的奖励函数，用同一 RL 算法训练，并定量比较它们对最终平衡性能的影响。面试官会问："你怎样设计奖励函数来引导 RL 学到你想要的行为？如果奖励函数有漏洞，策略会怎么利用？"

具体交付：

1. 三种奖励函数的定义和代码（稀疏/密集/塑形）。
2. 一张训练曲线对比图：三种奖励下的 episode 奖励均值。
3. 一段"奖励漏洞分析"：展示策略在某种奖励下学到的非预期行为。

## 学习目标

- **能理解**：解释奖励函数的三个设计维度——稀疏性（何时给奖励）、方向性（引导还是惩罚）和尺度（数值范围），以及它们对 RL 学习速度的影响。
- **能推导**：从 MDP 的定义出发，证明奖励缩放不影响最优策略但影响学习速度。
- **能实现**：在 Upkie 环境中实现三种奖励函数，用固定 seed 训练并比较。

## 前置关卡

完成 `25`（Gymnasium 环境契约）的证据验收。你需要理解：

- Gymnasium 的 `step()` 返回值语义
- observation_space 和 action_space 的归一化
- terminated vs truncated 的区别

## 先观察现象

**错误基线实验**：给一个有漏洞的奖励函数——只有存活奖励，没有行为引导。

```python
def reward_hack(env):
    """漏洞奖励：只要没倒就给 1 分，倒了给 -100。"""
    height = env.data.qpos[2]  # 直接访问 MuJoCo 内部状态（不推荐）
    if height < -0.35:
        return -100.0
    return 1.0  # 活着就有分
```

**记录观察**：策略会学到什么？它会尽量"活着"——可能原地不动，也可能找到一个奇怪的姿势（比如躺倒但高度刚好超过阈值）来最大化存活时间。这不是你想要的"直立平衡"。

## 直觉与概念

<!-- upkie-animation:26-intuition -->

### 奖励函数：RL 的"考试大纲"

奖励函数告诉 RL 算法"什么是好的行为"。就像考试大纲告诉学生"哪些知识点要考"：

- **考试大纲只列出题型**（奖励只定义目标）→ 学生可能只背答案不理解原理（策略可能找到漏洞）
- **考试大纲覆盖所有能力**（奖励覆盖所有期望行为）→ 学生必须真正学会（策略必须学到正确的行为）

### 三种奖励设计模式

**1. 稀疏奖励（Sparse Reward）**

- `$r` — +100  如果成功（保持直立 10 秒）
- `$r` — -100  如果失败（倒下）
- `$r` — 0     其他情况

- 优点：目标明确，没有歧义
- 缺点：信号太少，RL 需要大量探索才能找到"成功"路径

**2. 密集奖励（Dense Reward）**

$$
r = \exp(-4 \cdot pitch^2) + \exp(-10 \cdot height^2) - 0.1 \cdot position^2 - 0.01 \cdot mean(action^2)
$$

每一步都有反馈：偏离直立越多，奖励越低。

- 优点：信号丰富，学习快
- 缺点：需要仔细设计各项权重，否则策略可能"刷分"（比如为了减小 ctrl^2 而不动作）

**3. 奖励塑形（Reward Shaping）**

$$
r = -\lVert x - x_{\text{target}}\lVert ^2 + bonus(\lVert x\lVert  < threshold)
$$

在密集奖励基础上加入"接近目标的额外奖励"，引导策略探索正确方向。

- 优点：结合了信号密度和目标明确性
- 缺点：shaping 设计不当可能导致策略优化 shaping 目标而非真实目标（Ng et al., 1999）

### 终止条件设计

- `$terminated` — True 当:
1. 俯仰角绝对值 > 0.8 rad（约 46 度，严重倾斜）
2. 基座高度 < -0.35 m（倒下）
- `$truncated` — True 当:
1. 步数 >= max_episode_steps（默认 1000 步，时间到）

实际实现位于 `src/upkie_mujoco_course/envs/termination.py`：

```python
def is_fallen(state, max_pitch_rad=0.8, min_height=-1.0):
    if abs(state.get("pitch_error", 0.0)) > max_pitch_rad:
        return True
    if state.get("base_height", 0.0) < min_height:
        return True
    return False
```

**关键原则**：终止条件必须独立于奖励。不能因为"奖励很低"就终止——终止条件定义的是"任务物理上无法继续"，不是"做得不好"。

## 教科书级展开

<!-- upkie-animation:26-parameter -->

### 奖励缩放不影响最优策略

**命题**：如果 `r'(s,a) = c * r(s,a)`（c > 0），则 r 和 r' 下的最优策略相同。

**证明**：

$$
V \cdot (s) = max_{\pi} E[sum \gamma^t r(s_{t}, a_{t}) | s_{0} = s, \pi]
V'*(s) = max_{\pi} E[sum \gamma^t c \cdot r(s_{t}, a_{t}) | s_{0} = s, \pi]
       = c \cdot max_{\pi} E[sum \gamma^t r(s_{t}, a_{t}) | s_{0} = s, \pi]
       = c \cdot V \cdot (s)
$$
因为 c > 0，max 操作不受常数缩放影响。

**物理意义**：奖励乘以常数只是改变了"刻度"，不改变相对优劣。但奖励缩放影响梯度大小——太大的奖励导致梯度爆炸，太小的奖励导致梯度消失。

### Upkie 奖励函数设计

实际实现位于 `BaseUpkieEnv.compute_reward_terms()`，采用 6 项加权求和的密集奖励：

```python
# 实际实现：src/upkie_mujoco_course/envs/base_env.py
def compute_reward_terms(self, state, action):
    """返回 6 个奖励项的字典，由 configs/env/standing.json 中的 reward_scales 加权求和。"""
    pitch = float(state["pitch_error"])
    height_error = float(state["base_height"]) - self.target_standing_height
    x_position = float(state["x_position"])
    return {
        "alive": 1.0 if bool(state["both_wheels_contact"]) else 0.0,
        "upright": float(np.exp(-4.0 * pitch * pitch)),
        "height": float(np.exp(-10.0 * height_error * height_error)),
        "position": -x_position * x_position,
        "effort": -float(np.mean(np.square(action))),
        "smoothness": -float(np.mean(np.square(action - self.previous_action))),
    }
```

权重配置来自 `configs/env/standing.json`：

```json
{
  "reward_scales": {
    "alive": 0.5,
    "upright": 1.0,
    "height": 0.5,
    "position": 0.1,
    "effort": 0.01,
    "smoothness": 0.02
  }
}
```

总奖励计算公式：

$$
reward = 0.5 \cdot alive + 1.0 \cdot upright + 0.5 \cdot height + 0.1 \cdot position + 0.01 \cdot effort + 0.02 \cdot smoothness
$$

关键行设计原因：

- `alive`：双轮同时着地得 1.0，否则得 0.0——这是最基本的存活信号。
- `upright = exp(-4 * pitch^2)`：高斯型奖励，俯仰角为零时得 1.0，偏离越远衰减越快。用高斯而非二次函数的好处是：小偏差时梯度平滑，大偏差时梯度饱和（不会无限增大）。
- `height = exp(-10 * height_error^2)`：其中 `height_error=base_height-target_standing_height`。环境初始化时先 reset 到 `stand`，若配置未显式给出目标高度，就用该站立姿态的真实基座高度作为目标。因此站立时该项接近 1，基座趋近地面不会得到更高奖励。
- `position = -x^2`：二次惩罚，阻止机器人漂移太远。
- `effort = -mean(action^2)`：动作幅度惩罚，权重仅 0.01——不希望策略为了节能而放弃平衡。
- `smoothness = -mean((action - prev_action)^2)`：动作变化率惩罚，鼓励平滑的控制输出。

### 指标体系

| 指标 | 含义 | 合格阈值 |
|---|---|---|
| episode_reward | 单 episode 总奖励 | > -50 |
| survival_time | 存活步数 | > 500/1000 |
| max_pitch | 最大俯仰角偏差 | < 0.2 rad |
| ctrl_effort | 控制量 RMS | < 0.5 |
| success_rate | 100 次评估中存活满步的比例 | > 80% |

## 动手检查点

### 检查点 1：PPO 训练与奖励观察

```powershell
python scripts/06_train_ppo_standing.py --total-timesteps 1000 --profile smoke
```

预期输出：

训练完成，模型保存到: outputs/checkpoints/ppo_standing_latest.zip

训练后可通过 `info["reward_terms"]` 观察各奖励项的贡献：

```python
# 评估时查看奖励分解
from upkie_mujoco_course.envs.standing_env import StandingEnv
from upkie_mujoco_course.rl.evaluate import evaluate_policy
import numpy as np

env = StandingEnv(max_episode_steps=200)
obs, _ = env.reset(seed=42)
for _ in range(10):
    action = env.action_space.sample()
    obs, r, term, trunc, info = env.step(action)
    print(f"奖励={r:.3f}, 分解={info['reward_terms']}")
    if term or trunc:
        break
env.close()
```

### 检查点 2：奖励漏洞检测

```powershell
python -c "
import sys; sys.path.insert(0, 'src')
from upkie_mujoco_course.envs.standing_env import StandingEnv
import numpy as np

env = StandingEnv(max_episode_steps=200)
obs, _ = env.reset(seed=42)

# 测试：零动作时的奖励
total_r = 0
for _ in range(100):
    obs, r, term, trunc, info = env.step(np.zeros(6))
    total_r += r
    if term or trunc: break
print(f'零动作 100 步总奖励: {total_r:.2f}')
# 同时查看 terminated、reward_terms；密集存活奖励可能让累计值仍为正
env.close()
"
```

### 专属实验与统一验收

```powershell
python scripts/run_rl_lab.py --chapter 26
python scripts/course_checkpoint.py --chapter 26
```

固定 `seed=26`、中性动作 200 步的真实结果为：

reward_mean=1.8772752006406745
reward_std=0.2663234727769803
upright_mean=0.8851112501310621
height_mean=0.9843925478023553
terminated_ratio=0.01
truncated_ratio=0.0

实验发生 2 次跌倒重置，所以 `terminated_ratio=2/200=0.01`；它不是训练后策略成功率。

## 可视化证据

<!-- upkie-animation:26-evidence -->

实际证据为：

1. `outputs/plots/rl_26.png`：左图是中性动作奖励轨迹，右图是奖励项均值分解；
2. `outputs/logs/rl_26.json`：步数、终止/截断次数和实测指标；
3. `outputs/results/rl_26.json`：奖励方差及 upright/height 非负硬检查；
4. `outputs/portfolio/26/evidence.json`：作品集索引。

## 故障诊断挑战

<!-- upkie-animation:26-comparison -->

**破坏**：把奖励中 `ctrl^2` 的权重从 0.01 改为 10.0（1000 倍增大）。

**第一处异常**：策略学到"不动"——因为任何动作都会被重罚，零动作的奖励最高。机器人会原地倒下，但倒下前的累计奖励比"努力平衡但产生大量控制量"更高。

**根因假设**：控制量惩罚过重，使得策略认为"不消耗能量"比"保持平衡"更重要。

**最小修复**：恢复 `ctrl` 权重为 0.01。

**验证**：策略重新学到主动平衡行为。

## 三档任务

### 基础任务

- 实现三种奖励函数（稀疏/密集/塑形），用同一 seed 各训练 1000 步。
- 比较三种奖励下的训练速度和最终性能。

### 岗位挑战

- 设计一个"对抗性奖励"：故意让奖励函数有一个局部最优（比如鼓励小幅振荡而不是静止），证明 RL 策略会陷入这个局部最优。
- 提出修改方案消除局部最优，并验证。

### 开放探索

- 研究 Inverse RL（逆强化学习）：从人类示范中自动学习奖励函数。
- 写一段 200 字分析：为什么奖励设计是 RL 工程中最困难的部分之一？

## 复盘与面试

1. 稀疏奖励和密集奖励的权衡？

<!-- upkie-qa:26-q1 -->
稀疏奖励（只在成功/失败时给分）目标明确、不引入设计者偏见，但学习慢：策略在碰巧成功之前拿不到任何梯度信号，对平衡这种随机探索几乎不可能碰巧成功的任务尤其致命。密集奖励（每步按姿态、高度等 shaping 项给分）学习快，但每一项 shaping 都是设计者对"好行为"的猜测，猜错了策略就会优化到偏离真实目标的方向（奖励漏洞）。实践中通常从密集奖励开始让策略先学会基本行为，再逐步减少 shaping 项，让真实任务目标主导。
<!-- /upkie-qa -->

2. 为什么终止条件必须独立于奖励？

<!-- upkie-qa:26-q2 -->
如果"奖励很低"就终止 episode，RL 策略会学到"避免低奖励状态"而不是"从低奖励状态恢复"。更隐蔽的是：当终止能提前结束惩罚流时，策略会发现"自杀"（主动让 terminated=True）比苦苦支撑更划算，于是一有危险就放弃，行为极度保守。正确做法：终止条件只由物理事实定义（俯仰超阈值、高度过低等"真的倒了"），奖励只负责对行为好坏打分，两套机制各司其职；若需要惩罚倒地，在终止时给一次性负奖励，而不是反过来用奖励阈值触发终止。
<!-- /upkie-qa -->

3. 奖励缩放对学习率的影响？

<!-- upkie-qa:26-q3 -->
策略梯度的幅值正比于奖励（优势）的幅值：奖励太大→梯度太大→需要更小的学习率才不至于一步更新毁掉策略；奖励太小→梯度接近消失→需要更大的学习率才能推动参数。也就是说奖励尺度和学习率是耦合的，改了奖励量级等于隐式改了学习率，会让调好的超参数失效。通常把单步奖励归一化到 [-1, 1] 或 [0, 1] 范围，或使用运行时奖励归一化（如 VecNormalize），让同一套 PPO 超参数在不同任务间可迁移。
<!-- /upkie-qa -->

4. 怎样检测奖励漏洞？

<!-- upkie-qa:26-q4 -->
核心信号是"奖励高但行为不对"：如果策略学到了你没预期的"奇怪"行为却拿高分，说明奖励函数存在可利用的漏洞。检测手段：不要只看奖励曲线，必须定期看回放视频或轨迹；分项记录奖励各组成部分，检查是否某个 shaping 项被异常地单独刷分；用独立于奖励的物理指标（存活时长、跟踪误差、接触率）交叉验证。常见漏洞模式：不动（靠存活奖励躺平）、高频振荡（刷速度/姿态 shaping）、利用仿真 bug（接触穿透、能量不守恒）。
<!-- /upkie-qa -->

## 下一关

关卡 `27`（MDP 与策略梯度）会假设你已经有一个设计好的奖励函数和工作环境。本关产出的奖励函数将成为下一关推导策略梯度定理时的 `r(s,a)` 项——如果奖励函数有漏洞，策略梯度只会放大这个漏洞。
