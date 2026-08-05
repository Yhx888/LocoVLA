# 30 残差强化学习

> 建设状态：可执行
> 阶段：学习控制
> 作品集目录：`outputs/portfolio/30`

## 岗位任务

你的交付物是一份"残差控制器设计报告"：在 `ResidualStandingEnv` 内部把 `WheelBalancerController` 与 PPO 轮端残差合成，并在相同 seed、相同 10 N 外力下与经典基线配对比较。面试官会问："怎样证明训练时动作语义一直是残差？怎样阻止普通 PPO checkpoint 冒充残差模型？"

具体交付：

1. 残差控制器的架构图：经典层 + RL 层的分工和数据流。
2. 一段代码，实现 `u = clip(u_classic + scale * u_rl)` 的控制结构。
3. 一张配对图：经典基线与残差 PPO 的 10 回合回报，以及逐回合回报差。

## 学习目标

- **能理解**：解释残差 RL 的核心思想——经典控制器处理"已知的线性部分"，RL 策略只学习"经典控制器管不了的非线性残差"。
- **能推导**：从最优控制分解出发，证明 `u* = u_classic + u_residual`，其中 `u_classic` 是线性最优解，`u_residual` 补偿非线性。
- **能实现**：用 `WheelBalancerController`（轮速平衡控制器）作为基线，PPO（关卡 28）训练残差策略，在仿真中验证。

## 前置关卡

完成 `29`（域随机化与鲁棒性）的证据验收。你需要理解：

- `WheelBalancerController` 的接口：`compute_action(runner, sim_time)` 返回物理动作，`reset()` 重置内部状态
- PPO 训练流程和超参数
- 域随机化对训练的影响

## 先观察现象

**错误基线实验**：在大扰动下比较纯经典控制和纯 RL 策略。

```python
# 大扰动：把基座俯仰角设为 30 度
# 注意：自由基座的姿态由四元数 qpos[3:7]（wxyz）表示，
# 不能直接写 qpos[5]；下面用绕 y 轴 30 度的旋转构造四元数。
half = np.radians(30) / 2
data.qpos[3:7] = [np.cos(half), 0.0, np.sin(half), 0.0]

# 纯经典控制（WheelBalancerController）
u_classic = classic.compute_action(runner, sim_time)
# 问题：线性化假设在大偏差时不成立（30 度偏差太大），经典增益不再最优

# 纯 RL
u_rl = policy.predict(obs)
# 问题：RL 从零开始学习，没有利用经典控制器的先验知识
```

**记录观察**：纯经典控制在大扰动下可能恢复很慢或不稳定；纯 RL 训练时间长且不稳定。

## 直觉与概念

<!-- upkie-animation:30-intuition -->

### 残差学习的直觉：站在巨人肩膀上

想象你要学开车：

- **纯 RL**：从零开始——不知道方向盘干什么，不知道油门干什么，全靠试错
- **纯经典控制**：按教科书开——知道基本操作，但遇到复杂路况（结冰、大风）就慌
- **残差 RL**：先跟教练学基本操作（经典控制），然后自己上路积累经验（RL 修正教练的不足）

残差策略的公式 `u = u_classic + u_residual` 意味着：

1. 经典控制器负责"大方向正确"（基本平衡）
2. RL 负责"精细调整"（非线性补偿、扰动适应）
3. 如果 RL 输出为零，当前动作等于经典动作；但非零残差仍可能降低性能，所以必须做配对验收

### 安全性保证

残差结构的安全优势：

$$
u_{\text{total}} = clip(u_{\text{classic}} + scale \cdot u_{rl}, u_{\text{min}}, u_{\text{max}})
$$
如果 u_rl = 0: u_total = clip(u_classic, u_min, u_max)  → 当前步等于经典动作
如果 u_rl 很大: clip 只保证动作不超归一化范围
scale 控制 RL 的影响权重（0 = 纯经典控制, 1 = 完全信任 RL）

动作限幅不等于状态安全：即使每个轮端力矩都合法，持续错误动作仍可能让俯仰越过跌倒阈值。本关还要硬检查回报不退化、成功率不低于基线、跌倒率不高于基线和最大俯仰边界。

## 教科书级展开

<!-- upkie-animation:30-parameter -->

### 最优控制分解

**假设**：系统动力学可以分解为线性和非线性部分

$$
dx/dt = Ax + Bu + f_{nl}(x, u)
$$
A, B = 线性化模型（平衡点附近）
- `$f_nl` — 非线性残差（大偏差时显著）

**最优控制也可以分解**：

u* = u_linear* + u_residual*
u_linear* = -Kx         （LQR 解，处理线性部分）
u_residual* = g(x)       （非线性补偿，通常无法解析求解）

**设计动机**：u_linear* 有解析解（LQR），我们可以放心依赖它。u_residual* 需要学习，但它只需要补偿"线性控制器管不了的部分"，学习负担比从零开始小得多。

### 残差策略的观测空间

RL 策略接收标准 15 维观测，不额外拼接基线输出。训练和评估都把 PPO 动作直接传给 `ResidualStandingEnv.step()`；环境内部才计算基线、裁剪残差并合成最终动作：

- `$obs` — 15 维环境观测
- `$raw_residual` — PPO.predict(obs)                         6 维归一化残差
- `$residual` — clip(raw_residual, -1, 1) * torque_mask     腿部 4 维强制为 0
base = normalize(WheelBalancerController.compute_action(...))
applied = clip(base + residual_scale * residual, -1, 1)
BaseUpkieEnv.step(applied)

`info` 同时记录 `base_action`、`residual_action` 和 `applied_action`。`residual_mask` 只允许两个 torque actuator 被 PPO 修改，四个腿部 position actuator 的残差恒为 0。

### 数值算例

$$
residual_{\text{scale}}=0.05
raw_{\text{residual}}=[0.8,-0.4,0.7,-0.9,1.2,-0.6]
torque_{\text{mask}}=[0,0,0,0,1,1]
residual=[0,0,0,0,1.0,-0.6]
$$
若 base=[0,0,0,0,0.30,-0.20]，则：
applied=[0,0,0,0,0.35,-0.23]

腿部残差被 mask 清零；左轮原始残差 1.2 先裁到 1.0，再乘 0.05。最终动作还会再次裁到 `[-1,1]`。

### Upkie 代码映射

```python
import sys
sys.path.insert(0, 'src')
from stable_baselines3 import PPO

from upkie_mujoco_course.envs.standing_env import ResidualStandingEnv
from upkie_mujoco_course.rl.evaluate import (
    residual_checkpoint_metadata,
    validate_loaded_residual_policy,
)

checkpoint = "outputs/checkpoints/ppo_residual_latest.zip"
metadata = residual_checkpoint_metadata(checkpoint, residual_scale=0.05)
env = ResidualStandingEnv(
    max_episode_steps=200,
    residual_scale=float(metadata["residual_scale"]),
    residual_clip=float(metadata["residual_clip"]),
)
model = PPO.load(checkpoint, env=env)
validate_loaded_residual_policy(model, metadata)

# 残差评估循环
obs, _ = env.reset(seed=0)
total_reward = 0.0
for _ in range(200):
    residual_action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(residual_action)
    total_reward += reward
    if terminated or truncated:
        break

print(f"残差模式总奖励: {total_reward:.2f}")
env.close()
```

加载器先读 `ppo_residual_latest.metadata.json`，要求 `training_mode=residual`，再核对 zip 内嵌元数据。普通 `ppo_standing_latest.zip` 即使手改 sidecar，也会因 zip 内嵌模式不是 residual 被拒绝。

## 动手检查点

### 检查点 1：残差评估

先训练一个 RL 策略，再用残差模式评估：

```powershell
# 第一步：在 ResidualStandingEnv 中训练残差 PPO
python scripts/06_train_ppo_standing.py --mode residual --total-timesteps 10000 --seed 17 --residual-scale 0.05

# 第二步：加载独立残差 checkpoint
python scripts/08_eval_policy.py --mode residual --model outputs/checkpoints/ppo_residual_latest.zip --episodes 10 --seed 300 --residual-scale 0.05
```

这条 CLI 评估使用当前默认随机化配置。要复现固定的 10 N 推力配对实验，应运行专属实验，因为 `08_eval_policy.py` 没有暴露随机化参数。

### 检查点 2：多模式对比评估

使用 `08_eval_policy.py` 的四种模式（zero、classic、rl、residual）对比策略性能：

```powershell
# 纯经典控制
python scripts/08_eval_policy.py --mode classic --episodes 10

# 纯 RL 策略
python scripts/08_eval_policy.py --mode rl --model outputs/checkpoints/ppo_standing_latest.zip --episodes 10

# 残差模式（经典 + 独立残差 PPO）
python scripts/08_eval_policy.py --mode residual --model outputs/checkpoints/ppo_residual_latest.zip --episodes 10 --residual-scale 0.05
```

`rl` 与 `residual` 使用不同 checkpoint 和不同动作语义，不能把三条命令的回报当成只改变一个变量的严格配对实验。严格结论以 `run_rl_lab.py --chapter 30` 为准。

### 专属实验与统一验收

```powershell
python scripts/run_rl_lab.py --chapter 30
python scripts/course_checkpoint.py --chapter 30
```

固定实验事实：训练 seed `17`、10,000 步、`residual_scale=0.05`；评估 seed `300-309`；每回合第 50 步开始施加 10 N x 向推力，持续 10 步。真实指标为：

training_mode=residual
baseline_return_mean=392.5317382140501
residual_return_mean=396.7885578177174
residual_return_gap=4.256819603667282
paired_improvement_rate=1.0
baseline_success_rate=1.0
residual_success_rate=1.0
baseline_fall_rate=0.0
residual_fall_rate=0.0
residual_max_abs_pitch_rad=0.15424480121590495
residual_max_abs_action=1.0

通过条件明确拒绝性能退化：回报差必须非负，残差成功率不能低于基线，跌倒率不能高于基线，最大俯仰不超过 `0.35 rad`。

## 可视化证据

<!-- upkie-animation:30-evidence -->

固定证据为：

1. `outputs/plots/rl_30.png`：左图为经典/残差逐回合回报，右图为相同 seed 的逐回合回报差；
2. `outputs/logs/rl_30.json`：训练配置、checkpoint、扰动、配对 seed 和逐回合安全记录；
3. `outputs/results/rl_30.json`：性能与安全硬门槛；
4. `outputs/checkpoints/ppo_residual_latest.zip` 与 `ppo_residual_latest.metadata.json`：独立残差模型及训练模式；
5. `outputs/portfolio/30/evidence.json`：作品集索引。

## 故障诊断挑战

<!-- upkie-animation:30-comparison -->

**破坏**：在残差公式中去掉 clip——`u_total = u_classic + scale * u_rl` 不做限幅。

**第一处异常**：训练早期 RL 策略输出不稳定（可能很大），叠加到经典控制器输出后总力矩超出执行器范围。MuJoCo 会裁剪 ctrl，但 RL 策略不知道实际执行的动作与它输出的不同——导致策略学到错误的因果关系。

**根因假设**：RL 策略的 `u_rl` 在训练初期方差很大，与 `u_classic` 叠加后可能产生极端值。如果不在环境层面裁剪，执行器可能输出物理上不可能的力矩。

**最小修复**：恢复 `ResidualStandingEnv.step()` 中的两次裁剪和 torque mask，并检查 `info["base_action"]`、`info["residual_action"]`、`info["applied_action"]`。

**验证**：动作仍在范围内，并重新运行 10 N 配对实验；只有回报、成功率、跌倒率和俯仰边界全部通过才能恢复验收。

## 三档任务

### 基础任务

- 实现残差控制器，在三种扰动水平下比较纯经典控制和残差（经典+RL）的恢复时间。
- 绘制恢复时间 vs 扰动大小的对比曲线。

### 岗位挑战

- 在域随机化条件下训练残差策略，测试它在 10 种未见参数组合上的鲁棒性。
- 分析 scale 从 0 到 1 变化时，性能和稳定性的权衡曲线。

### 开放探索

- 研究"安全层"（Safety Layer）方法：用约束优化确保残差策略的输出不会使系统进入不安全状态。
- 写一段 200 字分析：残差 RL 在真实机器人部署中的关键挑战是什么？

## 复盘与面试

1. 为什么不直接用 RL？

<!-- upkie-qa:30-q1 -->
残差结构的核心价值是利用经典基线：总动作 = 经典控制器输出 + 被限幅的 RL 修正项。这带来两个好处。第一，减少从零探索：纯 RL 在训练初期输出接近随机动作，机器人频繁跌倒，大量样本消耗在“学会不倒”这一步上；残差结构从第一步就站在经典控制器的肩膀上，探索发生在“已经能平衡”的邻域内，样本效率高得多。第二，动作分工可审计：任意时刻都能把总动作拆成“经典部分 + 残差部分”，工程上可以单独监控残差的幅度和方向，判断 RL 到底在修正什么。但必须警惕一个常见误解：残差结构并没有自动解决安全问题。非零残差同样可能把系统推向错误方向（见 q2），所以动作限幅、状态终止条件、配对退化检查和部署安全层一样都不能省。一句话总结：残差 RL 用经典控制器换探索效率和可解释性，但安全保障仍靠显式的工程约束，不靠结构本身。
<!-- /upkie-qa -->

2. 残差策略的最差情况是什么？

<!-- upkie-qa:30-q2 -->
先看一个安慰性事实：零残差时总动作等于经典动作，所以未训练的策略（输出接近零）大致保持经典性能。但这不构成性能下界：训练后的策略完全可能输出持续非零的错误残差，把系统一直推向错误方向——比如奖励设计有漏洞时，策略可以学会用残差抵消经典控制器的正确修正来刷某个奖励分量。clip 只限制残差的幅度（本关固定 scale=0.05），不限制它的方向和持续性：一个幅度小但方向错误、每步都错的残差，累积效应足以让机器人慢慢漂移到跌倒边缘。所以“最差情况”的正确回答是：性能可以任意地比经典基线差，结构本身不提供保底。防御手段必须是实证的：用与经典基线相同 seed、相同扰动的配对评估监控回报差，一旦出现退化就拒绝部署；同时保留状态级安全终止（俯仰超限立即结束）作为最后一道防线。把“零残差等于基线”误读成“永远不会比基线差”，是残差 RL 部署中最危险的认知陷阱。
<!-- /upkie-qa -->

3. scale 参数的作用？

<!-- upkie-qa:30-q3 -->
scale 控制 RL 修正的强度：策略网络输出归一化动作后乘以 scale 才叠加到经典动作上，所以它直接决定残差的物理量纲上限。scale 小，RL 只能微调，安全但提升空间有限；scale 大，RL 有能力大幅改写经典动作，上限更高但退化风险同步放大。本项目的具体约定要分清两层：CLI 的默认值是 0.2，但第 30 关的固定证据链训练与评估均使用 0.05。更关键的是一致性的刚性约束：scale 在训练时就被“烤进”了策略——网络学到的输出分布是适配该 scale 的，同一个网络输出在不同 scale 下代表完全不同的物理力矩。若训练用 0.05 而评估时用 0.2 加载，残差幅度直接放大 4 倍，评估结果与训练行为完全脱节。所以本关的加载逻辑把 scale 写进 sidecar/zip 元数据：加载时请求值必须与训练尺度一致，否则直接拒绝评估而不是默默接受。这是“把隐式约定变成显式校验”的工程实践：参数不匹配应该在加载时报错，而不是在评估报告里留下一个无法解释的性能异常。
<!-- /upkie-qa -->

4. 怎样证明残差比纯经典控制好？

<!-- upkie-qa:30-q4 -->
用配对实验，而不是两组独立实验的均值比较。本关的协议是：在同一 10 N 推力扰动、相同 seed 序列下，分别运行“经典控制器”和“经典 + 残差”两套控制链路，保留每回合回报和安全记录后逐 seed 作差。配对的好处是消除环境随机性这个最大的方差来源：同一 seed 下两者面对完全相同的初始状态和扰动序列，回报差只反映控制器差异本身（第 31 关把这套方法扩展成了带置信区间的完整统计协议）。本次固定证据的结果是平均回报差 `+4.256819603667282`，残差版占优。但诚实的结论必须声明适用范围：它只证明在当前 200 步仿真协议、当前扰动强度、当前奖励定义下残差更好，不自动外推到更长时域、更大扰动或真实硬件。面试中完整的回答还应补两点：报告差值的同时报告逐 seed 分布（避免少数 seed 拉动均值）；除回报外同时比较安全指标（峰值俯仰、跌倒次数），因为回报更高但更危险的控制器在工程上不可接受。
<!-- /upkie-qa -->

## 下一关

关卡 `31` 先固定使用同一个 `WheelBalancerController` 比较标称与随机化分布，以隔离物理分布差异。残差策略可以复用同一协议，但第 31 关固定证据并没有加载本关 PPO，也不等于已经迁移到真实机器人。
